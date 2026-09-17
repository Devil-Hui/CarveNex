"""媒体同步服务 —— 文件直连对象存储（default_storage），缓存走 DB。

历史：早期存在「图片/视频以 Base64 暂存内存缓存 → Celery 任务回传对象存储」
的中间链路。该链路的上传主路径早已改为 default_storage.save 直写 MySQL + R2
（见 goods.views 与批量导入），中间暂存方法/字段已无代码，已整体移除。
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class MediaService:
    """媒体数量校验 / 排序推导 / 主图同步（纯 MySQL + 存储操作）。"""

    # ── 数量校验 ──

    @classmethod
    def validate_media_count(cls, spu_id: int, media_type: str) -> bool:
        """校验数量限制"""
        from .models import ProductMedia
        max_count = (
            settings.MEDIA_MAX_IMAGES_PER_SPU
            if media_type == 'image'
            else settings.MEDIA_MAX_VIDEOS_PER_SPU
        )
        current = ProductMedia.objects.filter(
            spu_id=spu_id, media_type=media_type
        ).exclude(status='rejected').count()
        return current < max_count

    @classmethod
    def get_next_sort_order(cls, spu_id: int, media_type: str) -> int:
        """获取下一个排序编号（头插 = 0，已有媒体往后排）"""
        from .models import ProductMedia
        last = ProductMedia.objects.filter(
            spu_id=spu_id, media_type=media_type
        ).exclude(status='rejected').order_by('-sort_order').first()
        if last is None:
            return 0
        return last.sort_order + 1

    # ── 同步 main_image ──

    @classmethod
    def sync_main_image(cls, spu_id: int):
        """同步 SPU.main_image = sort_order=0 的图片大图 URL"""
        from .models import ProductMedia, SPU
        first_image = ProductMedia.objects.filter(
            spu_id=spu_id, media_type='image', status='active'
        ).order_by('sort_order').first()
        if first_image and first_image.large_url:
            SPU.objects.filter(id=spu_id).update(main_image=first_image.large_url)
            logger.info(f'已同步 SPU#{spu_id} main_image: {first_image.large_url}')