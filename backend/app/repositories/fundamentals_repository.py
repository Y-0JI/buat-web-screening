"""Repository Fundamentals — satu pintu akses data fundamental.

Cache per ticker dengan TTL 1 jam. Menentukan cache vs provider.
Tidak ada business logic.
"""

from app.cache.memory_cache import MemoryCache
from app.providers import FundamentalsProvider

_FUNDAMENTALS_TTL = 3600  # 1 jam


class FundamentalsRepository:
    def __init__(self, provider: FundamentalsProvider | None = None, cache: MemoryCache | None = None):
        self._provider = provider or FundamentalsProvider()
        self._cache = cache or MemoryCache(default_ttl=_FUNDAMENTALS_TTL)

    async def get_fundamentals(self, symbol: str) -> dict:
        key = symbol.upper().replace(".JK", "")
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        data = await self._provider.fetch_fundamentals(symbol)
        if not data.get("error"):
            await self._cache.set(key, data)
        return data
