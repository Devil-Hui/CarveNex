from rest_framework import serializers
from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    sku_id = serializers.IntegerField(source='sku.id', read_only=True)
    # 新契约主字段为 sku_name；sku_code 保留为向后兼容别名
    sku_name = serializers.CharField(source='sku.sku_name', read_only=True)
    sku_code = serializers.CharField(source='sku.sku_name', read_only=True)
    spu_name = serializers.CharField(source='sku.spu.name', read_only=True)
    # 多语言商品名：供前端按当前界面语言（en-US / ar）渲染购物车商品名称
    spu_name_en = serializers.CharField(source='sku.spu.name_en', read_only=True)
    spu_name_ar = serializers.CharField(source='sku.spu.name_ar', read_only=True)
    price = serializers.DecimalField(source='sku.price', max_digits=10, decimal_places=2, read_only=True)
    stock = serializers.IntegerField(source='sku.stock', read_only=True)
    # SKU 字段是 image_url；SKU 未单独配图时回退 SPU 主图（prefetch items__sku__spu，零额外查询）
    image = serializers.SerializerMethodField()
    spec_values = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'sku_id', 'sku_name', 'sku_code', 'spu_name', 'spu_name_en', 'spu_name_ar',
            'price', 'stock', 'image', 'spec_values', 'quantity', 'selected',
            'created_at',
        ]

    def get_image(self, obj):
        if obj.sku.image_url:
            return obj.sku.image_url
        spu = obj.sku.spu
        return (spu.main_image or '') if spu else ''

    def get_spec_values(self, obj):
        # 依赖 CartService.get_cart_with_items 的 prefetch；
        # 不要再链式 .select_related()，否则会绕过 prefetch 缓存变成 N+1。
        # SKUSpecValue 自带 spec_name FK，优先用它，避免再跳一层。
        return [
            {
                'spec_name': (
                    sv.spec_name.name if sv.spec_name_id
                    else (sv.spec_value.spec_name.name if sv.spec_value_id else '')
                ),
                'spec_value': sv.spec_value.value if sv.spec_value_id else '',
            }
            for sv in obj.sku.sku_spec_values.all()
        ]


class AddCartItemSerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(default=1, min_value=1, max_value=999)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0, max_value=999)


class SelectCartItemsSerializer(serializers.Serializer):
    item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )
