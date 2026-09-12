"""
Admin SPU 视图 — SPU CRUD + 审核 + 上下架 + 复制 + 定时上下架
"""

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import datetime
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes
from logging import getLogger

from utils.api_base_view import BaseApiView
from utils.response_codes import Messages
from utils.api_base_pagination import safe_int
from ..models import SPU, SPUStatus, Brand, Category, SKU
from apps.rbac.permissions import HasPerm, IsSuperAdmin
from apps.rbac.services import has_role
from apps.rbac.constants import Role
from ..admin_permissions import can_audit_spu, can_operate_spu, get_group_managed_category_ids
from ..services import SPUStatusCache, GoodsCacheService
from ..serializers import (
    SPUCreateRequestSerializer, SPUUpdateRequestSerializer, SPUAdminDetailSerializer,
)
from .admin_audit import create_audit_log, create_operation_log
from .admin_sku import SKUAdminBatchCreateView

_logger = getLogger('biz')


class SPUAdminListView(BaseApiView):
    """管理端 SPU 分页列表（含状态筛选、分类筛选、品牌筛选、关键词搜索）"""
    permission_classes = [HasPerm('goods.spu.read')]

    @extend_schema(responses={200: OpenApiResponse(description='List or retrieve')})
    def get(self, request):
        queryset = SPU.objects.filter(deleted_at__isnull=True).select_related('brand', 'category__parent__parent', 'submitted_by', 'reviewed_by')

        # 非超管用户只能看到自己组的 SPU
        if not has_role(request.user, Role.SUPERADMIN.value):
            managed_category_ids = get_group_managed_category_ids(request.user)
            if managed_category_ids:
                queryset = queryset.filter(category_id__in=managed_category_ids)
            else:
                # 用户不在任何组，返回空列表
                return Response({
                    'total': 0,
                    'page': 1,
                    'page_size': safe_int(request.query_params.get('page_size'), getattr(settings, 'SPU_ADMIN_DEFAULT_PAGE_SIZE', 20)),
                    'items': [],
                })

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        category_id = request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        brand_id = request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        q = request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(skus__sku_code__icontains=q) |
                Q(skus__barcode__icontains=q)
            ).distinct()

        page = safe_int(request.query_params.get('page'), 1)
        page_size = safe_int(request.query_params.get('page_size'), getattr(settings, 'SPU_ADMIN_DEFAULT_PAGE_SIZE', 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = queryset.count()
        items = []
        spu_ids = []
        # 预取 SKU 数据，避免 N+1 查询
        spu_list = list(queryset.order_by('-id')[start:end])
        spu_ids = [spu.id for spu in spu_list]
        spu_id_to_skus = {}
        if spu_ids:
            skus_qs = SKU.objects.filter(spu_id__in=spu_ids)
            for sku in skus_qs:
                spu_id_to_skus.setdefault(sku.spu_id, []).append(sku)
        for spu in spu_list:
            skus = spu_id_to_skus.get(spu.id, [])
            price_range = None
            if skus:
                prices = [s.price for s in skus]
                price_range = {'min': str(min(prices)), 'max': str(max(prices))}
            items.append({
                'id': spu.id,
                'name': spu.name,
                'brand_id': spu.brand_id,
                'brand_name': spu.brand.name,
                'category_id': spu.category_id,
                'category_path': self._get_category_path(spu.category),
                'main_image': spu.main_image,
                'status': spu.status,
                'status_display': spu.get_status_display(),
                'price_range': price_range,
                'sku_count': len(skus),
                'submitted_by': spu.submitted_by.username if spu.submitted_by else None,
                'submitted_at': spu.submitted_at,
                'reviewed_by': spu.reviewed_by.username if spu.reviewed_by else None,
                'reviewed_at': spu.reviewed_at,
                'created_at': spu.created_at,
                'updated_at': spu.updated_at,
            })

        # 🔥 合并 Redis 状态缓存（确保最新状态覆盖数据库读取）
        if spu_ids:
            redis_statuses = SPUStatusCache.get_bulk(spu_ids)
            for item in items:
                if item['id'] in redis_statuses:
                    redis_status = redis_statuses[item['id']]
                    if redis_status != item['status']:
                        item['status'] = redis_status
                        item['status_display'] = dict(SPUStatus.choices).get(redis_status, redis_status)

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        })

    @staticmethod
    def _get_category_path(category):
        parts = []
        current = category
        while current:
            parts.insert(0, current.name)
            current = current.parent
        return ' / '.join(parts)


