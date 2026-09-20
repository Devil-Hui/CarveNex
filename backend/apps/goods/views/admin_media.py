"""媒体管理 API —— 列表 / 删除 / 排序 / 信息更新 / 编辑模式上传"""

import os
import json
from utils.storage import media_key
import logging
from io import BytesIO
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes

from utils.api_base_view import BaseApiView
from utils.upload_security import (
    UploadValidationError,
    strip_exif,
    validate_image_upload,
)
from ..models import ProductMedia, SPU
from apps.rbac.permissions import HasPerm
from ..admin_permissions import can_operate_spu
from ..media_service import MediaService
from ..serializers import (
    ProductMediaSerializer,
    MediaUpdateRequestSerializer,
    MediaUpdateResponseSerializer,
    MediaReorderRequestSerializer,
)
from ..services import GoodsCacheService

_logger = logging.getLogger('biz')

# WebP 编码质量（0-100，Pillow 档）。前端对应 WEBP_QUALITY=0.9，强度一致。
WEBP_QUALITY = 90


def _serialize_media(m: ProductMedia) -> dict:
    """序列化单个 ProductMedia 为响应 dict（含 alt_text）。"""
    item = {
        'id': m.id,
        'media_type': m.media_type,
        'sort_order': m.sort_order,
        'status': m.status,
        'alt_text': m.alt_text,
        'file_size': m.file_size,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    }
    if m.media_type == 'image':
        item.update({
            'thumb_url': m.thumb_url,
            'list_url': m.list_url,
            'large_url': m.large_url,
            'original_url': m.original_url,
        })
    else:
        item.update({
            'video_url': m.video_url,
            'video_thumb_url': m.video_thumb_url,
            'video_list_url': m.video_list_url,
            'video_large_url': m.video_large_url,
        })
    return item


def _delete_storage_file(url: str) -> None:
    """删除存储中的媒体文件（local / R2 通用，按 URL 自身形态判定后端）。

    - 绝对 URL（https://cdn.carvenex.com/... 或 https://api.carvenex.com/media/...）→ 远程 R2：
      剥掉域名与可选 /media/ 前缀得到对象 key，调 default_storage.delete(key)。
    - 相对路径 /media/... → 本地文件：MEDIA_ROOT 下删除。

    ⚠️ 必须以「URL 本身的形态」为准，而非当前 settings.FILE_STORAGE / MEDIA_URL。
    否则在 R2 模式下删除旧的「相对路径」记录时，会去 R2 删一个不存在的对象，
    导致本地卷里的文件永远删不掉（存储泄漏）。这是历史本地→R2 过渡期的典型坑。
    """
    if not url:
        return
    if url.startswith('http://') or url.startswith('https://'):
        path = urlparse(url).path  # /product_media/x.jpg 或 /media/product_media/x.jpg
        key = path.lstrip('/')
        if key.startswith('media/'):
            key = key[len('media/'):]
        try:
            default_storage.delete(key)
        except Exception as e:  # noqa: BLE001 - 删除失败仅告警，不影响主流程
            _logger.warning('删除远程文件失败 key=%s error=%s', key, e)
        return

    # 相对路径 /media/... → 本地文件
    key = url
    if key.startswith('/media/'):
        key = key[len('/media/'):]
    elif key.startswith('/'):
        key = key.lstrip('/')
    # 路径穿越防护：key 归一化后必须仍位于 MEDIA_ROOT 内才允许删除
    media_root = os.path.realpath(getattr(settings, 'MEDIA_ROOT', ''))
    local_path = os.path.realpath(os.path.join(media_root, key))
    if not local_path.startswith(media_root + os.sep):
        _logger.warning('拒绝删除 MEDIA_ROOT 之外的文件: key=%s', key)
        return
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except OSError as e:
            _logger.warning('删除本地文件失败 path=%s error=%s', local_path, e)


