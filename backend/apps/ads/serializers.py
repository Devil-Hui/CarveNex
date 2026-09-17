from decimal import Decimal

from rest_framework import serializers

from .models import AdCampaignRecord, AdHotProduct, AdHotSearch, AdMetricSnapshot, AdPlatform


class AdPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlatform
        fields = ['id', 'code', 'name', 'logo_url', 'sort_order']


class MetricSnapshotSerializer(serializers.ModelSerializer):
    change_pct = serializers.SerializerMethodField()

    class Meta:
        model = AdMetricSnapshot
        fields = ['metric_key', 'before_value', 'after_value', 'unit', 'lower_is_better', 'change_pct', 'updated_at']

    def get_change_pct(self, obj):
        if not obj.before_value:
            return None
        delta = (obj.after_value - obj.before_value) / obj.before_value * 100
        return round(float(delta), 2)


class HotSearchSerializer(serializers.ModelSerializer):
    platform_code = serializers.CharField(source='platform.code', read_only=True, default='')
    platform_name = serializers.CharField(source='platform.name', read_only=True, default='')

    class Meta:
        model = AdHotSearch
        fields = ['id', 'keyword', 'keyword_zh', 'keyword_ar', 'heat', 'trend', 'platform_code', 'platform_name']


class HotProductSerializer(serializers.ModelSerializer):
    spu_id = serializers.IntegerField(source='spu.id', read_only=True)
    spu_name = serializers.CharField(source='spu.name', read_only=True)
    spu_name_en = serializers.CharField(source='spu.name_en', read_only=True)
    spu_name_ar = serializers.CharField(source='spu.name_ar', read_only=True)
    spu_image = serializers.CharField(source='spu.main_image', read_only=True)

    class Meta:
        model = AdHotProduct
        fields = ['id', 'spu_id', 'spu_name', 'spu_name_en', 'spu_name_ar', 'spu_image',
                  'heat', 'reason', 'reason_zh', 'reason_ar']


class CampaignHistorySerializer(serializers.ModelSerializer):
    platform_code = serializers.CharField(source='platform.code', read_only=True)
    operator = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = AdCampaignRecord
        fields = ['id', 'spu_id', 'platform_code', 'amount', 'version', 'status',
                  'executed_at', 'note', 'operator', 'created_at']


class PlatformMetricSerializer(serializers.Serializer):
    """前台多平台指标面板：单平台一行。

    `metrics` 是当前快照（取自 series 最新一点），`series` 是近 N 天走势（用于迷你折线）。
    `trend` + `delta_pct` 用于在右侧徽章展示"今天 vs 昨天"的瞬时变化。
    """

    platform_code = serializers.CharField()
    platform_name = serializers.CharField()
    logo_url = serializers.CharField(allow_blank=True)
    metrics = serializers.DictField(child=serializers.FloatField())
    series = serializers.DictField(child=serializers.ListField(child=serializers.FloatField()))
    trend = serializers.DictField(child=serializers.CharField())
    delta_pct = serializers.DictField(child=serializers.FloatField())


class ProductWeeklyItemSerializer(serializers.Serializer):
    """单商品在指定平台上的本周指标（周一 ~ 今天）。"""

    spu_id = serializers.IntegerField()
    spu_name = serializers.CharField(allow_blank=True)
    spu_name_en = serializers.CharField(allow_blank=True)
    spu_name_ar = serializers.CharField(allow_blank=True)
    spu_image = serializers.CharField(allow_blank=True)
    metrics = serializers.DictField(child=serializers.FloatField())
    weekly = serializers.DictField(child=serializers.ListField(child=serializers.FloatField()))
    order_share = serializers.FloatField()


class CampaignSaveItemSerializer(serializers.Serializer):
    """单条保存项的入参校验：金额必须为非负、两位小数以内、带乐观锁版本号。"""

    MAX_AMOUNT = 999999.99

    spu_id = serializers.IntegerField(min_value=1)
    platform_code = serializers.CharField(max_length=32)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'))
    base_version = serializers.IntegerField(min_value=0)

    def validate_amount(self, value):
        if value > self.MAX_AMOUNT:
            raise serializers.ValidationError(f'金额超出上限 {self.MAX_AMOUNT}')
        return value