class SPUAdminCreateView(BaseApiView):
    """创建 SPU —— 超管创建即直接上架（ON_SALE），前台实时可见。"""
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=SPUCreateRequestSerializer,
        responses={201: OpenApiResponse(description='SPU created')}
    )
    def post(self, request):
        name = request.data.get('name', '').strip()
        brand_id = request.data.get('brand_id')
        category_id = request.data.get('category_id')
        description = request.data.get('description', '')
        name_en = request.data.get('name_en', '')
        description_en = request.data.get('description_en', '')
        name_ar = request.data.get('name_ar', '')
        description_ar = request.data.get('description_ar', '')
        main_image = request.data.get('main_image', '')
        meta_title = request.data.get('meta_title', '')
        meta_description = request.data.get('meta_description', '')
        product_type = request.data.get('product_type', '')
        tags = request.data.get('tags', [])
        requires_shipping = request.data.get('requires_shipping', True)
        taxable = request.data.get('taxable', True)
        product_kind = request.data.get('product_kind', 'physical')

        # Handle specs: JSON string (from FormData) or list (from JSON body)
        specs_raw = request.data.get('specs', [])
        if isinstance(specs_raw, str):
            import json
            try:
                specs_raw = json.loads(specs_raw)
            except json.JSONDecodeError:
                specs_raw = []

        if not name:
            return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        if not brand_id or not category_id:
            return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        try:
            brand = Brand.objects.get(id=brand_id, is_active=True)
        except Brand.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        try:
            category = Category.objects.get(id=category_id, is_active=True)
        except Category.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        # 组隔离：非超管只能在本组管理的类目下创建（与编辑/审核/上架一致）。
        # 此前缺此校验 → 组员/组长可跨组创建商品，后续管理却 403（能建不能管的孤儿商品）。
        if not has_role(request.user, Role.SUPERADMIN.value):
            managed_ids = get_group_managed_category_ids(request.user)
            if category_id not in managed_ids:
                return Response({'detail': Messages.ADMIN_SPU_NOT_IN_GROUP},
                                status=status.HTTP_403_FORBIDDEN)

        # 需求调整：超管创建商品即直接上架（ON_SALE），前台实时可见，无需审核流程。
        initial_status = (
            SPUStatus.ON_SALE
            if has_role(request.user, Role.SUPERADMIN.value)
            else SPUStatus.DRAFT
        )
        spu = SPU.objects.create(
            name=name, brand=brand, category=category,
            description=description, name_en=name_en, description_en=description_en,
            name_ar=name_ar, description_ar=description_ar,
            main_image=main_image,
            meta_title=meta_title, meta_description=meta_description,
            product_type=product_type, tags=tags,
            requires_shipping=requires_shipping, taxable=taxable,
            product_kind=product_kind,
            status=initial_status,
            specs=specs_raw,
        )

        # 布隆过滤器：添加新 SPU ID
        GoodsCacheService.add_spu_to_bloom(spu.id)
        # 预热 SPU 商品类型缓存
        GoodsCacheService.warm_spu_kind(spu.id)

        # 创建时若前端显式传入 skus（含 sku_code/价格/库存等），或未提供规格级默认价
        # （SPU 表单流程：前端随后单独调用 /sku/batch 用明细 SKU 创建，请求不带顶层 price/stock），
        # 则这里不再自动生成，否则同一批规格组合会被创建两次（重复 SKU）。
        explicit_skus = request.data.get('skus')
        has_default_price = request.data.get('price') not in (None, '')
        sku_created = 0
        if not explicit_skus and specs_raw and has_default_price:
            try:
                combinations = SKUAdminBatchCreateView._generate_combinations(specs_raw)
                for spec in combinations:
                    SKU.objects.create(
                        spu=spu,
                        spec_values=spec,
                        price=request.data.get('price', 0),
                        discount_price=request.data.get('discount_price'),
                        stock=request.data.get('stock', 0),
                    )
                    sku_created += 1
            except Exception as e:
                _logger.warning('Auto SKU generation failed for spu_id=%s: %s', spu.id, str(e))

        create_audit_log(request.user, 'create', 'spu', spu.id,
                         changes={'name': name, 'brand_id': brand_id, 'category_id': category_id},
                         ip_address=request.META.get('REMOTE_ADDR'))
        create_operation_log(spu, request.user, 'create')

        return Response({
            'id': spu.id,
            'name': spu.name,
            'status': spu.status,
            'sku_count': sku_created,
            'created_at': spu.created_at,
        }, status=status.HTTP_201_CREATED)