class MediaListBySPUView(BaseApiView):
    """获取 SPU 的媒体列表（含审核状态、alt_text）"""
    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(responses={200: ProductMediaSerializer})
    def get(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        media_qs = ProductMedia.objects.filter(spu_id=spu_id).order_by('sort_order', 'id')
        data = [_serialize_media(m) for m in media_qs]
        return Response(data)


class MediaDeleteView(BaseApiView):
    """删除单个媒体（pending / rejected / active 均可删除，active 需前端二次确认）。

    删除时同步清理存储文件 + 失效媒体列表缓存。
    """
    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description='Media deleted')}
    )
    def delete(self, request, media_id):
        try:
            media = ProductMedia.objects.get(id=media_id)
        except ProductMedia.DoesNotExist:
            return Response({'detail': '媒体不存在'}, status=status.HTTP_404_NOT_FOUND)

        spu_id = media.spu_id
        if spu_id:
            try:
                spu = SPU.objects.get(id=spu_id)
            except SPU.DoesNotExist:
                return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)
            if not can_operate_spu(request.user, spu):
                return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        # 清理存储文件（thumb/list/large/original 或视频；支持 local/R2）
        if media.media_type == 'image':
            for url in (media.thumb_url, media.list_url, media.large_url, media.original_url):
                _delete_storage_file(url)
        else:
            for url in (media.video_url, media.video_thumb_url, media.video_list_url, media.video_large_url):
                _delete_storage_file(url)
        ProductMedia.objects.filter(id=media_id).delete()

        # 失效媒体列表缓存
        if spu_id:
            GoodsCacheService.invalidate_media_list(spu_id)
            GoodsCacheService.invalidate_spu(spu_id)
            GoodsCacheService.invalidate_spu_list()
            # 同步 main_image
            MediaService.sync_main_image(spu_id)
        return Response({'detail': '已删除'})


