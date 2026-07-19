"""Provider Market Intelligence (16.5) — satu-satunya tempat fetch data mentah.

Primary: IDX (dividend via profile detail, corporate action via DigitalStatistic,
foreign flow via stock summary, broker summary). Sekunder: Yahoo Finance (earnings).

Mengikuti pola `IdxProvider`: reuse helper jaringan `_fetch_json` /
`_ensure_session_warm` sehingga rate-limit, retry, dan session hangat konsisten
dengan Data Layer (16.4). Semua kegagalan aman — return dict ber-key `error`,
list kosong, atau None; tidak pernah raise ke caller.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.providers.idx_provider import (
    _IDX_BASE,
    _ensure_session_warm,
    _fetch_json,
)

logger = logging.getLogger(__name__)

_DIGITAL = f"{_IDX_BASE}/primary/DigitalStatistic/GetApiDataPaginated"


class MarketIntelligenceProvider:
    async def fetch_dividend(self, symbol: str) -> Dict[str, Any]:
        """Dividen terbaru per emiten dari GetCompanyProfilesDetail (`Dividen`)."""
        clean = symbol.upper().replace(".JK", "")
        try:
            await _ensure_session_warm()
            data = await _fetch_json(
                f"{_IDX_BASE}/primary/ListedCompany/GetCompanyProfilesDetail"
                f"?KodeEmiten={clean}&language=id-id"
            )
            div = data.get("Dividen") or []
            return {"item": div[0] if div else None}
        except Exception as e:  # noqa: BLE001
            logger.warning("%s | MI fetch_dividend error: %s", clean, e)
            return {"error": f"Gagal mengambil dividen IDX: {e}"}

    async def _fetch_year_list(self, url_name: str, year: int) -> List[Dict[str, Any]]:
        """Ambil satu tahun penuh (periodType=yearly, periodMonth=0) — 1 request."""
        data = await _fetch_json(
            f"{_DIGITAL}?urlName={url_name}&periodYear={year}&periodMonth=0"
            f"&periodType=yearly&isPrint=False&cumulative=false"
            f"&pageSize=1000&pageNumber=1"
        )
        return data.get("data") or []

    async def fetch_corporate_actions_year(self, year: int) -> Dict[str, Any]:
        """Split + right offering market-wide untuk satu tahun (2 request)."""
        try:
            await _ensure_session_warm()
            splits = await self._fetch_year_list("LINK_STOCK_SPLIT", year)
            rights = await self._fetch_year_list("LINK_RIGHT_OFFERING", year)
            return {"splits": splits, "rights": rights}
        except Exception as e:  # noqa: BLE001
            logger.warning("MI fetch_corporate_actions %s error: %s", year, e)
            return {"error": f"Gagal mengambil corporate action IDX: {e}"}

    async def fetch_stock_summary(self, date_str: str) -> Optional[Dict[str, Any]]:
        """GetStockSummary satu tanggal → map {StockCode: row}. None bila kosong."""
        try:
            await _ensure_session_warm()
            data = await _fetch_json(
                f"{_IDX_BASE}/primary/TradingSummary/GetStockSummary?date={date_str}"
            )
            rows = data.get("data") or []
            if not rows:
                return None
            return {r["StockCode"]: r for r in rows if r.get("StockCode")}
        except Exception as e:  # noqa: BLE001
            logger.warning("MI fetch_stock_summary %s error: %s", date_str, e)
            return None

    async def fetch_broker_summary(
        self, date_str: str, limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """GetBrokerSummary satu tanggal (market-wide). None bila kosong."""
        try:
            await _ensure_session_warm()
            data = await _fetch_json(
                f"{_IDX_BASE}/primary/TradingSummary/GetBrokerSummary"
                f"?length={limit}&start=0&date={date_str}"
            )
            rows = data.get("data") or []
            return rows or None
        except Exception as e:  # noqa: BLE001
            logger.warning("MI fetch_broker_summary %s error: %s", date_str, e)
            return None

    async def fetch_earnings(self, symbol: str) -> Dict[str, Any]:
        """Earnings/calendar dari Yahoo (sumber sekunder, best-effort)."""
        ticker = symbol.upper()
        if not ticker.endswith(".JK"):
            ticker += ".JK"

        def _sync() -> Dict[str, Any]:
            import yfinance as yf

            cal = yf.Ticker(ticker).calendar
            return cal if isinstance(cal, dict) else {}

        try:
            cal = await asyncio.to_thread(_sync)
            return {"calendar": cal}
        except Exception as e:  # noqa: BLE001
            logger.warning("%s | MI fetch_earnings error: %s", ticker, e)
            return {"error": f"Gagal mengambil earnings Yahoo: {e}"}