class SPUAdminUpdateView(BaseApiView):
    """更新 SPU 基本信息"""
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=SPUUpdateRequestSerializer,
        responses={200: OpenApiResponse(description='SPU updated')}
    )
    def put(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, spu):
            return Response({'detail': Messages.ADMIN_SPU_NOT_IN_GROUP}, status=status.HTTP_403_FORBIDDEN)

        for field in ['name', 'description', 'name_en', 'description_en', 'name_ar', 'description_ar', 'main_image', 'specs', 'meta_title', 'meta_description', 'product_type', 'tags', 'requires_shipping', 'taxable', 'product_kind']:
            if field in request.data:
                setattr(spu, field, request.data[field])
        if 'brand_id' in request.data:
            try:
                spu.brand = Brand.objects.get(id=request.data['brand_id'], is_active=True)
            except Brand.DoesNotExist:
                return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        if 'category_id' in request.data:
            try:
                spu.category = Category.objects.get(id=request.data['category_id'], is_active=True)
            except Category.DoesNotExist:
                return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        spu.save(update_fields=[f for f in request.data if f in ('name', 'description', 'name_en', 'description_en', 'name_ar', 'description_ar', 'main_image', 'specs', 'brand_id', 'category_id', 'meta_title', 'meta_description', 'product_type', 'tags', 'requires_shipping', 'taxable', 'product_kind')])
        create_audit_log(request.user, 'update', 'spu', spu.id,
                         changes={k: str(v) for k, v in request.data.items() if k in ('name', 'description', 'name_en', 'description_en', 'name_ar', 'description_ar', 'main_image', 'brand_id', 'category_id', 'meta_title', 'meta_description', 'product_type', 'tags', 'requires_shipping', 'taxable', 'product_kind')},
                         ip_address=request.META.get('REMOTE_ADDR'))
        create_operation_log(spu, request.user, 'update', field_name=', '.join(k for k in request.data if k in ('name', 'description', 'name_en', 'description_en', 'name_ar', 'description_ar', 'main_image', 'specs', 'brand_id', 'category_id', 'meta_title', 'meta_description', 'product_type', 'tags', 'requires_shipping', 'taxable', 'product_kind')))
        # 失效 SPU 商品类型缓存 + SPU 详情缓存
        GoodsCacheService.invalidate_spu_kind(spu_id)
        GoodsCacheService.invalidate_spu(spu_id)
        return Response({'id': spu.id, 'name': spu.name, 'status': spu.status})


