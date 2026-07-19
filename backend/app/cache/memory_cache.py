"""Implementasi CacheBackend berbasis in-memory dengan TTL per-entry.

Aman untuk digunakan dalam event loop asyncio (dilindungi `asyncio.Lock`).
Setiap entry menyimpan waktu kedaluwarsa sendiri sehingga satu backend bisa
menampung banyak kategori dengan TTL berbeda (dipakai oleh `CacheService`).
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
            expiry, value = entry
            if time.time() >= expiry:
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        async with self._lock:
            self._store[key] = (time.time() + ttl, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self, prefix: Optional[str] = None) -> None:
        async with self._lock:
            if prefix is None:
                self._store.clear()
            else:
                for k in [k for k in self._store if k.startswith(prefix)]:
                    self._store.pop(k, None)

    async def invalidate(self) -> None:
        """Alias untuk `clear` sesuai terminologi dokumen (cache invalidation)."""
        await self.clear()