class MediaReorderView(BaseApiView):
    """调整媒体排序"""
    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(
        request=MediaReorderRequestSerializer,
        responses={200: OpenApiResponse(description='Media reordered')}
    )
    def post(self, request):
        media_ids = request.data.get('media_ids', [])
        if not media_ids:
            return Response({'detail': 'media_ids 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 组隔离：验证所有媒体项所属 SPU 是否可操作
        media_map = {}  # media_id → ProductMedia（预取，后续排序时复用）
        for mid in media_ids:
            try:
                media = ProductMedia.objects.select_related('spu').get(id=mid)
                if not can_operate_spu(request.user, media.spu):
                    return Response({'detail': f'媒体 {mid} 所属 SPU 不在您的管理范围内'}, status=status.HTTP_403_FORBIDDEN)
                media_map[mid] = media
            except ProductMedia.DoesNotExist:
                return Response({'detail': f'媒体 {mid} 不存在'}, status=status.HTTP_404_NOT_FOUND)

        spu_ids = set()
        for idx, media_id in enumerate(media_ids):
            updated = ProductMedia.objects.filter(id=media_id).update(sort_order=idx)
            if updated:
                # 从已查询的 media 对象中获取 spu_id，避免重复查询
                for mid, m in media_map.items():
                    if mid == media_id:
                        spu_ids.add(m.spu_id)
                        break
        # 失效涉及的 SPU 媒体缓存
        for sid in spu_ids:
            if sid:
                GoodsCacheService.invalidate_media_list(sid)
                GoodsCacheService.invalidate_spu(sid)
                GoodsCacheService.invalidate_spu_list()
                # 排序变更后重新推导主图（sort_order=0 的图片大图）
                MediaService.sync_main_image(sid)
        return Response({'detail': '排序已更新', 'count': len(media_ids)})


class MediaUpdateView(BaseApiView):
    """更新媒体信息（alt_text / sort_order）"""
    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(
        request=MediaUpdateRequestSerializer,
        responses={200: MediaUpdateResponseSerializer}
    )
    def patch(self, request, media_id):
        try:
            media = ProductMedia.objects.get(id=media_id)
        except ProductMedia.DoesNotExist:
            return Response({'detail': '媒体不存在'}, status=status.HTTP_404_NOT_FOUND)

        if media.spu_id:
            try:
                spu = SPU.objects.get(id=media.spu_id)
            except SPU.DoesNotExist:
                return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)
            if not can_operate_spu(request.user, spu):
                return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        update_fields = []
        if 'alt_text' in request.data:
            val = str(request.data['alt_text'] or '')
            if len(val) > 200:
                return Response({'detail': 'alt_text 长度不能超过 200'}, status=status.HTTP_400_BAD_REQUEST)
            media.alt_text = val
            update_fields.append('alt_text')
        if 'sort_order' in request.data:
            try:
                sort_order = int(request.data['sort_order'])
            except (TypeError, ValueError):
                return Response({'detail': 'sort_order 必须为整数'}, status=status.HTTP_400_BAD_REQUEST)
            if sort_order < 0:
                return Response({'detail': 'sort_order 不能为负数'}, status=status.HTTP_400_BAD_REQUEST)
            media.sort_order = sort_order
            update_fields.append('sort_order')

        if update_fields:
            media.save(update_fields=update_fields)
            # 失效媒体列表缓存
            if media.spu_id:
                GoodsCacheService.invalidate_media_list(media.spu_id)
                GoodsCacheService.invalidate_spu(media.spu_id)
                GoodsCacheService.invalidate_spu_list()
            # 排序变化需重新计算主图（sort_order=0 的图片大图）。
            if 'sort_order' in request.data:
                MediaService.sync_main_image(media.spu_id) if media.spu_id else None

        return Response({
            'id': media.id,
            'alt_text': media.alt_text,
            'sort_order': media.sort_order,
            'message': '更新成功',
        })


class MediaUploadRejected(ValueError):
    """媒体上传被拒绝（4xx，客户端可修正）。

    继承 ValueError 以兼容既有 `except ValueError` 分支；额外携带机器可读的
    `code`（= UploadValidationError.reason 或 'content_type_unsupported'）与
    出问题的 `file` 名，供调用方回传给前端做精确提示与定位。

    历史教训：此前所有校验失败统一抛
    `ValueError('文件扩展名、真实图片内容或大小不符合要求')`，把「0 字节 / 超过
    10MB / 像素超限 / 内容损坏 / 扩展名与内容不符 / 类型不支持」六种故障混为一谈；
    前端又把它一律翻译为「请检查存储空间是否充足后重试」，导致线上完全无法定位，
    用户反复重试还留下 8 个空商品（SPU 61→68）。
    """

    def __init__(self, message: str, *, code: str = '', file: str = ''):
        super().__init__(message)
        self.code = code
        self.file = file


def _is_disk_full(exc: BaseException) -> bool:
    """判断异常是否为「磁盘空间不足」（OSError ENOSPC / EDQUOT）。

    只有这一种情况才允许对用户说「存储空间不足」——其余一律按存储服务异常处理，
    避免把校验失败/网络抖动误报成容量问题。
    """
    errno = getattr(exc, 'errno', None)
    return errno in (28, 122)  # ENOSPC / EDQUOT


def _validate_and_save_cropped(files: dict, spu_id: int):
    """校验并保存四尺寸裁剪图，返回 dict 或抛异常。

    `files` 形如 {'thumb': Upload, 'list': Upload, 'large': Upload, 'original': Upload}。

    返回:
        {
          'thumb': url, 'list': url, 'large': url, 'original': url,
          'validated_extensions': {id(f): ext, ...},
          'sizes': {id(f): size, ...},
        }

    校验失败抛 `ValueError`（message 为给前端的 detail 文案）；
    存储异常统一抛带「存储服务异常」信息的 ValueError（由调用方降级为 502）。
    """
    # 读取四尺寸文件
    thumb = files.get('thumb')
    list_file = files.get('list')
    large = files.get('large')
    original = files.get('original')
    if not all([thumb, list_file, large, original]):
        missing = [k for k, v in (
            ('thumb', thumb), ('list', list_file), ('large', large), ('original', original),
        ) if not v]
        raise MediaUploadRejected(
            f'缺少必需的图片字段: {"/".join(missing)}（需要 thumb/list/large/original 四尺寸齐全）',
            code='missing_parts',
        )

    # 校验真实图片内容、扩展名、类型和大小；全部通过后才允许写存储。
    allowed = getattr(settings, 'FILE_STORAGE_ALLOWED_TYPES', [])
    max_size = getattr(settings, 'MEDIA_MAX_FILE_SIZE_MB', 10) * 1024 * 1024
    validated_extensions = {}
    for f in (thumb, list_file, large, original):
        try:
            extension, content_type = validate_image_upload(f, max_bytes=max_size)
        except UploadValidationError as exc:
            # 精确回传「哪一个文件 + 因为什么」被拒，并落一条带 request_id 的告警，
            # 让下次同类故障可以直接 grep 到，而不是靠猜。
            _logger.warning(
                '媒体上传校验失败 spu=%s file=%s size=%s reason=%s detail=%s',
                spu_id, f.name, getattr(f, 'size', None), exc.reason, exc,
            )
            raise MediaUploadRejected(
                f'「{f.name}」{exc}', code=exc.reason, file=f.name or '',
            ) from exc
        if allowed and content_type not in allowed:
            _logger.warning(
                '媒体上传类型不受支持 spu=%s file=%s content_type=%s',
                spu_id, f.name, content_type,
            )
            raise MediaUploadRejected(
                f'「{f.name}」不支持的文件类型: {content_type}（允许：{"/".join(allowed)}）',
                code='content_type_unsupported', file=f.name or '',
            )
        f.content_type = content_type
        validated_extensions[id(f)] = extension

    def save_file(f):
        content_type = getattr(f, 'content_type', '') or ''
        ext = validated_extensions[id(f)]
        # 前端已 WebP（q90）或历史 WebP → 校验完整性后原样落盘：
        #   避免二次编码损耗，且保留透明通道（strip_exif 对 WEBP 会拍平 RGBA 致透明变黑）。
        if content_type == 'image/webp' or ext.lower() == '.webp':
            try:
                f.seek(0)
                with Image.open(f) as probe:
                    probe.load()  # 强制全量像素解码，校验文件完整可解码
                    # 真实格式必须是 WEBP：防止伪造 content_type/扩展名（实为 PNG/JPEG 字节）
                    # 却以 .webp 后缀裸存导致展示损坏 —— 不符则降级到下方 Pillow 重编码。
                    if (probe.format or '').upper() != 'WEBP':
                        raise ValueError(f'声明 WebP 但实际格式为 {probe.format}')
                f.seek(0)
                raw = f.read()
                path = default_storage.save(
                    media_key('products', '.webp'),
                    ContentFile(raw),
                )
                return default_storage.url(path)
            except Exception as exc:  # noqa: BLE001 - WebP 直存失败 → 落入下方重编码兜底
                _logger.warning('WebP 直存校验失败，转 Pillow 重编码: %s', exc)

        # 其余格式（PNG/JPEG/...）→ Pillow 转「高质量 WebP」 q90（Google libwebp）：
        #   视觉近无损，体积比无损 WebP 再小 50–70%；EXIF 方向校正 + 重编码剥离元数据。
        try:
            f.seek(0)
            with Image.open(f) as img:
                img = ImageOps.exif_transpose(img)  # 校正手机拍摄方向
                img.load()
                # 保留透明通道（WebP 支持带 alpha 的有损），否则转 RGB 减小体积
                if img.mode in ('RGBA', 'LA', 'P', 'PA'):
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
                buf = BytesIO()
                # lossless=False + quality=WEBP_QUALITY：视觉无损；method=4 平衡压缩率与上传耗时
                img.save(buf, 'WEBP', lossless=False, quality=WEBP_QUALITY, method=4)
            buf.seek(0)
            path = default_storage.save(
                media_key('products', '.webp'),
                ContentFile(buf.getvalue()),
            )
            return default_storage.url(path)
        except UploadValidationError:
            raise
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 - 转码失败回退原格式，保证可用
            _logger.warning('WebP 转码失败，回退原格式保存: %s', exc)
            f.seek(0)
            path = default_storage.save(media_key('products', ext), strip_exif(f))
            return default_storage.url(path)

    # 保存四尺寸文件；任一失败整体失败（文件已落盘的由后续错误处理兜底）。
    try:
        thumb_url = save_file(thumb)
        list_url = save_file(list_file)
        large_url = save_file(large)
        original_url = save_file(original)
    except UploadValidationError:
        raise
    except Exception as exc:  # noqa: BLE001 - 存储异常统一抛给调用方（502）
        _logger.exception('媒体图片保存失败 spu=%s', spu_id)
        # 仅当确为磁盘写满（ENOSPC/EDQUOT）时才对用户说「存储空间不足」；
        # 其余情况一律表述为存储服务异常，杜绝「校验失败被误报成容量不足」。
        if _is_disk_full(exc):
            raise RuntimeError('图片保存失败：存储空间不足（磁盘已满），请清理后重试。') from exc
        raise RuntimeError(f'图片保存失败（存储服务异常），请稍后重试。{type(exc).__name__}') from exc

    sizes = {
        id(thumb): thumb.size,
        id(list_file): list_file.size,
        id(large): large.size,
        id(original): original.size,
    }
    return {
        'thumb': thumb_url,
        'list': list_url,
        'large': large_url,
        'original': original_url,
        'validated_extensions': validated_extensions,
        'sizes': sizes,
    }


class MediaCreateView(BaseApiView):
    """编辑模式：向已有 SPU 上传图片。

    接收前端 ImageCropper 裁剪后的四尺寸图片（thumb/list/large/original），
    保存到本地存储并创建 ProductMedia 记录（status='active'）。
    路由: POST /goods/media/spu/<spu_id>/upload
    """
    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={201: ProductMediaSerializer}
    )
    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        # 数量校验
        if not MediaService.validate_media_count(spu_id, 'image'):
            return Response(
                {'detail': f'图片数量已达上限 ({settings.MEDIA_MAX_IMAGES_PER_SPU} 张)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 校验并保存四尺寸裁剪图
        try:
            result = _validate_and_save_cropped(request.FILES, spu_id)
        except MediaUploadRejected as exc:
            # 回传 code / file，前端据此给出精确提示（不再一律说「存储空间不足」）
            return Response(
                {'detail': str(exc), 'code': exc.code, 'file': exc.file},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:  # 存储服务异常 → 502
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        # 四尺寸总大小
        total_size = sum(result['sizes'].values())
        sort_order = MediaService.get_next_sort_order(spu_id, 'image')
        alt_text = str(request.data.get('alt_text', '') or '')

        media = ProductMedia.objects.create(
            spu=spu,
            media_type='image',
            thumb_url=result['thumb'],
            list_url=result['list'],
            large_url=result['large'],
            original_url=result['original'],
            sort_order=sort_order,
            status='active',
            file_size=total_size,
            alt_text=alt_text,
        )

        # 同步 SPU main_image
        MediaService.sync_main_image(spu_id)
        # 失效媒体列表缓存
        GoodsCacheService.invalidate_media_list(spu_id)
        GoodsCacheService.invalidate_spu(spu_id)
        GoodsCacheService.invalidate_spu_list()

        return Response(_serialize_media(media), status=status.HTTP_201_CREATED)


class MediaReplaceView(BaseApiView):
    """原地重新裁剪/替换单张图片（不新增记录）。

    接收前端 ImageCropper 重新裁剪后的四尺寸图片（thumb/list/large/original），
    在**原 ProductMedia 记录上原地替换**四 URL（保留 id / sort_order / alt_text），
    删除被替换的旧存储文件，并同步 SPU.main_image —— 解决「重新裁剪主图会追加到
    队尾、不成主图，且触顶 15 张上限被拒」的功能缺口。
    路由: POST /goods/media/<media_id>/replace

    ⚠️ 仅在 media_type='image' 且 status='active'/'pending'/'rejected' 时允许替换；
    media_type='video' 走其它端点。
    """
    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: ProductMediaSerializer}
    )
    def post(self, request, media_id):
        try:
            media = ProductMedia.objects.select_related('spu').get(id=media_id)
        except ProductMedia.DoesNotExist:
            return Response({'detail': '媒体不存在'}, status=status.HTTP_404_NOT_FOUND)

        spu = media.spu
        if spu and not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        # 仅支持图片
        if media.media_type != 'image':
            return Response(
                {'detail': '仅支持图片重新裁剪'}, status=status.HTTP_400_BAD_REQUEST)

        spu_id = media.spu_id

        # 校验并保存新四尺寸
        try:
            result = _validate_and_save_cropped(request.FILES, spu_id)
        except MediaUploadRejected as exc:
            return Response(
                {'detail': str(exc), 'code': exc.code, 'file': exc.file},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        # 记录裁剪前的旧 URL，替换成功后删除旧文件
        old_urls = [media.thumb_url, media.list_url, media.large_url, media.original_url]
        new_urls = [result['thumb'], result['list'], result['large'], result['original']]

        # 原地更新（保留 id / sort_order / alt_text / status）
        media.thumb_url = result['thumb']
        media.list_url = result['list']
        media.large_url = result['large']
        media.original_url = result['original']
        media.file_size = sum(result['sizes'].values())
        media.save(update_fields=[
            'thumb_url', 'list_url', 'large_url', 'original_url', 'file_size',
        ])

        # 删除旧文件（替换后；不影响新图）
        for old in old_urls:
            if old and old not in new_urls:
                _delete_storage_file(old)

        # 主图同步 + 缓存失效（若替换的正是主图，main_image 会指向新的 large_url）
        if spu_id:
            MediaService.sync_main_image(spu_id)
            GoodsCacheService.invalidate_media_list(spu_id)
            GoodsCacheService.invalidate_spu(spu_id)
            GoodsCacheService.invalidate_spu_list()

        return Response(_serialize_media(media))


class MediaVideoCreateView(BaseApiView):
    """1.2 视频上传：向已有 SPU 上传一条商品视频。

    路由: POST /goods/media/spu/<spu_id>/video/upload
    校验：video/mp4、video/webm、video/quicktime；单条 ≤ MEDIA_MAX_VIDEO_SIZE_MB(200)。
    保存原视频到对象存储，创建 ProductMedia(media_type='video')。
    """

    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiResponse(description='Video media created')}
    )
    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        # 数量校验
        if not MediaService.validate_media_count(spu_id, 'video'):
            return Response(
                {'detail': f'视频数量已达上限 ({settings.MEDIA_MAX_VIDEOS_PER_SPU} 条)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        video = request.FILES.get('file')
        if not video:
            return Response({'detail': '请上传文件字段 file'}, status=status.HTTP_400_BAD_REQUEST)

        allowed = {'video/mp4': '.mp4', 'video/webm': '.webm', 'video/quicktime': '.mov'}
        content_type = (video.content_type or '').lower()
        ext = allowed.get(content_type)
        if not ext:
            return Response(
                {'detail': f'不支持的文件类型: {content_type}（仅支持 MP4/WebM/MOV）'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_bytes = getattr(settings, 'MEDIA_MAX_VIDEO_SIZE_MB', 200) * 1024 * 1024
        if video.size > max_bytes:
            return Response(
                {'detail': f'视频过大（> {settings.MEDIA_MAX_VIDEO_SIZE_MB}MB）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            path = default_storage.save(media_key('products/video', ext), video)
            video_url = default_storage.url(path)
        except Exception as exc:  # noqa: BLE001 - 存储异常统一降级为可读错误
            _logger.exception('SPU %s 视频保存失败', spu_id)
            return Response(
                {'detail': f'视频保存失败（存储服务异常），请稍后重试。{type(exc).__name__}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 视频首帧：可选字段 thumb（1 张 WebP 缩略图），前端如果提供则一并入库，
        # 用于列表/详情缩略图显示（无则回退到播放器首帧）。其余 list/large 留空。
        video_thumb_url = ''
        thumb = request.FILES.get('thumb')
        if thumb:
            try:
                thumb_path = default_storage.save(
                    media_key('products/video_thumb', '.webp'),
                    thumb,
                )
                video_thumb_url = default_storage.url(thumb_path)
            except Exception as exc:  # noqa: BLE001 - 首帧保存失败不影响主视频
                _logger.warning('SPU %s 视频首帧保存失败: %s', spu_id, exc)

        media = ProductMedia.objects.create(
            spu=spu,
            media_type='video',
            video_url=video_url,
            video_thumb_url=video_thumb_url,
            sort_order=MediaService.get_next_sort_order(spu_id, 'video'),
            status='active',
            file_size=video.size,
        )
        GoodsCacheService.invalidate_media_list(spu_id)
        GoodsCacheService.invalidate_spu(spu_id)
        GoodsCacheService.invalidate_spu_list()
        return Response(_serialize_media(media), status=status.HTTP_201_CREATED)


def _r2_client():
    """构造指向 Cloudflare R2 的 boto3 S3 client（仅当生产启用 R2）。

    依赖 django-storages 的 S3Boto3Storage 配置（AWS_* 环境变量已在 settings.prod
    注入）。未配置 R2 时返回 None，调用方应降级报错。
    """
    if getattr(settings, 'FILE_STORAGE', 'local') != 'r2':
        return None
    account_id = getattr(settings, 'R2_ACCOUNT_ID', '')
    if not account_id:
        return None
    import boto3
    return boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=getattr(settings, 'R2_ACCESS_KEY_ID', ''),
        aws_secret_access_key=getattr(settings, 'R2_SECRET_ACCESS_KEY', ''),
        region_name='auto',
    )


_VIDEO_ALLOWED_EXT = {'.mp4', '.webm', '.mov'}



class MediaVideoChunkInitView(BaseApiView):
    """分片上传第 1 步：申请 R2 multipart upload。

    路由: POST /goods/media/spu/<spu_id>/video/chunk-init
    请求体: {"file_name": "demo.mp4", "content_type": "video/mp4", "file_size": 12345678}
    响应: { "key": "...", "upload_id": "...", "chunk_size": 8388608, "chunks": 12 }
    """

    permission_classes = [HasPerm('goods.media.write')]

    @extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiResponse(description='Multipart init')})
    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        client = _r2_client()
        if client is None:
            return Response({'detail': '服务端未启用 R2，无法分片上传。请改用普通视频上传。'}, status=status.HTTP_400_BAD_REQUEST)

        file_name = str(request.data.get('file_name', '') or '').strip()
        content_type = str(request.data.get('content_type', '') or '').lower().strip()
        file_size = int(request.data.get('file_size') or 0)
        if not file_name or not content_type:
            return Response({'detail': '缺少 file_name 或 content_type'}, status=status.HTTP_400_BAD_REQUEST)
        if content_type not in {'video/mp4', 'video/webm', 'video/quicktime'}:
            return Response({'detail': f'不支持的文件类型: {content_type}'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(file_name)[1].lower() or '.mp4'
        if ext not in _VIDEO_ALLOWED_EXT:
            return Response({'detail': f'不支持的扩展名: {ext}'}, status=status.HTTP_400_BAD_REQUEST)
        max_bytes = getattr(settings, 'MEDIA_MAX_VIDEO_SIZE_MB', 200) * 1024 * 1024
        if file_size > max_bytes:
            return Response(
                {'detail': f'视频过大（> {settings.MEDIA_MAX_VIDEO_SIZE_MB}MB）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key = media_key('products/video', ext)
        chunk_size = int(getattr(settings, 'R2_CHUNK_SIZE', 8)) * 1024 * 1024
        chunks = max(1, -(-file_size // chunk_size)) if file_size else 1
        try:
            created = client.create_multipart_upload(
                Bucket=getattr(settings, 'R2_BUCKET', ''),
                Key=key,
                ContentType=content_type,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.exception('创建 R2 分片上传失败 spu=%s', spu_id)
            return Response({'detail': f'创建分片上传失败：{type(exc).__name__}'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            'key': key,
            'upload_id': created['UploadId'],
            'chunk_size': chunk_size,
            'chunks': chunks,
        })


class MediaVideoChunkUploadView(BaseApiView):
    """分片上传第 2 步：上传单个分片。

    路由：POST /gw/media/spu/<spu_id>/video/chunk-upload
    multipart/form-data: upload_id + key + part_number + part(文件)
    """

    permission_classes = [HasPerm('goods.media.write')]

    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        client = _r2_client()
        if client is None:
            return Response({'detail': '服务端未启用 R2'}, status=status.HTTP_400_BAD_REQUEST)

        upload_id = str(request.data.get('upload_id', '') or '').strip()
        part_number = int(request.data.get('part_number') or 0)
        key = str(request.data.get('key', '') or '').strip()
        chunk = request.FILES.get('part')
        if not upload_id or not key or not part_number or not chunk:
            return Response({'detail': '缺少 upload_id/key/part_number/part'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chunk_bytes = chunk.read()
            resp = client.upload_part(
                Bucket=getattr(settings, 'R2_BUCKET', ''),
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=chunk_bytes,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.exception('分片上传失败 spu=%s part=%s', spu_id, part_number)
            return Response({'detail': f'分片上传失败：{type(exc).__name__}'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'etag': resp.get('ETag', '')})


class MediaVideoChunkCompleteView(BaseApiView):
    """分片上传第 3 步：完成 multipart —— 合并对象并建立 ProductMedia(video)。

    请求体: {"key":..., "upload_id":..., "parts": [{"part_number":1,"etag":"..."},...],
              "content_type": "video/mp4", "file_size": 12345678}
    可选 thumb: 视频头帧 WebP（multipart file）。
    """

    permission_classes = [HasPerm('goods.media.write')]

    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': 'SPU 不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, spu):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        if not MediaService.validate_media_count(spu_id, 'video'):
            return Response(
                {'detail': f'视频数量已达上限 ({settings.MEDIA_MAX_VIDEOS_PER_SPU} 条)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client = _r2_client()
        if client is None:
            return Response({'detail': '服务端未启用 R2'}, status=status.HTTP_400_BAD_REQUEST)

        key = str(request.data.get('key', '') or '').strip()
        upload_id = str(request.data.get('upload_id', '') or '').strip()
        raw_parts = request.data.get('parts') or []
        # multipart/form-data 传 JSON 字符串；JSON body 时已是 list
        if isinstance(raw_parts, str) and raw_parts.strip():
            try:
                raw_parts = json.loads(raw_parts)
            except (ValueError, TypeError):
                raw_parts = []
        content_type = str(request.data.get('content_type', '') or '').strip().lower()
        file_size = int(request.data.get('file_size') or 0)
        if not key or not upload_id or not raw_parts:
            return Response({'detail': '缺少 key/upload_id/parts'}, status=status.HTTP_400_BAD_REQUEST)
        if not key.startswith('products/video/'):
            return Response({'detail': '非法的对象 key'}, status=status.HTTP_400_BAD_REQUEST)

        parts = []
        seen = set()
        for p in raw_parts:
            try:
                num = int(p.get('part_number'))
                etag = (p.get('etag') or '').strip()
            except (TypeError, ValueError, AttributeError):
                continue
            if not num or not etag or num in seen:
                continue
            seen.add(num)
            parts.append({'PartNumber': num, 'ETag': etag})
        if not parts:
            return Response({'detail': 'parts 必须含 part_number + etag'}, status=status.HTTP_400_BAD_REQUEST)
        parts.sort(key=lambda x: x['PartNumber'])

        try:
            client.complete_multipart_upload(
                Bucket=getattr(settings, 'R2_BUCKET', ''),
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts},
            )
        except Exception as exc:  # noqa: BLE001
            _logger.exception('分片合并失败 spu=%s key=%s', spu_id, key)
            try:
                client.abort_multipart_upload(
                    Bucket=getattr(settings, 'R2_BUCKET', ''),
                    Key=key,
                    UploadId=upload_id,
                )
            except Exception:  # noqa: BLE001
                pass
            return Response({'detail': f'分片合并失败：{type(exc).__name__}'}, status=status.HTTP_502_BAD_GATEWAY)

        if not file_size:
            try:
                head = client.head_object(
                    Bucket=getattr(settings, 'R2_BUCKET', ''),
                    Key=key,
                )
                file_size = int(head.get('ContentLength') or 0)
            except Exception:  # noqa: BLE001
                file_size = 0
        max_bytes = getattr(settings, 'MEDIA_MAX_VIDEO_SIZE_MB', 200) * 1024 * 1024
        if file_size > max_bytes:
            return Response(
                {'detail': f'视频过大（> {settings.MEDIA_MAX_VIDEO_SIZE_MB}MB）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        video_url = f"{getattr(settings, 'R2_PUBLIC_URL', '').rstrip('/') or 'https://cdn.carvenex.com'}/{key}"

        video_thumb_url = ''
        thumb = request.FILES.get('thumb')
        if thumb:
            try:
                thumb_path = default_storage.save(
                    media_key('products/video_thumb', '.webp'),
                    thumb,
                )
                video_thumb_url = default_storage.url(thumb_path)
            except Exception as exc:  # noqa: BLE001 - 首帧保存失败不影响主视频
                _logger.warning('SPU %s 视频首帧保存失败: %s', spu_id, exc)

        media = ProductMedia.objects.create(
            spu=spu,
            media_type='video',
            video_url=video_url,
            video_thumb_url=video_thumb_url,
            sort_order=MediaService.get_next_sort_order(spu_id, 'video'),
            status='active',
            file_size=file_size,
        )
        GoodsCacheService.invalidate_media_list(spu_id)
        GoodsCacheService.invalidate_spu(spu_id)
        GoodsCacheService.invalidate_spu_list()
        return Response(_serialize_media(media), status=status.HTTP_201_CREATED)
