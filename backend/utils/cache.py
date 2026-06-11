"""
聚合数据缓存
- SQLite 缓存表（跨 worker 共享）：调度器写入，API worker 读取
- 内存 TTL 缓存：减少高频读取时的数据库查询
"""
import time
import json
from typing import Optional, Any
from datetime import datetime, timedelta


class MemoryCache:
    """简单的内存 TTL 缓存"""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（过期返回 None）"""
        entry = self._store.get(key)
        if entry:
            expires_at, value = entry
            if time.time() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 30):
        """设置缓存值"""
        self._store[key] = (time.time() + ttl, value)

    def clear(self):
        """清空缓存"""
        self._store.clear()


# 全局内存缓存实例
memory_cache = MemoryCache()
