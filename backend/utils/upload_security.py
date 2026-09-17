"""Bounded upload validation shared by API endpoints."""

from __future__ import annotations

import csv
import io
import os
import warnings

from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile


class UploadValidationError(ValueError):
    """上传校验失败。

    携带机器可读的 ``reason`` 原因码 + 面向用户的中文文案，调用方可据此给出
    **精确**提示（而不是「文件不符合要求」这种无法排查的笼统话术）。

    历史教训：此前只抛无结构的 ``ValueError('invalid image content')``，调用方
    只能统一回 400「文件扩展名、真实图片内容或大小不符合要求」，把「文件名为空 /
    0 字节 / 超过 10MB / 像素超限 / 内容损坏 / 扩展名与内容不符」六种完全不同的
    故障混为一谈，线上排查只能靠猜。
    """

    # 原因码
    FILENAME_INVALID = "filename_invalid"
    EXTENSION_UNSUPPORTED = "extension_unsupported"
    SIZE_EMPTY = "size_empty"
    SIZE_TOO_LARGE = "size_too_large"
    DIMENSION_TOO_LARGE = "dimension_too_large"
    CONTENT_INVALID = "content_invalid"
    EXTENSION_MISMATCH = "extension_mismatch"

    _MESSAGES = {
        FILENAME_INVALID: "文件名不合法（为空或含路径分隔符）",
        EXTENSION_UNSUPPORTED: "不支持的文件扩展名",
        SIZE_EMPTY: "文件为空（0 字节），请重新裁剪或重新选择图片",
        SIZE_TOO_LARGE: "文件过大",
        DIMENSION_TOO_LARGE: "图片尺寸（像素）超出上限",
        CONTENT_INVALID: "文件内容不是有效的图片，或文件已损坏",
        EXTENSION_MISMATCH: "文件扩展名与真实图片格式不一致",
    }

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        message = self._MESSAGES.get(reason, reason)
        if detail:
            message = f"{message}（{detail}）"
        super().__init__(message)

    def as_dict(self) -> dict:
        return {"code": self.reason, "message": str(self)}


# 重编码时允许的图片格式（GIF 不重编码以保留动画）
_STRIP_FORMATS = {"JPEG", "PNG", "WEBP"}


_IMAGE_FORMATS = {
    "JPEG": (".jpg", ".jpeg"),
    "PNG": (".png",),
    "GIF": (".gif",),
    "WEBP": (".webp",),
}
_FORMULA_PREFIXES = ("=", "+", "-", "@")
_VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov")


def _validate_plain_filename(name: str, allowed_extensions: tuple[str, ...]) -> str:
    if not name or os.path.basename(name) != name or "\x00" in name:
        raise UploadValidationError(UploadValidationError.FILENAME_INVALID, repr(name)[:80])
    extension = os.path.splitext(name)[1].lower()
    if extension not in allowed_extensions:
        raise UploadValidationError(
            UploadValidationError.EXTENSION_UNSUPPORTED,
            f"{extension or '无扩展名'}，允许：{'/'.join(allowed_extensions)}",
        )
    return extension


def _default_max_pixels() -> int:
    """像素上限默认值取自 settings.MEDIA_MAX_IMAGE_PIXELS（2C4G 内存护栏）。

    旧实现硬编码 25_000_000，在生产 web 容器（mem_limit 544m / 2 workers）下
    解码一张满格图需要 ~300MB，直接把 worker 打爆。现在默认跟随配置，
    所有调用方（商品/客服/工单/头像）统一受同一护栏约束。
    """
    try:
        from django.conf import settings

        return int(getattr(settings, 'MEDIA_MAX_IMAGE_PIXELS', 12_000_000))
    except Exception:
        return 12_000_000


