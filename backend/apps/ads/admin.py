from django.contrib import admin

from .models import AdCampaignRecord, AdHotProduct, AdHotSearch, AdMetricSnapshot, AdPlatform


@admin.register(AdPlatform)
class AdPlatformAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'name', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']


@admin.register(AdMetricSnapshot)
class AdMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ['metric_key', 'before_value', 'after_value', 'unit', 'lower_is_better', 'updated_at']


@admin.register(AdHotSearch)
class AdHotSearchAdmin(admin.ModelAdmin):
    list_display = ['id', 'keyword', 'heat', 'trend', 'platform', 'sort_order', 'is_active']
    list_editable = ['heat', 'trend', 'sort_order', 'is_active']


@admin.register(AdHotProduct)
class AdHotProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'spu', 'heat', 'sort_order', 'is_active']
    list_editable = ['heat', 'sort_order', 'is_active']


@admin.register(AdCampaignRecord)
class AdCampaignRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'spu', 'platform', 'amount', 'version', 'status', 'created_by', 'created_at']
    list_filter = ['platform', 'status']
    readonly_fields = ['spu', 'platform', 'amount', 'version', 'status', 'executed_at', 'created_by', 'created_at']
