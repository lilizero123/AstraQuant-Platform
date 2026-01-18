"""
简单的数据缓存模块
"""
import threading
import time
from typing import Any, Dict, Optional


class DataCache:
    """线程安全的TTL缓存"""

    def __init__(self, default_ttl: float = 5.0):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Any] = {}
        self._expire: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            if self._expire[key] < time.time():
                self._cache.pop(key, None)
                self._expire.pop(key, None)
                return None
            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        ttl = ttl if ttl is not None else self.default_ttl
        with self._lock:
            self._cache[key] = value
            self._expire[key] = time.time() + ttl

    def invalidate(self, key: str):
        with self._lock:
            self._cache.pop(key, None)
            self._expire.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._expire.clear()


data_cache = DataCache()
