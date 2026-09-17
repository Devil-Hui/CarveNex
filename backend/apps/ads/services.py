"""
推广投放业务服务层。

并发约定：
  保存投放金额时，先 `SPU.objects.select_for_update()` 锁住商品行（必然存在），
  把同一商品的并发保存串行化；再比对客户端携带的 base_version 做乐观锁，
  版本不一致返回冲突列表，由前端提示刷新。投放记录只 INSERT 不 UPDATE，
  天然保留完整历史版本。

投放执行：
  `_execute_campaign` 当前为同步占位实现（直接置 done）。接入真实平台
  （TikTok/Meta/Google Ads API）时替换为异步任务 + 回写 status。
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.goods.models import SPU, SPUStatus

from .models import (
    AdCampaignRecord, AdHotProduct, AdHotSearch, AdMetricSnapshot, AdPlatform,
    AdPlatformDailyMetric, AdProductDailyMetric, CampaignStatus,
)


class CampaignConflict(Exception):
    """base_version 与当前最新版本不一致（他人已先保存）。"""

    def __init__(self, platform_code: str, current_version: int):
        super().__init__(platform_code)
        self.platform_code = platform_code
        self.current_version = current_version


def _execute_campaign(record: AdCampaignRecord) -> None:
    """执行投放（占位实现）。真实接入时在此调用各平台 Marketing API。"""
    record.status = CampaignStatus.DONE
    record.executed_at = timezone.now()
    record.save(update_fields=['status', 'executed_at'])


class CampaignService:
    """管理端：投放矩阵读取 / 批量保存 / 历史查询。"""

    @staticmethod
    def list_platforms():
        return AdPlatform.objects.filter(is_active=True)

    @staticmethod
    def _latest_map(spu_ids, platform_ids):
        """{(spu_id, platform_id): [最新记录, 上一版记录]}，两次遍历完成，避免 N+1。"""
        records = (
            AdCampaignRecord.objects
            .filter(spu_id__in=spu_ids, platform_id__in=platform_ids)
            .order_by('spu_id', 'platform_id', '-version')
        )
        result: dict[tuple[int, int], list] = {}
        for rec in records:
            key = (rec.spu_id, rec.platform_id)
            bucket = result.setdefault(key, [])
            if len(bucket) < 2:
                bucket.append(rec)
        return result

    @classmethod
    def build_matrix(cls, page: int, per_page: int):
        """投放矩阵：行=在售商品（分页），列=启用平台，格=当前金额+上一版金额+版本号。"""
        platforms = list(cls.list_platforms())
        spu_qs = (
            SPU.objects
            .filter(status=SPUStatus.ON_SALE, deleted_at__isnull=True)
            .order_by('-id')
        )
        total = spu_qs.count()
        spus = list(spu_qs[(page - 1) * per_page: page * per_page])
        latest = cls._latest_map(
            [s.id for s in spus],
            [p.id for p in platforms],
        )

        rows = []
        for spu in spus:
            cells = {}
            for p in platforms:
                versions = latest.get((spu.id, p.id), [])
                current = versions[0] if versions else None
                previous = versions[1] if len(versions) > 1 else None
                cells[p.code] = {
                    'amount': str(current.amount) if current else None,
                    'prev_amount': str(previous.amount) if previous else None,
                    'version': current.version if current else 0,
                    'status': current.status if current else None,
                }
            rows.append({
                'spu_id': spu.id,
                'spu_name': spu.name,
                'spu_name_en': spu.name_en,
                'spu_name_ar': spu.name_ar,
                'spu_image': spu.main_image,
                'cells': cells,
            })
        return rows, total, platforms

    @classmethod
    @transaction.atomic
    def save_batch(cls, items, user) -> list[AdCampaignRecord]:
        """批量保存：任一冲突即整批回滚，保证矩阵写入的原子性。"""
        saved = []
        for item in items:
            saved.append(cls._save_one(item, user))
        for record in saved:
            _execute_campaign(record)
        return saved

    @classmethod
    def _save_one(cls, item, user) -> AdCampaignRecord:
        spu_id = item['spu_id']
        platform_code = item['platform_code']
        amount: Decimal = item['amount']
        base_version: int = item['base_version']

        # 行锁：串行化同一商品的并发保存（SPU 行必然存在，不存在即参数错误）
        spu = SPU.objects.select_for_update().get(pk=spu_id, deleted_at__isnull=True)
        platform = AdPlatform.objects.get(code=platform_code, is_active=True)

        latest = (
            AdCampaignRecord.objects
            .filter(spu=spu, platform=platform)
            .order_by('-version')
            .first()
        )
        current_version = latest.version if latest else 0
        if base_version != current_version:
            raise CampaignConflict(platform_code, current_version)
        # 幂等：金额未变时不产生新版本，直接复用当前记录
        if latest and latest.amount == amount:
            return latest

        return AdCampaignRecord.objects.create(
            spu=spu,
            platform=platform,
            amount=amount,
            version=current_version + 1,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
        )

    @staticmethod
    def history(spu_id: int, platform_code: str):
        return (
            AdCampaignRecord.objects
            .filter(spu_id=spu_id, platform__code=platform_code)
            .select_related('platform', 'created_by')
            .order_by('-version')[:50]
        )


class InsightService:
    """前台展示页：效果对比 / 智能热搜 / 商品热榜（全部只读）。"""

    @staticmethod
    def overview():
        return list(AdMetricSnapshot.objects.all())

    @staticmethod
    def hot_searches(limit: int = 10):
        return list(
            AdHotSearch.objects
            .filter(is_active=True)
            .select_related('platform')[:limit]
        )

    @staticmethod
    def hot_products(limit: int = 8):
        return list(
            AdHotProduct.objects
            .filter(is_active=True, spu__deleted_at__isnull=True)
            .select_related('spu')[:limit]
        )

    @staticmethod
    def product_weekly(platform_code: str, limit: int = 6):
        """指定平台下商品的一周指标（周一 ~ 今天）。

        返回 (platform, day_labels, items)；平台不存在返回 (None, [], [])。

        动态天数：今天周几就显示几天（今天周四 = 4 天，明天周五 = 5 天）。
        从 AdProductDailyMetric 真实表查询，无数据时回退到伪数据。
        """
        from datetime import date, timedelta

        platform = AdPlatform.objects.filter(code=platform_code, is_active=True).first()
        if not platform:
            return None, [], []

        # 商品池：热榜优先，空则取在售商品
        hot = list(
            AdHotProduct.objects
            .filter(is_active=True, spu__deleted_at__isnull=True)
            .select_related('spu')[:limit]
        )
        spus = [h.spu for h in hot]
        if not spus:
            spus = list(
                SPU.objects
                .filter(status=SPUStatus.ON_SALE, deleted_at__isnull=True)
                .order_by('-id')[:limit]
            )
        if not spus:
            return platform, [], []

        # 动态天数：今天周几就显示几天
        today = date.today()
        weekday = today.weekday()  # Mon=0
        day_count = weekday + 1
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        dates = [today - timedelta(days=weekday - i) for i in range(day_count)]
        day_labels = [f"{day_names[d.weekday()]} {d.month}/{d.day}" for d in dates]

        # 从真实表查询
        spu_ids = [s.id for s in spus]
        metrics_qs = (
            AdProductDailyMetric.objects
            .filter(platform=platform, spu_id__in=spu_ids, date__in=dates)
            .order_by('spu_id', 'date')
        )
        metrics_by_spu: dict[int, list] = {}
        for m in metrics_qs:
            metrics_by_spu.setdefault(m.spu_id, []).append(m)

        items = []
        total_order = 0.0
        for spu in spus:
            daily = metrics_by_spu.get(spu.id, [])
            if not daily:
                # 无真实数据，用伪数据兜底
                daily = InsightService._fallback_product_daily(platform, spu, dates)

            s_search = [float(m.search_volume) for m in daily]
            s_click = [float(m.click_volume) for m in daily]
            s_order = [float(m.order_volume) for m in daily]

            cur_search = s_search[-1] if s_search else 0
            cur_click = s_click[-1] if s_click else 0
            cur_order = s_order[-1] if s_order else 0
            cur_cvr = (cur_order / cur_click * 100) if cur_click > 0 else 0
            total_order += cur_order

            items.append({
                'spu_id': spu.id,
                'spu_name': spu.name,
                'spu_name_en': spu.name_en,
                'spu_name_ar': spu.name_ar,
                'spu_image': spu.main_image,
                'metrics': {
                    'search': round(cur_search, 1),
                    'click': round(cur_click, 1),
                    'order': round(cur_order, 1),
                    'conversion_rate': round(cur_cvr, 2),
                },
                'weekly': {'search': s_search, 'click': s_click, 'order': s_order},
                'order_share': 0.0,
            })

        if total_order > 0:
            for item in items:
                item['order_share'] = round(item['metrics']['order'] / total_order, 4)

        return platform, day_labels, items

    @staticmethod
    def _fallback_product_daily(platform, spu, dates):
        """伪数据兜底：按 (平台, 商品, 日期) 做种子生成稳定数据。"""
        import hashlib

        items = []
        seed_key = f'{platform.code}-{spu.id}'
        seed = int(hashlib.md5(seed_key.encode()).hexdigest(), 16)
        base_search = 400 + (seed % 900)

        for i, d in enumerate(dates):
            h = int(hashlib.md5(f'{seed_key}-{d}'.encode()).hexdigest(), 16)
            pct = ((h % 6000) - 3000) / 10000.0
            v_search = base_search * (1 + pct)
            v_click = v_search * (0.14 + (seed % 10) / 100.0)
            v_order = v_click * (0.04 + (seed % 6) / 100.0)
            items.append(AdProductDailyMetric(
                platform=platform,
                spu=spu,
                date=d,
                search_volume=int(v_search),
                click_volume=int(v_click),
                order_volume=int(v_order),
                conversion_rate=round(v_order / v_click * 100, 2) if v_click > 0 else 0,
            ))
        return items

    @staticmethod
    def platform_metrics(days: int = 7):
        """每个平台返回：当前 4 个核心指标 + 每个指标近 N 天走势 + 涨跌方向 + 涨跌幅。

        从 AdPlatformDailyMetric 真实表查询，无数据时回退到伪数据。
        动态天数：今天周几就显示几天（今天周四 = 4 天，明天周五 = 5 天）。
        """
        from datetime import date, timedelta

        today = date.today()
        weekday = today.weekday()  # Mon=0
        day_count = weekday + 1
        dates = [today - timedelta(days=weekday - i) for i in range(day_count)]

        platforms = list(AdPlatform.objects.filter(is_active=True).order_by('sort_order', 'id'))
        if not platforms:
            return []

        # 从真实表查询
        metrics_qs = (
            AdPlatformDailyMetric.objects
            .filter(platform_id__in=[p.id for p in platforms], date__in=dates)
            .order_by('platform_id', 'date')
        )
        metrics_by_platform: dict[int, list] = {}
        for m in metrics_qs:
            metrics_by_platform.setdefault(m.platform_id, []).append(m)

        rows = []
        for platform in platforms:
            daily = metrics_by_platform.get(platform.id, [])
            if not daily:
                # 无真实数据，用伪数据兜底
                daily = InsightService._fallback_platform_daily(platform, dates)

            series_search = [float(m.search_volume) for m in daily]
            series_click = [float(m.click_volume) for m in daily]
            series_order = [float(m.order_volume) for m in daily]

            cur_search = series_search[-1] if series_search else 0
            cur_click = series_click[-1] if series_click else 0
            cur_order = series_order[-1] if series_order else 0
            cur_cvr = (cur_order / cur_click * 100) if cur_click > 0 else 0.0

            def _delta(series: list[float]) -> tuple[float, str]:
                """最近一点 vs 倒数第二点；单调上涨 → 'up'，下跌 → 'down'，持平 → 'flat'。"""
                if len(series) < 2:
                    return 0.0, 'flat'
                prev = series[-2]
                cur = series[-1]
                if prev <= 0:
                    return 0.0, 'flat'
                pct = (cur - prev) / prev * 100
                if pct > 0.5:
                    return round(pct, 2), 'up'
                if pct < -0.5:
                    return round(pct, 2), 'down'
                return round(pct, 2), 'flat'

            ds, ts = _delta(series_search)
            dc, tc = _delta(series_click)
            do, to = _delta(series_order)
            cvr_series = [
                (s_o / s_c * 100) if s_c > 0 else 0.0
                for s_o, s_c in zip(series_order, series_click)
            ]
            dcv, tcv = _delta(cvr_series)

            rows.append({
                'platform_code': platform.code,
                'platform_name': platform.name,
                'logo_url': platform.logo_url,
                'metrics': {
                    'search': round(cur_search, 1),
                    'click': round(cur_click, 1),
                    'order': round(cur_order, 1),
                    'conversion_rate': round(cur_cvr, 2),
                },
                'series': {
                    'search': series_search,
                    'click': series_click,
                    'order': series_order,
                    'conversion': cvr_series,
                },
                'trend': {'search': ts, 'click': tc, 'order': to, 'conversion': tcv},
                'delta_pct': {'search': ds, 'click': dc, 'order': do, 'conversion': dcv},
            })
        return rows

    @staticmethod
    def _fallback_platform_daily(platform, dates):
        """伪数据兜底：按 (平台, 日期) 做种子生成稳定数据。"""
        import hashlib

        items = []
        seed_base = hashlib.md5(platform.code.encode()).digest()
        for d in dates:
            k = f'{platform.code}-{d}'
            h = int(hashlib.md5(k.encode()).hexdigest(), 16)
            pct = ((h % 3300) - 1500) / 10000.0
            base_search = 8000 + (seed_base[0] % 20) * 1500
            base_click = int(base_search * (0.18 + ((seed_base[1] % 80) / 1000.0)))
            base_order = int(base_click * (0.05 + ((seed_base[2] % 50) / 1000.0)))
            items.append(AdPlatformDailyMetric(
                platform=platform,
                date=d,
                search_volume=int(base_search * (1 + pct)),
                click_volume=int(base_click * (1 + pct * 0.8)),
                order_volume=int(base_order * (1 + pct * 0.6)),
                conversion_rate=round(base_order / base_click * 100, 2) if base_click > 0 else 0,
            ))
        return items
