import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('goods', '0027_category_multilang_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdPlatform',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=32, unique=True, verbose_name='平台编码')),
                ('name', models.CharField(max_length=64, verbose_name='平台名称')),
                ('logo_url', models.CharField(blank=True, default='', max_length=500, verbose_name='Logo URL')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('is_active', models.BooleanField(default=True, verbose_name='启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '投放平台',
                'verbose_name_plural': '投放平台',
                'db_table': 'ads_platform',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='AdMetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_key', models.CharField(max_length=32, unique=True, verbose_name='指标键')),
                ('before_value', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='投放前数值')),
                ('after_value', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='投放后数值')),
                ('unit', models.CharField(blank=True, default='', max_length=16, verbose_name='单位')),
                ('lower_is_better', models.BooleanField(default=False, verbose_name='越低越好')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '效果对比指标',
                'verbose_name_plural': '效果对比指标',
                'db_table': 'ads_metric_snapshot',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='AdCampaignRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='投放金额')),
                ('version', models.PositiveIntegerField(verbose_name='版本号')),
                ('status', models.CharField(choices=[('executing', '执行中'), ('done', '已完成'), ('failed', '失败')], default='executing', max_length=20, verbose_name='执行状态')),
                ('executed_at', models.DateTimeField(blank=True, null=True, verbose_name='执行完成时间')),
                ('note', models.CharField(blank=True, default='', max_length=500, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ad_campaign_records', to=settings.AUTH_USER_MODEL, verbose_name='操作人')),
                ('platform', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campaigns', to='ads.adplatform', verbose_name='投放平台')),
                ('spu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ad_campaigns', to='goods.spu', verbose_name='商品')),
            ],
            options={
                'verbose_name': '投放记录',
                'verbose_name_plural': '投放记录',
                'db_table': 'ads_campaign_record',
                'ordering': ['-version', '-id'],
                'unique_together': {('spu', 'platform', 'version')},
                'indexes': [
                    models.Index(fields=['spu', 'platform', '-version'], name='ads_campaig_spu_id_6f6e6c_idx'),
                    models.Index(fields=['platform'], name='ads_campaig_platfor_1f2b53_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='AdHotSearch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyword', models.CharField(max_length=200, verbose_name='关键词（英文）')),
                ('keyword_zh', models.CharField(blank=True, default='', max_length=200, verbose_name='关键词（中文）')),
                ('keyword_ar', models.CharField(blank=True, default='', max_length=200, verbose_name='关键词（阿语）')),
                ('heat', models.PositiveIntegerField(default=0, verbose_name='热度分')),
                ('trend', models.CharField(choices=[('up', '上升'), ('flat', '持平'), ('down', '下降')], default='flat', max_length=8, verbose_name='趋势')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('is_active', models.BooleanField(default=True, verbose_name='启用')),
                ('platform', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hot_searches', to='ads.adplatform', verbose_name='来源平台')),
            ],
            options={
                'verbose_name': '热搜词',
                'verbose_name_plural': '热搜词',
                'db_table': 'ads_hot_search',
                'ordering': ['sort_order', '-heat'],
            },
        ),
        migrations.CreateModel(
            name='AdHotProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('heat', models.PositiveIntegerField(default=0, verbose_name='热度分')),
                ('reason', models.CharField(blank=True, default='', max_length=200, verbose_name='上榜理由（英文）')),
                ('reason_zh', models.CharField(blank=True, default='', max_length=200, verbose_name='上榜理由（中文）')),
                ('reason_ar', models.CharField(blank=True, default='', max_length=200, verbose_name='上榜理由（阿语）')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('is_active', models.BooleanField(default=True, verbose_name='启用')),
                ('spu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ad_hot_entries', to='goods.spu', verbose_name='商品')),
            ],
            options={
                'verbose_name': '热榜商品',
                'verbose_name_plural': '热榜商品',
                'db_table': 'ads_hot_product',
                'ordering': ['sort_order', '-heat'],
                'unique_together': {('spu',)},
            },
        ),
    ]
