"""
填充过去 7 天的平台/商品每日指标数据。

用法：
    python manage.py seed_daily_metrics [--days=7]

数据生成策略：
  - 按 (平台, 日期) 做种子生成稳定的伪数据（同一天同一平台数据不变）
  - 平台级：search_volume, click_volume, order_volume, conversion_rate
  - 商品级：同上，但按 (平台, 商品, 日期) 做种子
  - 转化率 = order / click * 100
"""
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ads.models import AdPlatform, AdPlatformDailyMetric, AdProductDailyMetric
from apps.goods.models import SPU, SPUStatus


def _seeded_random(seed_str: str) -> random.Random:
    """用字符串种子生成稳定的随机数（同一种子同一天数据不变）。"""
    seed_int = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_int)


class Command(BaseCommand):
    help = '填充过去 N 天的平台/商品每日指标数据（默认 7 天）'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='填充天数（默认 7）')

    @transaction.atomic
    def handle(self, *args, **options):
        days = options['days']
        today = date.today()

        platforms = list(AdPlatform.objects.filter(is_active=True))
        if not platforms:
            self.stderr.write(self.style.ERROR('没有启用的平台'))
            return

        spus = list(
            SPU.objects
            .filter(status=SPUStatus.ON_SALE, deleted_at__isnull=True)
            .order_by('-id')[:10]
        )
        if not spus:
            self.stderr.write(self.style.ERROR('没有在售商品'))
            return

        self.stdout.write(f'填充 {days} 天数据，{len(platforms)} 个平台，{len(spus)} 个商品')

        # 平台级指标
        platform_metrics = []
        for platform in platforms:
            for i in range(days):
                d = today - timedelta(days=i)
                seed_str = f'{platform.code}-{d}'
                rng = _seeded_random(seed_str)

                base_search = 8000 + rng.randint(0, 4000)
                base_click = int(base_search * rng.uniform(0.12, 0.22))
                base_order = int(base_click * rng.uniform(0.03, 0.08))
                cvr = (base_order / base_click * 100) if base_click > 0 else 0

                platform_metrics.append(
                    AdPlatformDailyMetric(
                        platform=platform,
                        date=d,
                        search_volume=base_search,
                        click_volume=base_click,
                        order_volume=base_order,
                        conversion_rate=Decimal(str(round(cvr, 2))),
                    )
                )

        AdPlatformDailyMetric.objects.bulk_create(platform_metrics, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'写入 {len(platform_metrics)} 条平台每日指标'))

        # 商品级指标
        product_metrics = []
        for platform in platforms:
            for spu in spus:
                for i in range(days):
                    d = today - timedelta(days=i)
                    seed_str = f'{platform.code}-{spu.id}-{d}'
                    rng = _seeded_random(seed_str)

                    base_search = 400 + rng.randint(0, 900)
                    base_click = int(base_search * rng.uniform(0.10, 0.20))
                    base_order = int(base_click * rng.uniform(0.03, 0.07))
                    cvr = (base_order / base_click * 100) if base_click > 0 else 0

                    product_metrics.append(
                        AdProductDailyMetric(
                            platform=platform,
                            spu=spu,
                            date=d,
                            search_volume=base_search,
                            click_volume=base_click,
                            order_volume=base_order,
                            conversion_rate=Decimal(str(round(cvr, 2))),
                        )
                    )

        AdProductDailyMetric.objects.bulk_create(product_metrics, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'写入 {len(product_metrics)} 条商品每日指标'))
