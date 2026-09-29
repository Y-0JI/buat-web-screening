"""Repository Stock Price — satu pintu akses data harga & verifikasi ticker.

Primary: IDX Edge PRO (`IdxEdgeProvider`, REST API) saat `IDX_EDGE_API_KEY` diisi.
Kill-switch: bila key kosong, kembali memakai IDX scraping + Yahoo Finance.
Tidak ada business logic di sini; hanya orkestrasi sumber + cache.
"""

import logging

import pandas as pd

from app.cache.service import cache_service
from app.config import settings
from app.providers import IdxProvider, StockPriceProvider
from app.providers.idx_edge_provider import IdxEdgeProvider, rows_to_price_df

logger = logging.getLogger(__name__)

_PRICE_CATEGORY = "price"

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
        edge_provider: IdxEdgeProvider | None = None,
    ):
        self._provider = provider or StockPriceProvider()
        self._idx_provider = idx_provider or IdxProvider()
        self._edge = edge_provider or IdxEdgeProvider()

    async def get_price(
        self, symbol: str, fast_fail: bool = False
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"price:{symbol.upper().replace('.JK', '')}:{fast_fail}"
        cached = await cache_service.get(_PRICE_CATEGORY, key)
        if cached is not None:
            return cached
        df, sim = await self._fetch(symbol, _period_to_limit(settings.yfinance_period))
        await cache_service.set(_PRICE_CATEGORY, key, (df, sim))
        return df, sim

    async def get_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"history:{symbol.upper().replace('.JK', '')}:{period}"
        cached = await cache_service.get(_PRICE_CATEGORY, key)
        if cached is not None:
            return cached
        df, sim = await self._fetch(symbol, _period_to_limit(period))
        await cache_service.set(_PRICE_CATEGORY, key, (df, sim))
        return df, sim

    async def _fetch(
        self, symbol: str, limit: int
    ) -> tuple[pd.DataFrame | None, bool]:
        if self._edge.enabled:
            clean = symbol.upper().replace(".JK", "")
            rows = await self._edge.fetch_history(clean, limit=limit)
            return rows_to_price_df(rows), False
        df, sim = await self._idx_provider.fetch_daily_price(symbol, limit=limit)
        if df is None:
            df, sim = await self._provider.fetch_history(
                symbol, period=settings.yfinance_period
            )
        return df, sim

    async def clear(self) -> None:
        await cache_service.clear(_PRICE_CATEGORY)
