from rest_framework import serializers


class ProductSearchSerializer(serializers.Serializer):
    """Product search request serializer."""
    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    category_id = serializers.IntegerField(required=False)
    brand_id = serializers.IntegerField(required=False)
    # 前端用 price_min/price_max，旧调用方可能用 min_price/max_price —— 两种都接受，归一化后统一输出
    price_min = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    price_max = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    min_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    max_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)
    sort = serializers.CharField(required=False, default='-created_at')
    status = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        # 旧命名 min_price/max_price 归一为 price_min/price_max，交给查询服务统一处理
        if isinstance(data, dict):
            data = data.copy()
            if 'min_price' in data and 'price_min' not in data:
                data['price_min'] = data['min_price']
                del data['min_price']
            if 'max_price' in data and 'price_max' not in data:
                data['price_max'] = data['max_price']
                del data['max_price']
        return super().to_internal_value(data)