# Generated manually: 后台「活动管理」功能下线。
# 删除折扣活动模型及其关联表（同时清理已有活动数据）：
#   - promotion_activity      （DiscountActivity）
#   - promotion_activity_sku  （ActivitySKURelation）
# 优惠券（Coupon / UserCoupon / PromoCode / CouponScope 等）保持不变。
# 依赖顺序：ActivitySKURelation 先删（其 FK 指向 DiscountActivity 与 goods.SKU），再删 DiscountActivity。

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('promotion', '0012_alter_discountactivity_type'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ActivitySKURelation',
        ),
        migrations.DeleteModel(
            name='DiscountActivity',
        ),
    ]