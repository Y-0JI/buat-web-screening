"""Repository Stock Price — satu pintu akses data harga & verifikasi ticker.

Primary harga: IDX (`IdxProvider.fetch_daily_price`, OHLCV harian). Fallback:
Yahoo Finance (`StockPriceProvider`) bila IDX tidak memberi data. Verifikasi
ticker tetap pakai Yahoo (IDX tidak punya endpoint verify). Cache per kategori.
Tidak ada business logic.
"""

import pandas as pd

from app.cache.service import cache_service
from app.providers import IdxProvider, StockPriceProvider
from app.config import settings

_PRICE_CATEGORY = "price"
_VERIFY_CATEGORY = "verify"

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

    async def get_price(
        self, symbol: str, fast_fail: bool = False
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"price:{symbol.upper().replace('.JK', '')}:{fast_fail}"
        cached = await cache_service.get(_PRICE_CATEGORY, key)
        if cached is not None:
            return cached
        limit = _period_to_limit(settings.yfinance_period)
        df, sim = await self._idx_provider.fetch_daily_price(symbol, limit=limit)
        if df is None:
            df, sim = await self._provider.fetch_price(symbol, fast_fail=fast_fail)
        await cache_service.set(_PRICE_CATEGORY, key, (df, sim))
        return df, sim

    async def get_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"history:{symbol.upper().replace('.JK', '')}:{period}"
        cached = await cache_service.get(_PRICE_CATEGORY, key)
        if cached is not None:
            return cached
        df, sim = await self._idx_provider.fetch_daily_price(
            symbol, limit=_period_to_limit(period)
        )
        if df is None:
            df, sim = await self._provider.get_history(symbol, period=period)
        await cache_service.set(_PRICE_CATEGORY, key, (df, sim))
        return df, sim

    async def verify_ticker(self, candidate: str) -> bool:
        key = candidate.upper().replace(".JK", "")
        cached = await cache_service.get(_VERIFY_CATEGORY, key)
        if cached is not None:
            return cached
        result = await self._provider.verify_ticker(candidate)
        await cache_service.set(_VERIFY_CATEGORY, key, result)
        return result

    async def clear(self) -> None:
        await cache_service.clear(_PRICE_CATEGORY)
        await cache_service.clear(_VERIFY_CATEGORY)
