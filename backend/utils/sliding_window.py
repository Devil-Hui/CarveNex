"""滑动窗口限流 — MySQL-only（Django DatabaseCache 计数桶）。

固定窗口计数（近似滑动窗口），2C4G 资源约束下足够。
失败默认放行，避免基础设施故障阻断主路径。
"""

from __future__ import annotations

import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)


class RateLimitBackendUnavailable(RuntimeError):
    """The distributed rate-limit store cannot make a safe decision."""


def check_sliding_window(
    key: str,
    *,
    window_seconds: int = 60,
    max_count: int = 30,
    fail_open: bool = True,
) -> bool:
    """返回 True 表示允许通过，False 表示超限。"""
    now = time.time()
    # DatabaseCache / 通用 cache：固定窗口计数（近似滑动窗口，2C4G 足够）
    try:
        bucket = int(now // window_seconds)
        cache_key = f'{key}:bucket:{bucket}'
        # add 初始化；失败则 incr
        if cache.add(cache_key, 1, timeout=window_seconds + 10):
            return True
        try:
            n = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=window_seconds + 10)
            n = 1
        return int(n) <= max_count
    except Exception as e:
        logger.error('sliding_window cache failed key=%s: %s', key, e)
        if fail_open:
            return True
        raise RateLimitBackendUnavailable('rate limit backend unavailable') from e