"""Repository Stock Price — satu pintu akses data harga & verifikasi ticker.

Cache per kategori (price / history / verify) dengan TTL masing-masing.
Menentukan cache vs provider dan menyimpan hasil ke cache. Tidak ada business
logic — cache key dan TTL adalah konfigurasi, bukan logika domain.
"""

import pandas as pd

from app.cache.memory_cache import MemoryCache
from app.providers import StockPriceProvider

_PRICE_TTL = 3600  # 1 jam (mengikuti settings.cache_ttl_seconds)
_HISTORY_TTL = 3600
_VERIFY_TTL = 300  # 5 menit


class StockPriceRepository:
    def __init__(self, provider: StockPriceProvider | None = None):
        self._provider = provider or StockPriceProvider()
        self._price_cache = MemoryCache(default_ttl=_PRICE_TTL)
        self._history_cache = MemoryCache(default_ttl=_HISTORY_TTL)
        self._verify_cache = MemoryCache(default_ttl=_VERIFY_TTL)

    async def get_price(
        self, symbol: str, fast_fail: bool = False
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"{symbol.upper().replace('.JK', '')}:{fast_fail}"
        cached = await self._price_cache.get(key)
        if cached is not None:
            return cached
        data = await self._provider.fetch_price(symbol, fast_fail=fast_fail)
        await self._price_cache.set(key, data)
        return data

    async def get_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"{symbol.upper().replace('.JK', '')}:{period}"
        cached = await self._history_cache.get(key)
        if cached is not None:
            return cached
        data = await self._provider.fetch_history(symbol, period=period)
        await self._history_cache.set(key, data)
        return data

    async def verify_ticker(self, candidate: str) -> bool:
        key = candidate.upper().replace(".JK", "")
        cached = await self._verify_cache.get(key)
        if cached is not None:
            return cached
        result = await self._provider.verify_ticker(candidate)
        await self._verify_cache.set(key, result)
        return result
