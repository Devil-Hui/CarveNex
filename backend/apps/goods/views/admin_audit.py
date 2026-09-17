"""
综合审计日志视图 — 分页、筛选、搜索。
同时提供 create_audit_log 工具函数供其他 admin 视图调用。
"""
import logging
from ..models import GoodsAuditLog, ProductOperationLog

_logger = logging.getLogger('biz')


# ── 工具函数：供 admin SPU views 自动写审计日志 ──

def create_audit_log(user, action: str, resource_type: str, resource_id: int,
                     changes: dict = None, extra_data: dict = None, ip_address: str = None):
    """创建一条审计日志。失败不抛异常，仅记录 warning。"""
    try:
        GoodsAuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes or {},
            extra_data=extra_data or {},
            ip_address=ip_address,
        )
    except Exception:
        _logger.warning('Failed to create audit log: %s %s#%s by user=%s',
                        action, resource_type, resource_id, getattr(user, 'id', None))


def create_operation_log(spu, user, action: str, field_name: str = '',
                         old_value: str = '', new_value: str = ''):
    """创建一条商品操作日志。失败不抛异常。"""
    try:
        ProductOperationLog.objects.create(
            spu=spu,
            user=user,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        _logger.warning('Failed to create operation log: %s SPU#%s by user=%s',
                        action, getattr(spu, 'id', None), getattr(user, 'id', None))


# 管理端审计日志查看类（AuditLogListView / AuditLogStatsView / SPUAuditLogView /
# OperationLogListView）已按需求下线，仅保留 create_audit_log / create_operation_log
# 供业务视图写入审计记录使用，避免影响 SPU 增删改、批量、导出等既有调用点。