class SPUAdminDeleteView(BaseApiView):
    """软删除 SPU（统一规则：上架中 on_sale 禁止直接删除，必须先下架）"""
    permission_classes = [IsSuperAdmin]

    @extend_schema(responses={200: OpenApiResponse(description='Delete')})
    def delete(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        # 统一删除规则：任何在售商品必须先下架才能删除，避免前台在售状态被静默软删
        if spu.status == SPUStatus.ON_SALE:
            return Response(
                {'detail': '商品正在上架中，请先下架（或挂起）后再删除。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        spu.soft_delete(request.user)
        create_audit_log(request.user, 'delete', 'spu', spu_id,
                         changes={'name': spu.name},
                         ip_address=request.META.get('REMOTE_ADDR'))
        create_operation_log(spu, request.user, 'delete')
        return Response({'message': Messages.SUCCESS})


class SPUAdminDetailView(BaseApiView):
    """管理端 SPU 详情（含审批信息、完整 SKU）。无权限者看不到：非超管校验类目归属，跨组返回 404（与列表不可见一致，避免泄露存在性）。"""
    permission_classes = [HasPerm('goods.spu.read')]

    @extend_schema(responses={200: SPUAdminDetailSerializer})
    def get(self, request, spu_id):
        try:
            spu = SPU.objects.prefetch_related(
                'skus', 'tag_relations__tag', 'media'
            ).select_related('brand', 'category__parent__parent').get(
                id=spu_id, deleted_at__isnull=True
            )
        except SPU.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        if not has_role(request.user, Role.SUPERADMIN.value):
            managed_ids = get_group_managed_category_ids(request.user)
            if spu.category_id not in managed_ids:
                return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        skus = []
        for sku in spu.skus.all():
            skus.append({
                'id': sku.id,
                'spec_values': sku.spec_values,
                'price': str(sku.price),
                'discount_price': str(sku.discount_price) if sku.discount_price is not None else None,
                'stock': sku.stock,
                'image_url': sku.image_url,
                'shelf_status': sku.shelf_status,
                'alert_threshold': sku.alert_threshold,
                'sku_code': sku.sku_code,
                'barcode': sku.barcode,
                'weight': str(sku.weight),
                'track_inventory': sku.track_inventory,
            })

        tags = []
        for tr in spu.tag_relations.select_related('tag').all():
            tags.append({
                'id': tr.tag.id,
                'name': tr.tag.name,
                'color': tr.tag.color,
                'is_active': tr.tag.is_active,
            })

        # 关联媒体列表（≤6 条，直接返回，不分页），含 alt_text
        media = []
        for m in spu.media.order_by('sort_order', 'id'):
            item = {
                'id': m.id,
                'media_type': m.media_type,
                'sort_order': m.sort_order,
                'status': m.status,
                'alt_text': m.alt_text,
                'file_size': m.file_size,
                'created_at': m.created_at.isoformat() if m.created_at else None,
            }
            if m.media_type == 'image':
                item.update({
                    'thumb_url': m.thumb_url,
                    'list_url': m.list_url,
                    'large_url': m.large_url,
                    'original_url': m.original_url,
                })
            else:
                item.update({
                    'video_url': m.video_url,
                    'video_thumb_url': m.video_thumb_url,
                    'video_list_url': m.video_list_url,
                    'video_large_url': m.video_large_url,
                })
            media.append(item)

        return Response({
            'id': spu.id,
            'name': spu.name,
            'brand_id': spu.brand_id,
            'brand_name': spu.brand.name,
            'category_id': spu.category_id,
            'category_path': SPUAdminListView._get_category_path(spu.category),
            'description': spu.description,
            'name_en': spu.name_en,
            'description_en': spu.description_en,
            'name_ar': spu.name_ar,
            'description_ar': spu.description_ar,
            'main_image': spu.main_image,
            'specs': spu.specs,
            'status': spu.status,
            'status_display': spu.get_status_display(),
            'submitted_by': spu.submitted_by.username if spu.submitted_by else None,
            'submitted_at': spu.submitted_at,
            'reviewed_by': spu.reviewed_by.username if spu.reviewed_by else None,
            'reviewed_at': spu.reviewed_at,
            'review_comment': spu.review_comment,
            'scheduled_publish_at': spu.scheduled_publish_at,
            'scheduled_unpublish_at': spu.scheduled_unpublish_at,
            'skus': skus,
            'tags': tags,
            'media': media,
            'product_kind': spu.product_kind,
            'created_at': spu.created_at,
            'updated_at': spu.updated_at,
        })


class SPUAdminShelfView(BaseApiView):
    """上下架 / 挂起 / 恢复"""
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiResponse(description='SPU shelf status updated')}
    )
    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        if not can_operate_spu(request.user, spu):
            return Response({'detail': Messages.ADMIN_SPU_NOT_IN_GROUP}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        try:
            if action == 'put_on_sale':
                # 草稿免审上架仅限组长/超管（与审核权对齐）；组员必须走 提交→审核 流程
                if spu.status == SPUStatus.DRAFT and not can_audit_spu(request.user, spu):
                    return Response({'detail': Messages.ADMIN_SPU_AUDIT_NOT_ALLOWED},
                                    status=status.HTTP_403_FORBIDDEN)
                spu.put_on_sale()
            elif action == 'put_off_sale':
                spu.put_off_sale()
            elif action == 'suspend':
                spu.suspend()
            elif action == 'resume':
                spu.resume()
            else:
                return Response({'detail': Messages.ADMIN_INVALID_ACTION}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            _logger.warning(
                'SPU shelf action fail: user_id=%s spu_id=%s action=%s error=%s',
                request.user.id, spu_id, action, str(e)
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        GoodsCacheService.invalidate_spu(spu_id)
        GoodsCacheService.invalidate_spu_list()
        create_audit_log(request.user, 'shelf_' + action, 'spu', spu_id,
                         ip_address=request.META.get('REMOTE_ADDR'))
        create_operation_log(spu, request.user, 'shelf', field_name=action, new_value=spu.status)
        _logger.info(
            'SPU shelf action success: user_id=%s spu_id=%s action=%s new_status=%s',
            request.user.id, spu_id, action, spu.status
        )
        return Response({'message': Messages.SUCCESS, 'status': spu.status})


class SPUAdminScheduleView(BaseApiView):
    """设置定时上下架时间"""
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiResponse(description='Schedule set')}
    )
    def post(self, request, spu_id):
        try:
            spu = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        if not can_operate_spu(request.user, spu):
            return Response({'detail': Messages.ADMIN_SPU_NOT_IN_GROUP}, status=status.HTTP_403_FORBIDDEN)

        publish_at = request.data.get('publish_at')
        unpublish_at = request.data.get('unpublish_at')

        if publish_at:
            spu.schedule_publish(timezone.datetime.fromisoformat(publish_at.replace('Z', '+00:00')))
        if unpublish_at:
            spu.schedule_unpublish(timezone.datetime.fromisoformat(unpublish_at.replace('Z', '+00:00')))

        create_audit_log(request.user, 'schedule', 'spu', spu_id,
                         changes={'publish_at': publish_at, 'unpublish_at': unpublish_at},
                         ip_address=request.META.get('REMOTE_ADDR'))
        return Response({'message': Messages.ADMIN_SCHEDULED_PUBLISH_SET})


class SPUAdminDuplicateView(BaseApiView):
    """复制商品"""
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=None,
        responses={201: OpenApiResponse(description='SPU duplicated')}
    )
    def post(self, request, spu_id):
        try:
            original = SPU.objects.get(id=spu_id, deleted_at__isnull=True)
        except SPU.DoesNotExist:
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        if not can_operate_spu(request.user, original):
            return Response({'detail': Messages.ADMIN_SPU_NOT_IN_GROUP}, status=status.HTTP_403_FORBIDDEN)

        # 需求调整：超管复制商品直接上架（ON_SALE），前台实时可见。
        initial_status = (
            SPUStatus.ON_SALE
            if has_role(request.user, Role.SUPERADMIN.value)
            else SPUStatus.DRAFT
        )
        new_spu = SPU.objects.create(
            name=f'{original.name} (Copy)',
            brand=original.brand,
            category=original.category,
            description=original.description,
            main_image=original.main_image,
            status=initial_status,
        )
        create_audit_log(request.user, 'duplicate', 'spu', new_spu.id,
                         changes={'source_spu_id': spu_id, 'name': new_spu.name},
                         ip_address=request.META.get('REMOTE_ADDR'))
        create_operation_log(new_spu, request.user, 'duplicate', old_value=str(spu_id))
        return Response({
            'id': new_spu.id,
            'name': new_spu.name,
            'message': Messages.ADMIN_DUPLICATE_SUCCESS,
        }, status=status.HTTP_201_CREATED)


class SPUTranslateView(BaseApiView):
    """商品内容翻译（调用腾讯云机器翻译）。

    用于商品表单中把名称/描述翻译成目标语言（如阿拉伯语）。
    未配置 TMT 密钥时返回 503，前端可隐藏翻译按钮。
    """
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiResponse(description='Translated text')},
    )
    def post(self, request):
        text = request.data.get('text', '')
        source = request.data.get('source', 'auto')
        target = request.data.get('target', 'ar')
        if not text or not text.strip():
            return Response({'detail': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)

        from ..translation_service import translate_text
        result = translate_text(text, source=source, target=target)
        if result is None:
            return Response(
                {'detail': '翻译服务未配置或调用失败，请检查 TMT_SECRET_ID/TMT_SECRET_KEY'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'translated_text': result})
