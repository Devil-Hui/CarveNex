"""R2 上传 — 同步落盘（Celery 已下线，不再做异步入队）。

对外接口与原先保持一致：
- enqueue_media_upload(file_obj, prefix, content_type) -> upload_id
- get_upload_status(upload_id) -> 结果 dict

图片统一转有损 WebP（GIF 动画保留），保存到 default_storage（R2/DB/本地回退），
结果写缓存供轮询查询。
"""

from __future__ import annotations

import os
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from utils.upload_security import to_webp

UPLOAD_RESULT_TTL = 3600
_TMP_DIRNAME = ".tmp_uploads"


def async_upload_enabled() -> bool:
    # 异步上传已随 Celery 下线，恒为 False，调用方按同步结果处理。
    return False


def _tmp_path(upload_id: str, ext: str) -> str:
    base = getattr(settings, "MEDIA_ROOT", "/app/media")
    tmp_dir = os.path.join(base, _TMP_DIRNAME)
    return os.path.join(tmp_dir, f"{upload_id}{ext}")


def enqueue_media_upload(file_obj, prefix: str, content_type: str) -> str:
    """图片统一转有损 WebP（GIF 动画保留）后，直接同步保存到存储并返回 upload_id。"""
    is_image = content_type.startswith("image/")
    if is_image:
        webp = to_webp(file_obj)
        content_type = getattr(webp, "content_type", content_type) or content_type
        file_obj = webp
    upload_id = uuid.uuid4().hex
    ext = os.path.splitext(getattr(file_obj, "name", "") or "")[1].lower() or ".webp"

    from django.core.files.storage import default_storage
    from utils.storage import media_key

    key = media_key(prefix, ext)
    raw = file_obj.read() if not hasattr(file_obj, "chunks") else b"".join(file_obj.chunks())
    try:
        path = default_storage.save(key, ContentFile(raw))
        url = default_storage.url(path)
        cache.set(
            f"upload:result:{upload_id}",
            {"status": "done", "url": url, "key": path},
            UPLOAD_RESULT_TTL,
        )
        return upload_id
    except Exception:
        cache.set(f"upload:result:{upload_id}", {"status": "error"}, UPLOAD_RESULT_TTL)
        raise


def get_upload_status(upload_id: str):
    return cache.get(f"upload:result:{upload_id}")