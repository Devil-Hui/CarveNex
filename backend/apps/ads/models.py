"""
推广投放（推广精投）数据模型。

设计要点：
  1. AdCampaignRecord 采用「不可变版本链」：每次保存追加一条新 version 记录，
     当前生效值 = 该 (spu, platform) 下 version 最大的一条；历史版本天然保留，
     上一版金额 = version 次大的一条。不做 UPDATE，避免并发互相覆盖后无迹可查。
  2. AdMetricSnapshot / AdHotSearch / AdHotProduct 为前台展示页数据源，
     由后台配置（Django admin 或后续运营界面），前台只读。
"""
from django.db import models


class AdPlatform(models.Model):
    """海外投放平台配置（TikTok / Meta / Google / Amazon / Shopee 等）。"""

    code = models.CharField(max_length=32, unique=True, verbose_name='平台编码')
    name = models.CharField(max_length=64, verbose_name='平台名称')
    logo_url = models.CharField(max_length=500, blank=True, default='', verbose_name='Logo URL')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ads_platform'
        verbose_name = '投放平台'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.name}({self.code})'


class CampaignStatus(models.TextChoices):
    EXECUTING = 'executing', '执行中'
    DONE = 'done', '已完成'
    FAILED = 'failed', '失败'


class AdCampaignRecord(models.Model):
    """投放记录（版本链）。amount 为单平台单商品的投放金额（USD）。"""

    spu = models.ForeignKey(
        'goods.SPU', on_delete=models.CASCADE, related_name='ad_campaigns',
        verbose_name='商品',
    )
    platform = models.ForeignKey(
        AdPlatform, on_delete=models.CASCADE, related_name='campaigns',
        verbose_name='投放平台',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='投放金额')
    version = models.PositiveIntegerField(verbose_name='版本号')
    status = models.CharField(
        max_length=20, choices=CampaignStatus.choices,
        default=CampaignStatus.EXECUTING, verbose_name='执行状态',
    )
    executed_at = models.DateTimeField(null=True, blank=True, verbose_name='执行完成时间')
    note = models.CharField(max_length=500, blank=True, default='', verbose_name='备注')
    created_by = models.ForeignKey(
        'auth.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='ad_campaign_records', verbose_name='操作人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ads_campaign_record'
        verbose_name = '投放记录'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        unique_together = [('spu', 'platform', 'version')]
        ordering = ['-version', '-id']
        indexes = [
            models.Index(fields=['spu', 'platform', '-version']),
            models.Index(fields=['platform']),
        ]

    def __str__(self):
        return f'{self.spu_id}@{self.platform.code} v{self.version} ${self.amount}'


class AdMetricSnapshot(models.Model):
    """前台「效果对比」指标快照：投放前(before) vs 精准投放后(after)。"""

    metric_key = models.CharField(max_length=32, unique=True, verbose_name='指标键')
    before_value = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='投放前数值')
    after_value = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='投放后数值')
    unit = models.CharField(max_length=16, blank=True, default='', verbose_name='单位')
    lower_is_better = models.BooleanField(default=False, verbose_name='越低越好')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ads_metric_snapshot'
        verbose_name = '效果对比指标'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        ordering = ['id']

    def __str__(self):
        return f'{self.metric_key}: {self.before_value} -> {self.after_value}{self.unit}'


class AdHotSearch(models.Model):
    """智能化热搜词（前台展示页）。"""

    TREND_CHOICES = (('up', '上升'), ('flat', '持平'), ('down', '下降'))

    keyword = models.CharField(max_length=200, verbose_name='关键词（英文）')
    keyword_zh = models.CharField(max_length=200, blank=True, default='', verbose_name='关键词（中文）')
    keyword_ar = models.CharField(max_length=200, blank=True, default='', verbose_name='关键词（阿语）')
    heat = models.PositiveIntegerField(default=0, verbose_name='热度分')
    trend = models.CharField(max_length=8, choices=TREND_CHOICES, default='flat', verbose_name='趋势')
    platform = models.ForeignKey(
        AdPlatform, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='hot_searches', verbose_name='来源平台',
    )
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        db_table = 'ads_hot_search'
        verbose_name = '热搜词'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        ordering = ['sort_order', '-heat']

    def __str__(self):
        return f'{self.keyword}({self.heat})'


class AdHotProduct(models.Model):
    """商品热榜（前台展示页）：关联商品库 SPU，配图与名称实时取商品侧。"""

    spu = models.ForeignKey(
        'goods.SPU', on_delete=models.CASCADE, related_name='ad_hot_entries',
        verbose_name='商品',
    )
    heat = models.PositiveIntegerField(default=0, verbose_name='热度分')
    reason = models.CharField(max_length=200, blank=True, default='', verbose_name='上榜理由（英文）')
    reason_zh = models.CharField(max_length=200, blank=True, default='', verbose_name='上榜理由（中文）')
    reason_ar = models.CharField(max_length=200, blank=True, default='', verbose_name='上榜理由（阿语）')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        db_table = 'ads_hot_product'
        verbose_name = '热榜商品'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        ordering = ['sort_order', '-heat']
        unique_together = [('spu',)]

    def __str__(self):
        return f'{self.spu_id} heat={self.heat}'


class AdPlatformDailyMetric(models.Model):
    """平台每日指标聚合（按平台+日期）。

    用于前台展示页的"多平台实时指标"和"商品周数据"。
    由定时任务或管理命令每日聚合生成，前台只读。
    """

    platform = models.ForeignKey(
        AdPlatform, on_delete=models.CASCADE, related_name='daily_metrics',
        verbose_name='投放平台',
    )
    date = models.DateField(verbose_name='日期')
    search_volume = models.PositiveIntegerField(default=0, verbose_name='搜索量')
    click_volume = models.PositiveIntegerField(default=0, verbose_name='点击量')
    order_volume = models.PositiveIntegerField(default=0, verbose_name='订单量')
    conversion_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='转化率(%)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ads_platform_daily_metric'
        verbose_name = '平台每日指标'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        unique_together = [('platform', 'date')]
        ordering = ['-date']

    def __str__(self):
        return f'{self.platform.code} {self.date} search={self.search_volume}'


class AdProductDailyMetric(models.Model):
    """商品每日指标聚合（按平台+商品+日期）。

    用于前台展示页的"商品周数据"。
    """

    platform = models.ForeignKey(
        AdPlatform, on_delete=models.CASCADE, related_name='product_daily_metrics',
        verbose_name='投放平台',
    )
    spu = models.ForeignKey(
        'goods.SPU', on_delete=models.CASCADE, related_name='ad_daily_metrics',
        verbose_name='商品',
    )
    date = models.DateField(verbose_name='日期')
    search_volume = models.PositiveIntegerField(default=0, verbose_name='搜索量')
    click_volume = models.PositiveIntegerField(default=0, verbose_name='点击量')
    order_volume = models.PositiveIntegerField(default=0, verbose_name='订单量')
    conversion_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='转化率(%)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ads_product_daily_metric'
        verbose_name = '商品每日指标'
        verbose_name_plural = verbose_name
        app_label = 'ads'
        unique_together = [('platform', 'spu', 'date')]
        ordering = ['-date']

    def __str__(self):
        return f'{self.platform.code} spu={self.spu_id} {self.date} search={self.search_volume}'
