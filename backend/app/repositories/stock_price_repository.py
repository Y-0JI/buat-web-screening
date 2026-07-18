"""Repository Stock Price — satu pintu akses data harga & verifikasi ticker.

Primary harga: IDX (`IdxProvider.fetch_daily_price`, OHLCV harian). Fallback:
Yahoo Finance (`StockPriceProvider`) bila IDX tidak memberi data. Verifikasi
ticker tetap pakai Yahoo (IDX tidak punya endpoint verify). Cache per kategori.
Tidak ada business logic.
"""

import pandas as pd

from app.cache.memory_cache import MemoryCache
from app.providers import IdxProvider, StockPriceProvider
from app.config import settings

_PRICE_TTL = 3600  # 1 jam
_HISTORY_TTL = 3600
_VERIFY_TTL = 300  # 5 menit

_PERIOD_LIMITS = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
}


def _period_to_limit(period: str) -> int:
    for key, limit in _PERIOD_LIMITS.items():
        if period.startswith(key):
            return limit
    return 252


class StockPriceRepository:
    def __init__(
        self,
        provider: StockPriceProvider | None = None,
        idx_provider: IdxProvider | None = None,
    ):
        self._provider = provider or StockPriceProvider()
        self._idx_provider = idx_provider or IdxProvider()
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
        limit = _period_to_limit(settings.yfinance_period)
        df, sim = await self._idx_provider.fetch_daily_price(symbol, limit=limit)
        if df is None:
            df, sim = await self._provider.fetch_price(symbol, fast_fail=fast_fail)
        await self._price_cache.set(key, (df, sim))
        return df, sim

    async def get_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"{symbol.upper().replace('.JK', '')}:{period}"
        cached = await self._history_cache.get(key)
        if cached is not None:
            return cached
        df, sim = await self._idx_provider.fetch_daily_price(
            symbol, limit=_period_to_limit(period)
        )
        if df is None:
            df, sim = await self._provider.get_history(symbol, period=period)
        await self._history_cache.set(key, (df, sim))
        return df, sim

    async def verify_ticker(self, candidate: str) -> bool:
        key = candidate.upper().replace(".JK", "")
        cached = await self._verify_cache.get(key)
        if cached is not None:
            return cached
        result = await self._provider.verify_ticker(candidate)
        await self._verify_cache.set(key, result)
        return result
