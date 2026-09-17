"""
seed_ads —— 推广投放模块初始数据。

幂等：全部按唯一键 get_or_create / update_or_create，重复执行不产生重复行。
内容：
  1. 5 个海外投放平台（TikTok / Meta / Google / Amazon / Shopee）
  2. 5 项效果对比指标（曝光量 / 点击率 / 转化率 / ROI / CPC）
  3. 10 条智能热搜词
  4. 热榜商品：取在售 SPU 前 8 个关联上榜（无在售商品时跳过）
"""
from django.core.management.base import BaseCommand

from apps.ads.models import AdHotProduct, AdHotSearch, AdMetricSnapshot, AdPlatform
from apps.goods.models import SPU, SPUStatus


PLATFORMS = [
    {'code': 'tiktok', 'name': 'TikTok', 'logo_url': '/static/images/platforms/tiktok.svg', 'sort_order': 1},
    {'code': 'meta', 'name': 'Meta', 'logo_url': '/static/images/platforms/meta.svg', 'sort_order': 2},
    {'code': 'google', 'name': 'Google', 'logo_url': '/static/images/platforms/google.svg', 'sort_order': 3},
    {'code': 'amazon', 'name': 'Amazon', 'logo_url': '/static/images/platforms/amazon.svg', 'sort_order': 4},
    {'code': 'shopee', 'name': 'Shopee', 'logo_url': '/static/images/platforms/shopee.svg', 'sort_order': 5},
]

METRICS = [
    {'metric_key': 'impressions', 'before_value': '128000', 'after_value': '486000', 'unit': '', 'lower_is_better': False},
    {'metric_key': 'ctr', 'before_value': '1.20', 'after_value': '3.85', 'unit': '%', 'lower_is_better': False},
    {'metric_key': 'cvr', 'before_value': '0.80', 'after_value': '2.40', 'unit': '%', 'lower_is_better': False},
    {'metric_key': 'roi', 'before_value': '1.60', 'after_value': '4.80', 'unit': 'x', 'lower_is_better': False},
    {'metric_key': 'cpc', 'before_value': '1.85', 'after_value': '0.62', 'unit': '$', 'lower_is_better': True},
]

HOT_SEARCHES = [
    {'keyword': 'laser engraver', 'keyword_zh': '激光雕刻机', 'keyword_ar': 'آلة النقش بالليزر', 'heat': 9860, 'trend': 'up', 'platform': 'google'},
    {'keyword': 'portable laser engraver', 'keyword_zh': '便携激光雕刻机', 'keyword_ar': 'آلة نقش ليزر محمولة', 'heat': 8740, 'trend': 'up', 'platform': 'tiktok'},
    {'keyword': 'wood engraving machine', 'keyword_zh': '木材雕刻机', 'keyword_ar': 'آلة نقش الخشب', 'heat': 7620, 'trend': 'up', 'platform': 'amazon'},
    {'keyword': 'metal laser marker', 'keyword_zh': '金属激光打标机', 'keyword_ar': 'جهاز وسم المعادن بالليزر', 'heat': 6980, 'trend': 'flat', 'platform': 'google'},
    {'keyword': 'diy laser cutter', 'keyword_zh': 'DIY 激光切割机', 'keyword_ar': 'قاطع ليزر يدوي', 'heat': 6410, 'trend': 'up', 'platform': 'tiktok'},
    {'keyword': 'jewelry engraving', 'keyword_zh': '珠宝雕刻', 'keyword_ar': 'نقش المجوهرات', 'heat': 5870, 'trend': 'up', 'platform': 'meta'},
    {'keyword': 'leather engraving tool', 'keyword_zh': '皮革雕刻工具', 'keyword_ar': 'أداة نقش الجلود', 'heat': 5230, 'trend': 'flat', 'platform': 'amazon'},
    {'keyword': 'laserpecker', 'keyword_zh': 'LaserPecker 啄木鸟', 'keyword_ar': 'ليزر بيكر', 'heat': 4920, 'trend': 'up', 'platform': 'google'},
    {'keyword': 'acrylic engraving', 'keyword_zh': '亚克力雕刻', 'keyword_ar': 'نقش الأكريليك', 'heat': 4350, 'trend': 'down', 'platform': 'shopee'},
    {'keyword': 'gift customization', 'keyword_zh': '礼品定制', 'keyword_ar': 'تخصيص الهدايا', 'heat': 3980, 'trend': 'up', 'platform': 'meta'},
]

HOT_PRODUCT_REASONS = [
    ('Best seller in engraving', '雕刻品类热销第一', 'الأكثر مبيعاً في النقش'),
    ('High conversion on TikTok', 'TikTok 转化率领先', 'تحويل مرتفع على تيك توك'),
    ('Top searched this week', '本周搜索热度榜首', 'الأكثر بحثاً هذا الأسبوع'),
    ('Repeat purchase favorite', '复购率明星单品', 'مفضل لإعادة الشراء'),
    ('Rising star in DIY niche', 'DIY 圈层上升新星', 'نجم صاعد في مجال الأعمال اليدوية'),
    ('Best ROI performer', 'ROI 表现最佳', 'أفضل أداء للعائد على الاستثمار'),
    ('Trending in gift season', '礼品季趋势单品', 'رائج في موسم الهدايا'),
    ('Top rated by creators', '创作者评分最高', 'الأعلى تقييماً من المبدعين'),
]


class Command(BaseCommand):
    help = '初始化推广投放模块数据（平台 / 对比指标 / 热搜词 / 热榜商品）'

    def handle(self, *args, **options):
        platform_objs = {}
        for item in PLATFORMS:
            obj, created = AdPlatform.objects.update_or_create(
                code=item['code'],
                defaults={'name': item['name'], 'logo_url': item['logo_url'], 'sort_order': item['sort_order']},
            )
            platform_objs[item['code']] = obj
            self.stdout.write(f"{'+' if created else '='} platform {obj.code}")

        for item in METRICS:
            AdMetricSnapshot.objects.update_or_create(
                metric_key=item['metric_key'],
                defaults={
                    'before_value': item['before_value'],
                    'after_value': item['after_value'],
                    'unit': item['unit'],
                    'lower_is_better': item['lower_is_better'],
                },
            )
        self.stdout.write(f'= metrics x{len(METRICS)}')

        for idx, item in enumerate(HOT_SEARCHES):
            AdHotSearch.objects.update_or_create(
                keyword=item['keyword'],
                defaults={
                    'keyword_zh': item['keyword_zh'],
                    'keyword_ar': item['keyword_ar'],
                    'heat': item['heat'],
                    'trend': item['trend'],
                    'platform': platform_objs.get(item['platform']),
                    'sort_order': idx,
                },
            )
        self.stdout.write(f'= hot searches x{len(HOT_SEARCHES)}')

        spus = list(
            SPU.objects
            .filter(status=SPUStatus.ON_SALE, deleted_at__isnull=True)
            .order_by('-id')[:8]
        )
        if not spus:
            self.stdout.write(self.style.WARNING('无在售商品，跳过热榜 seed'))
            return
        for idx, spu in enumerate(spus):
            reason, reason_zh, reason_ar = HOT_PRODUCT_REASONS[idx % len(HOT_PRODUCT_REASONS)]
            AdHotProduct.objects.update_or_create(
                spu=spu,
                defaults={
                    'heat': 9600 - idx * 700,
                    'reason': reason,
                    'reason_zh': reason_zh,
                    'reason_ar': reason_ar,
                    'sort_order': idx,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'= hot products x{len(spus)} (done)'))
