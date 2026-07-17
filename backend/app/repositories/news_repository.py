"""Repository News — satu pintu akses data berita.

Cache per (ticker, limit) dengan TTL 15 menit. Menentukan cache vs provider.
Tidak ada business logic.
"""

from app.cache.memory_cache import MemoryCache
from app.providers import NewsProvider

_NEWS_TTL = 900  # 15 menit


class NewsRepository:
    def __init__(self, provider: NewsProvider | None = None, cache: MemoryCache | None = None):
        self._provider = provider or NewsProvider()
        self._cache = cache or MemoryCache(default_ttl=_NEWS_TTL)

    async def get_news(self, symbol: str, limit: int = 10) -> dict:
        key = f"{symbol.upper().replace('.JK', '')}:{limit}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        data = await self._provider.fetch_news(symbol, limit=limit)
        if not data.get("error"):
            await self._cache.set(key, data)
        return data
