from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response

from apps.rbac.permissions import HasPerm
from utils.api_base_pagination import parse_pagination
from utils.api_base_view import BaseApiView, PublicApiView

from .serializers import (
    AdPlatformSerializer,
    CampaignHistorySerializer,
    CampaignSaveItemSerializer,
    HotProductSerializer,
    HotSearchSerializer,
    MetricSnapshotSerializer,
    PlatformMetricSerializer,
    ProductWeeklyItemSerializer,
)
from .services import CampaignConflict, CampaignService, InsightService


# ── 前台展示页（只读，公开）────────────────────────────

class InsightOverviewView(PublicApiView):
    """效果对比：投放前 vs 精准投放后核心指标。"""

    @extend_schema(responses={200: MetricSnapshotSerializer(many=True)})
    def get(self, request):
        data = MetricSnapshotSerializer(InsightService.overview(), many=True).data
        return Response({'metrics': data})


class HotSearchListView(PublicApiView):
    """智能化热搜词榜。"""

    @extend_schema(responses={200: HotSearchSerializer(many=True)})
    def get(self, request):
        data = HotSearchSerializer(InsightService.hot_searches(), many=True).data
        return Response({'results': data})


class HotProductListView(PublicApiView):
    """商品热榜。"""

    @extend_schema(responses={200: HotProductSerializer(many=True)})
    def get(self, request):
        data = HotProductSerializer(InsightService.hot_products(), many=True).data
        return Response({'results': data})


class PlatformMetricsView(PublicApiView):
    """多平台实时指标面板：每个平台的搜索量 / 点击量 / 购买量 / 转化率 + 折线走势。"""

    @extend_schema(responses={200: PlatformMetricSerializer(many=True)})
    def get(self, request):
        data = PlatformMetricSerializer(InsightService.platform_metrics(), many=True).data
        return Response({'results': data})


class ProductWeeklyView(PublicApiView):
    """指定平台下商品的一周指标（周一 ~ 今天），配折线 + 环图数据。"""

    @extend_schema(
        parameters=[OpenApiParameter(name='platform', type=str, required=True)],
        responses={200: OpenApiResponse(description='Product weekly metrics')},
    )
    def get(self, request):
        platform_code = request.query_params.get('platform', '')
        if not platform_code:
            return Response({'detail': 'platform 必填'}, status=status.HTTP_400_BAD_REQUEST)
        platform, day_labels, items = InsightService.product_weekly(platform_code)
        if platform is None:
            return Response({'detail': '平台不存在或未启用'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'platform': platform.code,
            'platform_name': platform.name,
            'days': day_labels,
            'items': ProductWeeklyItemSerializer(items, many=True).data,
        })


# ── 管理端：真实投放操作 ──────────────────────────────

class AdminPlatformListView(BaseApiView):
    """已接入平台列表（表头 Logo 行数据源）。"""

    permission_classes = [HasPerm('ads.campaign.read')]

    @extend_schema(responses={200: AdPlatformSerializer(many=True)})
    def get(self, request):
        data = AdPlatformSerializer(CampaignService.list_platforms(), many=True).data
        return Response({'results': data})


class AdminCampaignMatrixView(BaseApiView):
    """投放矩阵：商品（分页）× 平台 的当前金额 / 上一版金额 / 版本号。"""

    permission_classes = [HasPerm('ads.campaign.read')]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', type=int, required=False, default=1),
            OpenApiParameter(name='per_page', type=int, required=False, default=15),
        ],
        responses={200: OpenApiResponse(description='Campaign matrix')},
    )
    def get(self, request):
        page, per_page = parse_pagination(request)
        rows, total, platforms = CampaignService.build_matrix(page, per_page)
        return Response({
            'count': total,
            'results': rows,
            'platforms': AdPlatformSerializer(platforms, many=True).data,
        })


class AdminCampaignSaveView(BaseApiView):
    """批量保存投放金额并执行投放。版本冲突返回 409 + 冲突明细。"""

    permission_classes = [HasPerm('ads.campaign.write')]

    @extend_schema(request=CampaignSaveItemSerializer(many=True), responses={200: OpenApiResponse(description='Saved')})
    def post(self, request):
        items = request.data.get('items') if isinstance(request.data, dict) else None
        if not items:
            return Response({'detail': 'items 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CampaignSaveItemSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)

        try:
            saved = CampaignService.save_batch(serializer.validated_data, request.user)
        except CampaignConflict as e:
            return Response(
                {'detail': '数据已被他人修改，请刷新后重试', 'conflict_platform': e.platform_code,
                 'current_version': e.current_version},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'saved': [
                {'spu_id': r.spu_id, 'platform_code': r.platform.code, 'version': r.version,
                 'amount': str(r.amount), 'status': r.status}
                for r in saved
            ]
        })


class AdminCampaignHistoryView(BaseApiView):
    """单商品单平台的投放历史（版本链，最新在前）。"""

    permission_classes = [HasPerm('ads.campaign.read')]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='spu_id', type=int, required=True),
            OpenApiParameter(name='platform_code', type=str, required=True),
        ],
        responses={200: CampaignHistorySerializer(many=True)},
    )
    def get(self, request):
        try:
            spu_id = int(request.query_params.get('spu_id', ''))
        except ValueError:
            spu_id = 0
        platform_code = request.query_params.get('platform_code', '')
        if spu_id <= 0 or not platform_code:
            return Response({'detail': 'spu_id 与 platform_code 必填'}, status=status.HTTP_400_BAD_REQUEST)
        data = CampaignHistorySerializer(CampaignService.history(spu_id, platform_code), many=True).data
        return Response({'results': data})
