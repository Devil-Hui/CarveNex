from django.urls import path

from .views import (
    AdminCampaignHistoryView,
    AdminCampaignMatrixView,
    AdminCampaignSaveView,
    AdminPlatformListView,
    HotProductListView,
    HotSearchListView,
    InsightOverviewView,
    PlatformMetricsView,
    ProductWeeklyView,
)

urlpatterns = [
    # 前台展示页（只读）
    path('insight/overview', InsightOverviewView.as_view(), name='ads-insight-overview'),
    path('insight/hot-searches', HotSearchListView.as_view(), name='ads-hot-searches'),
    path('insight/hot-products', HotProductListView.as_view(), name='ads-hot-products'),
    path('insight/platform-metrics', PlatformMetricsView.as_view(), name='ads-platform-metrics'),
    path('insight/product-weekly', ProductWeeklyView.as_view(), name='ads-product-weekly'),
    # 管理端投放操作
    path('admin/platforms', AdminPlatformListView.as_view(), name='ads-admin-platforms'),
    path('admin/campaigns', AdminCampaignMatrixView.as_view(), name='ads-admin-campaigns'),
    path('admin/campaigns/save', AdminCampaignSaveView.as_view(), name='ads-admin-campaigns-save'),
    path('admin/campaigns/history', AdminCampaignHistoryView.as_view(), name='ads-admin-campaigns-history'),
]
