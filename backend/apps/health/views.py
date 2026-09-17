"""Health check endpoint — MySQL-only (DB + DatabaseCache)."""
import logging

from django.db import connections
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger('biz')


def health_check(request):
    """GET /health/ — 200 if core services reachable, 503 otherwise."""
    statuses = {}

    try:
        connections['default'].cursor().execute('SELECT 1')
        statuses['db'] = 'ok'
    except Exception as e:
        statuses['db'] = f'error: {e}'

    try:
        cache.set('health_check', '1', timeout=10)
        if cache.get('health_check') == '1':
            statuses['cache'] = 'ok'
        else:
            statuses['cache'] = 'error: read failed'
        cache.delete('health_check')
    except Exception as e:
        statuses['cache'] = f'error: {e}'

    # 部署：Celery 已下线，不再探测 worker 存活
    critical_ok = statuses.get('db') == 'ok' and statuses.get('cache') == 'ok'
    return JsonResponse(
        {
            'status': 'healthy' if critical_ok else 'degraded',
            'infra': 'mysql-only',
            'checks': statuses,
        },
        status=200 if critical_ok else 503,
    )
