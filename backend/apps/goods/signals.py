"""商品信号 —— 同步缓存、布隆过滤器、main_image"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import ProductMedia, SPU, SKU
from .services import GoodsCacheService

logger = logging.getLogger(__name__)


# ── SPU 信号：创建/更新时自动同步布隆过滤器 + 清除缓存 ──

@receiver(post_save, sender=SPU)
def on_spu_saved(sender, instance, created, **kwargs):
    """SPU 保存后：同步布隆过滤器并清除相关缓存"""
    if created:
        GoodsCacheService.add_spu_to_bloom(instance.id)
        logger.info(f'信号: SPU#{instance.id} 已加入布隆过滤器')
    # 清除 SPU 详情缓存 & 列表缓存（确保下次请求拿到最新数据）
    transaction.on_commit(lambda: GoodsCacheService.invalidate_spu(instance.id))
    transaction.on_commit(lambda: GoodsCacheService.invalidate_spu_list())
    # 热门商品缓存：商品任何状态变更（上架/下架/删除/驳回）都可能影响热榜，
    # 统一失效避免「热榜展示已下架商品、点击 404」的缓存一致性问题
    # （hot 重建成本低——单次查询，商品变更频率低，无条件失效保证绝对正确）
    transaction.on_commit(GoodsCacheService.invalidate_hot_products)


# ── SKU 信号：创建/更新时自动同步布隆过滤器 + 清除缓存 ──

@receiver(post_save, sender=SKU)
def on_sku_saved(sender, instance, created, **kwargs):
    """SKU 保存后：同步布隆过滤器并清除相关缓存"""
    if created:
        GoodsCacheService.add_sku_to_bloom(instance.id)
        logger.info(f'信号: SKU#{instance.id} 已加入布隆过滤器')
    # 清除所属 SPU 详情缓存 & 热销缓存
    if instance.spu_id:
        transaction.on_commit(lambda: GoodsCacheService.invalidate_spu(instance.spu_id))
        transaction.on_commit(lambda: GoodsCacheService.invalidate_hot_products())


# ── ProductMedia 信号：同步 main_image ──

@receiver(post_save, sender=ProductMedia)
def sync_main_image_on_media_active(sender, instance, **kwargs):
    """当图片媒体变为 active 且 sort_order=0 时，同步 SPU.main_image"""
    if instance.media_type != 'image':
        return
    if instance.sort_order != 0:
        return
    if instance.status != 'active':
        return
    if not instance.spu_id:
        return
    if not instance.large_url:
        return

    spu = SPU.objects.filter(id=instance.spu_id).first()
    if spu and spu.main_image != instance.large_url:
        SPU.objects.filter(id=instance.spu_id).update(main_image=instance.large_url)
        logger.info(f'信号: 已同步 SPU#{instance.spu_id} main_image: {instance.large_url}')
