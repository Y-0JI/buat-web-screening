"""Provider Company Profile dari Yahoo Finance.

Mengembalikan dict mentah: {name, sector, market_cap}. Provider tidak melakukan
validasi atau transformasi response — itu tugas Service. Fallback ke nama
default bila yfinance gagal.
"""

import asyncio
import logging

from app.providers.base import _rate_limit, resolve_ticker
from app.utils.errors import NetworkError

logger = logging.getLogger(__name__)


class CompanyProfileProvider:
    async def fetch_profile(self, symbol: str) -> dict:
        clean = symbol.upper().replace(".JK", "")
        ticker_str = resolve_ticker(symbol)

        await _rate_limit()

        try:

            def _sync() -> dict:
                import yfinance as yf

                stock = yf.Ticker(ticker_str)
                info = stock.info or {}
                n = info.get("longName", info.get("shortName", ""))
                name = n or f"PT {clean} Tbk"
                return {
                    "name": name,
                    "sector": info.get("sector"),
                    "market_cap": info.get("marketCap"),
                }

            return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=10)
        except asyncio.TimeoutError as e:
            raise NetworkError(f"Timeout mengambil company profile {clean}") from e
        except Exception as e:
            logger.warning("%s | fetch_profile error: %s", clean, e)
            return {"name": f"PT {clean} Tbk", "sector": None, "market_cap": None}
