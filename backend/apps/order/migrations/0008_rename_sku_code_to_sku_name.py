# Generated manually: rename order.OrderItem.sku_code → sku_name (data-preserving)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0007_alter_order_payment_method'),
    ]

    operations = [
        # RenameField 保证已有订单项快照数据不丢（仅改列名）
        migrations.RenameField(
            model_name='orderitem',
            old_name='sku_code',
            new_name='sku_name',
        ),
    ]