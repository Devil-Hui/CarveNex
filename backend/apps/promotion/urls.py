from django.urls import path
from .views import (
    ClaimCouponView, ClaimByPromoCodeView, CouponDetailView, CouponListView,
    PromoDetailView,
    GenerateCouponView, MyCouponView,
)
from .admin_views import (
    CouponAdminListView, CouponAdminDetailView,
    CouponScopeView,
    PromoCodeAdminListView, PromoCodeDashboardView, PromoCodeAdminDetailView,
)

urlpatterns = [
    # Public
    path('', CouponListView.as_view(), name='promotion-list'),
    path('generate/', GenerateCouponView.as_view(), name='promotion-generate'),
    path('my/', MyCouponView.as_view(), name='promotion-my'),
    path('<str:code>/', CouponDetailView.as_view(), name='promotion-detail'),
    path('<str:code>/claim/', ClaimCouponView.as_view(), name='promotion-claim'),
    path('promo/<str:code>/claim/', ClaimByPromoCodeView.as_view(), name='promotion-promo-claim'),
    path('promo/<str:code>/', PromoDetailView.as_view(), name='promotion-promo-detail'),

    # Admin Coupon CRUD
    path('coupon', CouponAdminListView.as_view(), name='promotion-coupon-admin'),
    path('coupon/create', CouponAdminListView.as_view(), name='promotion-coupon-create'),
    path('coupon/<int:pk>/update', CouponAdminDetailView.as_view(), name='promotion-coupon-update'),
    path('coupon/<int:pk>/delete', CouponAdminDetailView.as_view(), name='promotion-coupon-delete'),
    path('coupon/<int:pk>/scope', CouponScopeView.as_view(), name='promotion-coupon-scope'),
    path('coupon/<int:pk>/promo-codes', PromoCodeAdminListView.as_view(), name='promotion-promo-codes'),
    path('coupon/<int:pk>/promo-dashboard', PromoCodeDashboardView.as_view(), name='promotion-promo-dashboard'),
    path('coupon/promo/<int:pk>/', PromoCodeAdminDetailView.as_view(), name='promotion-promo-detail-admin'),
]
