"""CacheService — pintu tunggal Smart Cache (16.4.5).

Seluruh repository, provider, dan scheduler mengakses cache LEWAT service ini,
bukan menyimpan dict/TTL sendiri. Ini memastikan:
- logika cache tidak tersebar di provider,
- seluruh konsumen memakai mekanisme yang sama,
- TTL konsisten per kategori (dari `cache.ttl`),
- invalidasi/refresh terpusat (per kategori atau global).

Key disimpan dengan namespace `"{category}:{key}"` pada satu backend sehingga
`clear(category)` cukup menghapus berdasarkan prefix.
"""

from typing import Any, Optional

from app.cache import CacheBackend
from app.cache.memory_cache import MemoryCache
from app.cache.ttl import TTL_BY_CATEGORY


class CacheService:
    def __init__(self, backend: Optional[CacheBackend] = None) -> None:
        self._backend = backend or MemoryCache()

    @staticmethod
    def _make_key(category: str, key: str) -> str:
        return f"{category}:{key}"

    async def get(self, category: str, key: str) -> Optional[Any]:
        return await self._backend.get(self._make_key(category, key))

    async def set(
        self, category: str, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        ttl = ttl if ttl is not None else TTL_BY_CATEGORY.get(category)
        await self._backend.set(self._make_key(category, key), value, ttl)

    async def delete(self, category: str, key: str) -> None:
        await self._backend.delete(self._make_key(category, key))

    async def clear(self, category: Optional[str] = None) -> None:
        """Invalidasi cache. `category` None → semua; selain itu satu kategori."""
        if category is None:
            await self._backend.clear()
        else:
            await self._backend.clear(prefix=f"{category}:")


cache_service = CacheService()
