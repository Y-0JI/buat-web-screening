"""Provider data harga saham dari Yahoo Finance.

Hanya mengambil data mentah (historis & verifikasi ticker). Fallback ke data
simulasi (mock) dipertahankan dari implementasi sebelumnya agar aplikasi tetap
jalan saat Yahoo Finance tidak responsif — flag `is_simulated` selalu dikembalikan
agar caller tahu data bukan live.
"""

import asyncio
import logging

import pandas as pd
from app.config import settings
from app.providers.base import (
    _dedup,
    _flatten_columns,
    _generate_mock_data,
    _rate_limit,
    _run_yf,
    resolve_ticker,
)
from app.utils.errors import RateLimitError

logger = logging.getLogger(__name__)


class StockPriceProvider:
    async def fetch_price(
        self, symbol: str, fast_fail: bool = False
    ) -> tuple[pd.DataFrame | None, bool]:
        ticker_str = resolve_ticker(symbol)

        async def _do() -> tuple[pd.DataFrame | None, bool]:
            await _rate_limit()
            timeouts = [5] if fast_fail else [8, 5, 4]
            yf_result: pd.DataFrame | None = None
            for attempt, to in enumerate(timeouts):
                try:

                    def _sync() -> pd.DataFrame | None:
                        import yfinance as yf

                        df = yf.Ticker(ticker_str).history(period=settings.yfinance_period)
                        if df is not None and not df.empty:
                            return _flatten_columns(df)
                        return None

                    yf_result = await _run_yf(_sync, to)
                    if yf_result is not None:
                        break
                except RateLimitError:
                    if not fast_fail and attempt < len(timeouts) - 1:
                        await asyncio.sleep(10)
                    continue
                except Exception:
                    if not fast_fail and attempt < len(timeouts) - 1:
                        await asyncio.sleep(1)
                    continue
            if yf_result is not None:
                return yf_result, False
            return _generate_mock_data(ticker_str, settings.yfinance_period), True

        return await _dedup(f"price:{ticker_str}:{fast_fail}", _do)

    async def fetch_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        ticker_str = resolve_ticker(symbol)

        async def _do() -> tuple[pd.DataFrame | None, bool]:
            if period == settings.yfinance_period:
                return await self.fetch_price(symbol)
            await _rate_limit()

            def _sync() -> pd.DataFrame | None:
                import yfinance as yf

                df = yf.Ticker(ticker_str).history(period=period)
                if df is not None and not df.empty:
                    return _flatten_columns(df)
                return None

            try:
                df = await _run_yf(_sync, 8)
                if df is not None:
                    return df, False
            except Exception as e:
                logger.warning("%s | fetch_history error: %s", ticker_str, e)
            return _generate_mock_data(ticker_str, period), True

        return await _dedup(f"history:{ticker_str}:{period}", _do)

    async def verify_ticker(self, candidate: str) -> bool:
        """Cek apakah candidate benar-benar ada di Yahoo Finance (bukan mock)."""
        ticker_str = resolve_ticker(candidate)

        async def _do() -> bool:
            await _rate_limit()

            def _sync() -> pd.DataFrame | None:
                import yfinance as yf

                df = yf.Ticker(ticker_str).history(period="5d")
                if df is not None and not df.empty:
                    return _flatten_columns(df)
                return None

            try:
                df = await _run_yf(_sync, 8)
                return df is not None and not df.empty
            except Exception:
                return False

        return await _dedup(f"verify:{ticker_str}", _do)
