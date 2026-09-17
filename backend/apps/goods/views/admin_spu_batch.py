"""
Admin SPU 批量操作 — 批量上下架/调价/改库存/改分类/改品牌/批量审核

设计要点：
- 同步执行 + transaction.atomic() 事务包裹（Celery 已下线，不再区分大/小批量）
- 所有操作在事务内完成，保证原子性
"""

from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes
from django.db import transaction

from utils.api_base_view import BaseApiView
from utils.response_codes import Messages
from ..models import SPU, SPUStatus
from apps.rbac.permissions import HasPerm
from apps.rbac.services import has_role, has_perm
from apps.rbac.constants import Role
from ..admin_permissions import can_operate_spu, can_audit_spu

def execute_batch(spus, action, params, user) -> dict:
    """批量执行核心逻辑，被同步和异步调用共用"""
    affected = 0
    errors = []

    if action == 'put_on_sale':
        for spu in spus:
            try:
                # 草稿免审上架仅限组长/超管；组员对草稿必须走 提交→审核 流程
                if spu.status == SPUStatus.DRAFT and not can_audit_spu(user, spu):
                    errors.append(f'SPU#{spu.id}: 草稿需先提交审核，仅组长/超管可免审上架')
                    continue
                spu.put_on_sale()
                affected += 1
            except ValueError as e:
                errors.append(f'SPU#{spu.id}: {e}')

    elif action == 'put_off_sale':
        for spu in spus:
            try:
                spu.put_off_sale()
                affected += 1
            except ValueError as e:
                errors.append(f'SPU#{spu.id}: {e}')

    elif action == 'update_price':
        price_type = params.get('type', 'fixed')
        value = float(params.get('value', 0))
        for spu in spus:
            for sku in spu.skus.all():
                if price_type == 'percent':
                    sku.price = sku.price * (1 + value / 100)
                else:
                    sku.price = max(0, sku.price + value)
                sku.save(update_fields=['price'])
            affected += 1

    elif action == 'update_stock':
        stock_value = int(params.get('value', 0))
        for spu in spus:
            for sku in spu.skus.all():
                sku.stock = max(0, sku.stock + stock_value)
                sku.save(update_fields=['stock'])
            affected += 1

    elif action == 'change_category':
        category_id = params.get('category_id')
        for spu in spus:
            spu.category_id = category_id
            spu.save(update_fields=['category_id'])
            affected += 1

    elif action == 'change_brand':
        brand_id = params.get('brand_id')
        for spu in spus:
            spu.brand_id = brand_id
            spu.save(update_fields=['brand_id'])
            affected += 1

    elif action == 'batch_audit':
        audit_action = params.get('audit_action')
        comment = params.get('comment', '')
        for spu in spus:
            try:
                if audit_action == 'approve':
                    spu.approve(user, comment)
                elif audit_action == 'reject':
                    spu.reject(user, comment)
                affected += 1
            except ValueError as e:
                errors.append(f'SPU#{spu.id}: {e}')

    return {'affected': affected, 'errors': errors}


class SPUAdminBatchView(BaseApiView):
    """批量操作入口"""
    permission_classes = [HasPerm('goods.spu.write')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiResponse(description='Batch operation result')}
    )
    def post(self, request):
        spu_ids = request.data.get('spu_ids', [])
        action = request.data.get('action')
        params = request.data.get('params', {})

        if not spu_ids or not action:
            return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        spus = SPU.objects.filter(id__in=spu_ids, deleted_at__isnull=True).prefetch_related('skus')
        if not spus.exists():
            return Response({'detail': Messages.SPU_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查：非超管只能操作本组 SPU
        if not has_role(request.user, Role.SUPERADMIN.value):
            for spu in spus:
                if not can_operate_spu(request.user, spu):
                    return Response({'detail': Messages.ADMIN_SPU_NOT_IN_GROUP}, status=status.HTTP_403_FORBIDDEN)

        # 参数校验：change_category / change_brand 需要额外参数
        if action == 'change_category' and not params.get('category_id'):
            return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        if action == 'change_brand' and not params.get('brand_id'):
            return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        if action == 'batch_audit':
            if not has_perm(request.user, 'goods.spu.audit'):
                return Response({'detail': Messages.ADMIN_SPU_AUDIT_NOT_ALLOWED}, status=status.HTTP_403_FORBIDDEN)
            if not params.get('audit_action'):
                return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        if action not in ('put_on_sale', 'put_off_sale', 'update_price', 'update_stock', 'change_category', 'change_brand', 'batch_audit'):
            return Response({'detail': Messages.BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # 敏感操作审计：批量操作（改价/改库存/改类目/批量审核/上下架）必须留痕
        from .admin_audit import create_audit_log
        create_audit_log(
            request.user, f'batch_{action}', 'spu_batch', 0,
            changes={'spu_ids': spu_ids, 'params': params},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # 统一同步 + 事务执行（Celery 已下线，不再区分大批量异步/小批量同步）
        with transaction.atomic():
            result = execute_batch(spus, action, params, request.user)

        return Response({
            'affected_count': result['affected'],
            'errors': result['errors'],
            'action': action,
        })