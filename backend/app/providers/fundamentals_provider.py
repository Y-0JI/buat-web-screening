"""Provider Fundamental dari Yahoo Finance.

Mengembalikan dict mentah dengan field market_cap, pe, pb, dividend_yield,
sector, industry, description, dll (daftar kanonik 16.4.3; beta & book_value
sengaja tidak diambil — di-drop dari scope). Provider tidak memetakan ke schema
response — itu tugas Service.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from app.providers.base import _rate_limit, resolve_ticker

logger = logging.getLogger(__name__)


class FundamentalsProvider:
    async def fetch_fundamentals(self, symbol: str) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        await _rate_limit()

        def _sync() -> Dict[str, Any]:
            try:
                import yfinance as yf

                stock = yf.Ticker(resolve_ticker(symbol))
                info = stock.info or {}

                fast = {}
                try:
                    fi = stock.fast_info
                    fast = {
                        "market_cap": getattr(fi, "market_cap", None),
                        "shares_outstanding": getattr(fi, "shares", None),
                        "previous_close": getattr(fi, "previous_close", None),
                        "last_price": getattr(fi, "last_price", None),
                    }
                except Exception:
                    pass

                return {
                    "market_cap": fast.get("market_cap") or info.get("marketCap"),
                    "enterprise_value": info.get("enterpriseValue"),
                    "previous_close": fast.get("previous_close") or info.get("previousClose"),
                    "last_price": fast.get("last_price"),
                    "shares_outstanding": fast.get("shares_outstanding") or info.get("sharesOutstanding"),
                    "pe": info.get("trailingPE") or info.get("forwardPE"),
                    "forward_pe": info.get("forwardPE"),
                    "pb": info.get("priceToBook"),
                    "peg": info.get("pegRatio") or info.get("trailingPegRatio"),
                    "eps": info.get("trailingEps") or info.get("forwardEps"),
                    "roe": info.get("returnOnEquity"),
                    "roa": info.get("returnOnAssets"),
                    "revenue": info.get("totalRevenue"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "net_income": info.get("netIncomeToCommon"),
                    "gross_margin": info.get("grossMargins"),
                    "operating_margin": info.get("operatingMargins"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio": info.get("currentRatio"),
                    "free_cash_flow": info.get("freeCashflow"),
                    "dividend_yield": info.get("dividendYield"),
                    "dividend_payout_ratio": info.get("payoutRatio"),
                    "trailing_annual_dividend_yield": info.get("trailingAnnualDividendYield"),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                    "fifty_day_average": info.get("fiftyDayAverage"),
                    "two_hundred_day_average": info.get("twoHundredDayAverage"),
                    "avg_volume_10d": info.get("averageDailyVolume10Day"),
                    "avg_volume_3m": info.get("averageDailyVolume3Month"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "description": info.get("longBusinessSummary", ""),
                    "website": info.get("website"),
                    "currency": info.get("currency"),
                    "exchange": info.get("exchange"),
                    "fetched_at": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.warning("%s | fetch_fundamentals error: %s", clean, e)
                return {"error": f"Gagal mengambil data fundamental: {e}", "fetched_at": None}

        try:
            return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("%s | fetch_fundamentals timeout", clean)
            return {"error": "Timeout mengambil data fundamental", "fetched_at": None}
        except Exception as e:
            logger.warning("%s | fetch_fundamentals error: %s", clean, e)
            return {"error": f"Gagal mengambil data fundamental: {e}", "fetched_at": None}