def _default_import_max_pixels() -> int:
    """批量导入/后台转码的「软」像素上限（2C4G 内存护栏）。

    与 validate_image_upload 的「硬拒绝」不同，批量导入路径走软降级：
    超限的图不拒绝，而是等比缩小到上限内，保证 DSLR 原图也能导入成功，
    同时把单张图的解码内存峰值钉死在 ~3 bytes/px 的水平。
    """
    try:
        from django.conf import settings

        return int(
            getattr(settings, "MEDIA_IMPORT_MAX_IMAGE_PIXELS", None)
            or getattr(settings, "MEDIA_MAX_IMAGE_PIXELS", 12_000_000) * 4 // 3
        )
    except Exception:
        return 16_000_000


def open_bounded_image(fp, *, max_pixels: int | None = None):
    """打开图片并把解码内存峰值控制在 max_pixels 以内。

    与 validate_image_upload 的区别：
      * 那个是「硬拒绝」——超限直接 400，用于面向用户的上传接口；
      * 这个 是「软降级」——超限就缩小，用于批量导入/后台转码，
        避免把用户已经准备好的整批商品图挡在门外。

    实现上有两个反直觉的点，踩过：
      1. JPEG 的 draft() 只支持 1/2、1/4、1/8 这类 2 的幂降采样。若只需要
         1.12 倍缩小，draft 会舍到 1（等于没降），白白多算一次。所以只在
         需要的倍数 ≥2 时才用 draft——它的真正用途是挡住几百 MP 的怪物图，
         避免「还没来得及缩小就已经把内存吃光」。
      2. ImageOps.exif_transpose 在**没有** EXIF 方向信息时返回 image.copy()，
         也就是白搭一份全尺寸拷贝（16MP 就是 48MB）。商品图绝大多数方向正常，
         先把方向读出来、只在真的需要旋转时才转，省掉这份拷贝。
    """
    from PIL import ImageOps

    if max_pixels is None:
        max_pixels = _default_import_max_pixels()
    max_pixels = max(1, int(max_pixels))

    img = Image.open(fp)

    # 文件头里就能拿到尺寸，此时还没解码
    width, height = img.size
    if width > 0 and height > 0 and width * height > max_pixels:
        needed = (width * height / max_pixels) ** 0.5
        # 只有当「至少得砍一半」时才值得动用 draft：draft 最小粒度就是 1/2，
        # 强行对只超一点点（如 20MP vs 16MP）的图用 draft 会直接砍到 1/2，
        # 白白损失一半画质。这类图交给下面的解码后缩放精修。
        if needed >= 2:
            factor = 1
            while factor < needed:
                factor *= 2
            try:
                img.draft(img.mode, (max(1, width // factor), max(1, height // factor)))
            except Exception:  # noqa: BLE001 - 格式不支持 draft 时忽略
                pass

    # 只有方向真的非正常时才转置（避免 exif_transpose 的无谓全图拷贝）；
    # transpose/load 都会触发完整解码，必须放在 draft 之后。
    try:
        orientation = img.getexif().get(0x0112)  # ExifTags.Base.Orientation
    except Exception:  # noqa: BLE001
        orientation = None
    if orientation and orientation != 1:
        img = ImageOps.exif_transpose(img)
    else:
        img.load()

    # 解码后再兜底缩一次：既覆盖 draft 不生效的格式（PNG/TIFF/WebP…），
    # 也覆盖「需要倍数 <2 所以跳过 draft」的情况。
    width, height = img.size
    if width > 0 and height > 0 and width * height > max_pixels:
        scale = (max_pixels / (width * height)) ** 0.5
        img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS)

    return img


def validate_image_upload(upload, *, max_bytes: int, max_pixels: int | None = None) -> tuple[str, str]:
    if max_pixels is None:
        max_pixels = _default_max_pixels()
    extension = _validate_plain_filename(upload.name, tuple(e for values in _IMAGE_FORMATS.values() for e in values))
    if upload.size <= 0:
        # 0 字节是最常见也最容易被误报为「存储故障」的一类：前端 canvas 导出失败
        # （toBlob 返回 null + toDataURL 返回 'data:,'）时会静默产出空 Blob。
        raise UploadValidationError(UploadValidationError.SIZE_EMPTY)
    if upload.size > max_bytes:
        raise UploadValidationError(
            UploadValidationError.SIZE_TOO_LARGE,
            f"{upload.name} {upload.size / 1048576:.1f}MB > {max_bytes / 1048576:.0f}MB",
        )

    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                image_format = image.format
                width, height = image.size
                if width <= 0 or height <= 0 or width * height > max_pixels:
                    raise UploadValidationError(
                        UploadValidationError.DIMENSION_TOO_LARGE,
                        f"{width}x{height} = {width * height / 1e6:.1f}MP > {max_pixels / 1e6:.0f}MP",
                    )
                image.verify()
    except UploadValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError) as exc:
        raise UploadValidationError(
            UploadValidationError.CONTENT_INVALID,
            f"{upload.name}: {str(exc).split(' <')[0]}",
        ) from exc
    finally:
        upload.seek(0)

    valid_extensions = _IMAGE_FORMATS.get(image_format or "")
    if not valid_extensions or extension not in valid_extensions:
        raise UploadValidationError(
            UploadValidationError.EXTENSION_MISMATCH,
            f"扩展名 {extension}，实际格式 {image_format or '未知'}",
        )
    mime = "image/jpeg" if image_format == "JPEG" else f"image/{image_format.lower()}"
    return extension, mime


def validate_media_upload(
    upload,
    *,
    image_max_bytes: int,
    video_max_bytes: int,
    allow_gif: bool = True,
) -> tuple[str, str]:
    extension = os.path.splitext(upload.name or "")[1].lower()
    if extension in tuple(e for values in _IMAGE_FORMATS.values() for e in values):
        if not allow_gif and extension == ".gif":
            raise UploadValidationError(UploadValidationError.EXTENSION_UNSUPPORTED, ".gif")
        return validate_image_upload(upload, max_bytes=image_max_bytes)

    extension = _validate_plain_filename(upload.name, _VIDEO_EXTENSIONS)
    if upload.size <= 0:
        raise UploadValidationError(UploadValidationError.SIZE_EMPTY)
    if upload.size > video_max_bytes:
        raise UploadValidationError(
            UploadValidationError.SIZE_TOO_LARGE,
            f"{upload.name} {upload.size / 1048576:.1f}MB > {video_max_bytes / 1048576:.0f}MB",
        )
    try:
        upload.seek(0)
        header = upload.read(16)
    finally:
        upload.seek(0)

    if extension in (".mp4", ".mov"):
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise UploadValidationError(UploadValidationError.CONTENT_INVALID, f"{upload.name} 不是 MP4/MOV")
        mime = "video/mp4" if extension == ".mp4" else "video/quicktime"
    elif extension == ".webm":
        if not header.startswith(b"\x1a\x45\xdf\xa3"):
            raise UploadValidationError(UploadValidationError.CONTENT_INVALID, f"{upload.name} 不是 WebM")
        mime = "video/webm"
    else:
        raise UploadValidationError(UploadValidationError.EXTENSION_UNSUPPORTED, extension)
    return extension, mime


def _is_formula(value: str) -> bool:
    return bool(value.lstrip()) and value.lstrip().startswith(_FORMULA_PREFIXES)


def parse_csv_upload(
    upload,
    *,
    max_bytes: int = 2 * 1024 * 1024,
    max_rows: int = 1000,
    max_columns: int = 30,
    max_cell_length: int = 2000,
) -> list[dict[str, str]]:
    _validate_plain_filename(upload.name, (".csv",))
    if upload.size <= 0:
        raise UploadValidationError(UploadValidationError.SIZE_EMPTY)
    if upload.size > max_bytes:
        raise UploadValidationError(UploadValidationError.SIZE_TOO_LARGE, f"{upload.size} > {max_bytes}")
    try:
        upload.seek(0)
        text = upload.read(max_bytes + 1).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadValidationError(UploadValidationError.CONTENT_INVALID, "CSV 需为 UTF-8 编码") from exc
    finally:
        upload.seek(0)
    if "\x00" in text:
        raise UploadValidationError(UploadValidationError.CONTENT_INVALID, "CSV 含空字节")

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames or len(reader.fieldnames) > max_columns:
        raise UploadValidationError("invalid CSV columns")
    rows = []
    for index, row in enumerate(reader, start=1):
        if index > max_rows:
            raise UploadValidationError("CSV row limit exceeded")
        for value in row.values():
            if value is None or len(value) > max_cell_length:
                raise UploadValidationError("CSV cell length exceeded")
            if _is_formula(value):
                raise UploadValidationError("CSV formula cells are not allowed")
        rows.append(row)
    return rows


def escape_csv_cell(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if _is_formula(text) else text


def to_webp(upload, *, quality: int = 90, method: int = 4, keep_gif: bool = True):
    """统一把上传图片转成 WebP（有损压缩）并剥离元数据、校正方向。

    用于「任何图片格式最终都落 WebP」的统一入口，返回新的 InMemoryUploadedFile：
    - 原为 WebP → 校验完整后原样返回（避免二次编码损耗，保留透明通道）。
    - 其他格式（PNG/JPEG/…）→ Pillow 转有损 WebP（quality=90，视觉近无损，
      体积比原始小 50–70%）；RGBA/LA/P/PA 保持 alpha（WebP 支持带 alpha 的有损）。
    - GIF 动画默认保留（转 WebP 会丢动画）；不保留时也会转成静态 WebP。
    - 解析/转码失败 → 原样返回，绝不让上传失败。

    调用方需保证已通过 validate_image_upload 校验（本函数是「再编码」而非「再校验」）。
    """
    try:
        upload.seek(0)
        with Image.open(upload) as probe:
            probe.load()
            fmt = (probe.format or '').upper()
            n_frames = getattr(probe, 'n_frames', 1) or 1
            # GIF 动画保留原文件（避免丢帧）
            if keep_gif and fmt == 'GIF' and n_frames > 1:
                upload.seek(0)
                return upload
            # 已是 WebP：完整可解码则原样返回，避免二次编码损耗
            if fmt == 'WEBP':
                upload.seek(0)
                return upload
            # 其余 → 重编码为有损 WebP
            img = ImageOps.exif_transpose(probe)  # 校正拍摄方向
            img.load()
            if img.mode in ('RGBA', 'LA', 'P', 'PA', 'I;16'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, 'WEBP', lossless=False, quality=quality, method=method)
        buf.seek(0)
        name = (upload.name or 'image.webp')
        base, _ext = os.path.splitext(name)
        return InMemoryUploadedFile(
            buf,
            'image',
            f'{base}.webp',
            'image/webp',
            buf.getbuffer().nbytes,
            None,
        )
    except Exception:
        # 任何异常都回退原始文件，保证可用
        try:
            upload.seek(0)
        except Exception:
            pass
        return upload


def strip_exif(upload):
    """重编码上传图片以剥离 EXIF（GPS / 相机 / 时间戳等元数据），并校正方向。

    返回新的 InMemoryUploadedFile；遇到非图片 / GIF / 解析异常时原样返回，
    保证调用方（default_storage.save / file.read）行为不变。
    """
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image_format = image.format or "JPEG"
            if image_format not in _STRIP_FORMATS:
                upload.seek(0)
                return upload

            # 按 EXIF Orientation 校正，避免重编码后图片横竖颠倒
            img = ImageOps.exif_transpose(image)
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            buffer = io.BytesIO()
            if image_format == "JPEG":
                img.save(buffer, format="JPEG", quality=85, exif=b"")
            elif image_format == "WEBP":
                img.save(buffer, format="WEBP", exif=b"")
            else:  # PNG —— save 默认不写 info 元数据
                img.save(buffer, format="PNG")

            buffer.seek(0)
            name = upload.name or f"image.{image_format.lower()}"
            return InMemoryUploadedFile(
                buffer,
                "image",
                name,
                f"image/{image_format.lower()}",
                buffer.tell(),
                None,
            )
    except Exception:
        # 任何异常都回退到原始文件，绝不让上传失败
        try:
            upload.seek(0)
        except Exception:
            pass
        return upload
