# Generated manually: rename goods.SKU.sku_code → sku_name (data-preserving)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0023_spu_english_fields'),
    ]

    operations = [
        # RenameField 保证已有数据不丢（仅改列名）
        migrations.RenameField(
            model_name='sku',
            old_name='sku_code',
            new_name='sku_name',
        ),
    ]