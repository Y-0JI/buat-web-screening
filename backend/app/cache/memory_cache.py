"""Implementasi CacheBackend berbasis in-memory dengan TTL.

Aman untuk digunakan dalam event loop asyncio (dilindungi `asyncio.Lock`).
Detail strategi cache (persistence, invalidation otomatis per kategori)
dikerjakan lebih lanjut di fase 16.4.5.
"""

import asyncio
import time
from typing import Any, Optional

from app.cache import CacheBackend


class MemoryCache(CacheBackend):
    def __init__(self, default_ttl: int = 3600) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.time() - ts >= self._default_ttl:
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        async with self._lock:
            self._store[key] = (time.time(), value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def invalidate(self) -> None:
        """Alias untuk `clear` sesuai terminologi dokumen (cache invalidation)."""
        await self.clear()
