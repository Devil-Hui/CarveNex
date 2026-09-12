from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from utils.cache import Cache

from utils.api_base_view import BaseApiView, PublicApiView
from utils.response_codes import Messages
from apps.rbac.permissions import HasPerm
from .models import Coupon, PromoCode
from .serializers import (
    ClaimCouponSerializer, CouponSerializer,
    GenerateCouponSerializer, UserCouponSerializer,
    PromoCodeCreateSerializer, PromoCodeDetailSerializer, PromoCodeSerializer,
)
from .services import PromotionService, PromoCodeService


class CouponListView(PublicApiView):
    """可领取的优惠券列表，公开访问。"""

    @extend_schema(responses={200: CouponSerializer(many=True)})
    def get(self, request):
        return Response(CouponSerializer(PromotionService.list_available(), many=True).data)


class CouponDetailView(PublicApiView):
    """公开优惠券分享详情，游客可查看。"""

    @extend_schema(responses={200: CouponSerializer})
    def get(self, request, code):
        try:
            detail = PromotionService.get_public_detail(code)
        except ValueError as exc:
            if str(exc) == 'COUPON_NOT_FOUND':
                return Response(
                    {'detail': Messages.COUPON_NOT_FOUND},
                    status=status.HTTP_404_NOT_FOUND,
                )
            raise
        return Response(detail)


class MyCouponView(BaseApiView):
    """当前用户已领取的优惠券。"""

    @extend_schema(
        responses={200: UserCouponSerializer(many=True)},
    )
    @extend_schema(responses={200: OpenApiResponse(description='List or retrieve')})
    def get(self, request):
        status_filter = request.query_params.get('status')
        user_coupons = PromotionService.list_user_coupons(request.user, status=status_filter)
        return Response(UserCouponSerializer(user_coupons, many=True).data)


class ClaimCouponView(BaseApiView):
    """通过券码领取优惠券。"""

    @extend_schema(request=None, responses={200: OpenApiResponse(description='coupon claimed')})
    def post(self, request, code):
        try:
            PromotionService.claim(request.user, code)
        except ValueError as e:
            error_map = {
                'COUPON_NOT_FOUND': (Messages.COUPON_NOT_FOUND, status.HTTP_404_NOT_FOUND),
                'COUPON_UNAVAILABLE': (Messages.COUPON_UNAVAILABLE, status.HTTP_400_BAD_REQUEST),
                'COUPON_LIMIT_REACHED': (Messages.COUPON_LIMIT_REACHED, status.HTTP_400_BAD_REQUEST),
                'COUPON_AUDIENCE_MISMATCH': (
                    Messages.COUPON_AUDIENCE_MISMATCH,
                    status.HTTP_403_FORBIDDEN,
                ),
            }
            if str(e) in error_map:
                msg, code = error_map[str(e)]
                return Response({'detail': msg}, status=code)
            raise
        return Response({'detail': Messages.COUPON_CLAIMED})


class ClaimByPromoCodeView(BaseApiView):
    """凭专属推广码领取优惠券（不同推广码指向同一张基础券）。"""

    @extend_schema(request=None, responses={200: OpenApiResponse(description='coupon claimed')})
    def post(self, request, code):
        try:
            PromotionService.claim_via_promo_code(request.user, code)
        except ValueError as e:
            error_map = {
                'PROMO_CODE_NOT_FOUND': (Messages.PROMO_CODE_NOT_FOUND, status.HTTP_404_NOT_FOUND),
                'COUPON_UNAVAILABLE': (Messages.COUPON_UNAVAILABLE, status.HTTP_400_BAD_REQUEST),
                'COUPON_LIMIT_REACHED': (Messages.COUPON_LIMIT_REACHED, status.HTTP_400_BAD_REQUEST),
                'COUPON_AUDIENCE_MISMATCH': (
                    Messages.COUPON_AUDIENCE_MISMATCH,
                    status.HTTP_403_FORBIDDEN,
                ),
            }
            if str(e) in error_map:
                msg, code = error_map[str(e)]
                return Response({'detail': msg}, status=code)
            raise
        return Response({'detail': Messages.COUPON_CLAIMED})


class PromoDetailView(PublicApiView):
    """公开：按推广码解析其指向的优惠券详情 + 推广码元信息（分享页用）。"""

    @extend_schema(responses={200: OpenApiResponse(description='promo detail')})
    def get(self, request, code):
        pc = PromoCode.objects.filter(code=code, is_active=True).select_related('coupon').first()
        if not pc:
            return Response(
                {'detail': Messages.PROMO_CODE_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            detail = PromotionService.get_public_detail(pc.coupon.code)
        except ValueError:
            return Response(
                {'detail': Messages.COUPON_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )
        detail['promo_code'] = pc.code
        detail['promo_name'] = pc.name
        detail['promo_note'] = pc.note
        return Response(detail)


class GenerateCouponView(BaseApiView):
    """生成优惠券并返回折扣信息（仅管理员可用）。"""
    permission_classes = [HasPerm('promotion.coupon.write')]

    @extend_schema(
        request=GenerateCouponSerializer,
        responses={201: OpenApiResponse(description='coupon created')},
    )
    @extend_schema(responses={200: OpenApiResponse(description='Create')})
    def post(self, request):
        serializer = GenerateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        coupon = Coupon.objects.create(
            code=data.get('code') or None,
            discount_type=data['discount_type'],
            amount=data['amount'],
            min_amount=data['min_amount'],
            max_discount=data.get('max_discount'),
            total_count=data['total_count'],
            stackable=data.get('stackable', False),
            start_time=data['start_time'],
            end_time=data['end_time'],
            created_by=request.user,
        )
        Cache('promotion').delete('available')
        from apps.goods.services import GoodsQueryService
        GoodsQueryService.invalidate_promo_caches()
        return Response(CouponSerializer(coupon).data, status=status.HTTP_201_CREATED)
