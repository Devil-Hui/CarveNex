from decimal import Decimal

from rest_framework import serializers
from .models import (
    Coupon,
    PromoCode,
    UserCoupon,
)


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'name', 'code', 'discount_type', 'amount', 'min_amount',
                  'max_discount', 'stackable', 'per_user_limit',
                  'total_count', 'claimed_count',
                  'start_time', 'end_time', 'is_active', 'created_at']


class CouponAdminSerializer(serializers.ModelSerializer):
    # 防御：total_count / per_user_limit 缺失或 <1 时直接校验拦截，避免无效数量。
    total_count = serializers.IntegerField(min_value=1, required=False, default=1000)
    per_user_limit = serializers.IntegerField(min_value=1, required=False, default=1)

    class Meta:
        model = Coupon
        fields = ['id', 'name', 'code', 'discount_type', 'amount', 'min_amount',
                  'max_discount', 'stackable', 'per_user_limit',
                  'total_count', 'claimed_count',
                  'start_time', 'end_time', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """兼容 discount_value → amount 字段别名"""
        if 'discount_value' in self.initial_data and 'amount' not in attrs:
            attrs['amount'] = self.initial_data['discount_value']
        if 'discount' in self.initial_data and 'amount' not in attrs:
            attrs['amount'] = self.initial_data['discount']
        return attrs


class PromoCodeSerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    class Meta:
        model = PromoCode
        fields = [
            'id', 'coupon', 'coupon_code', 'code', 'name', 'note', 'is_active',
            'claim_count', 'paid_order_count', 'gmv', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'coupon', 'coupon_code', 'claim_count', 'paid_order_count',
            'gmv', 'created_by_name', 'created_at', 'updated_at',
        ]


class PromoCodeDetailSerializer(PromoCodeSerializer):
    unique_users = serializers.IntegerField(read_only=True)

    class Meta(PromoCodeSerializer.Meta):
        fields = PromoCodeSerializer.Meta.fields + ['unique_users']


class PromoCodeCreateSerializer(serializers.Serializer):
    """推广码创建参数（8.3 严谨化）：
    - name 必填：推广码必须归属一个推广人/渠道，否则无意义；
    - prefix 仅允许大写字母+数字（0-8 位），为空则纯随机；
    - codes 可选：显式指定码值时同样必须给 name。
    """
    codes = serializers.ListField(
        child=serializers.CharField(max_length=32), required=False, allow_empty=True,
    )
    count = serializers.IntegerField(min_value=1, max_value=200, default=1, required=False)
    prefix = serializers.CharField(max_length=8, required=False, allow_blank=True, default='')
    name = serializers.CharField(max_length=128, required=True, allow_blank=False,
                                 error_messages={'blank': '推广码必须绑定推广人/渠道名称', 'required': '推广码必须绑定推广人/渠道名称'},
                                 help_text='推广人/渠道名称（必填），如：代言人A、直播间、线下门店')
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_prefix(self, value):
        value = (value or '').strip().upper()
        import re as _re
        if value and not _re.fullmatch(r'[A-Z0-9]{1,8}', value):
            raise serializers.ValidationError('前缀仅允许大写字母与数字（0-8 位），如 CN、VIP')
        return value

    def validate(self, attrs):
        if not (attrs.get('codes') or attrs.get('count')):
            raise serializers.ValidationError('需提供 codes 或 count')
        return attrs


class UserCouponSerializer(serializers.ModelSerializer):
    coupon = CouponSerializer(read_only=True)
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta:
        model = UserCoupon
        fields = ['id', 'coupon', 'promo_code', 'status', 'claimed_at', 'used_at', 'used_order_no']


class ClaimCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)


class GenerateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, required=False)
    discount_type = serializers.ChoiceField(choices=['fixed', 'percent'])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    min_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    total_count = serializers.IntegerField(default=1000, min_value=1)
    stackable = serializers.BooleanField(default=False)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
