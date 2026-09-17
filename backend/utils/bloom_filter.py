"""布隆过滤器 — 前置拦截不存在的 ID，防止缓存穿透。

在当前 MySQL-only 架构下，本过滤器作为纯计算对象存在，不具备外部位图存储，
因此 `exists()` 恒返回 `fallback`（默认 True），由调用方据此直查数据库，
保证查询结果的正确性。

Usage:
    bf = BloomFilter('spu_ids', capacity=100000, error_rate=0.001)
    bf.exists('spu:123')   # 恒返回 True（走查库兜底）
"""

from __future__ import annotations

from typing import List, Optional


class BloomFilter:
    """布隆过滤器 — 降级实现（无外部位图存储）。

    - `add` / `batch_add` / `clear`：no-op（不写任何外部存储）
    - `exists`：恒返回 `fallback`（默认 True），由调用方兜底直查数据库
    """

    def __init__(
        self,
        name: str,
        capacity: int = 100000,
        error_rate: float = 0.001,
        fallback: bool = True,
    ):
        self.name = name
        self.capacity = capacity
        self.error_rate = error_rate
        self.fallback = fallback

    def add(self, value: str) -> bool:
        """添加元素到布隆过滤器（no-op，直接返回 False）。"""
        return False

    def exists(self, value: str) -> bool:
        """检查元素是否可能存在。

        无外部存储，恒返回 `fallback`（默认 True，走查库兜底）。
        返回 True 表示"需要再查数据库确认"，绝不做误拦截。
        """
        return self.fallback

    def batch_add(self, values: List[str]) -> bool:
        """批量添加（no-op，直接返回 False）。"""
        return False

    def clear(self):
        """清除布隆过滤器（no-op）。"""
        return None

    def __contains__(self, value: str) -> bool:
        """复用 exists 的判定逻辑（恒返回 fallback）。"""
        return self.exists(value)