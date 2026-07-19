"""Repository Market Intelligence (16.5) — satu pintu akses data + cache.

Menentukan kapan pakai cache vs provider, dan menyaring data market-wide
(corporate action, foreign flow) menjadi per-ticker. Tidak ada business logic
di sini; hanya orkestrasi sumber + cache. Durasi cache mengikuti `cache.ttl`.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.cache.service import cache_service
from app.market_intelligence import models
from app.market_intelligence.provider import MarketIntelligenceProvider

logger = logging.getLogger(__name__)

_LOOKBACK_TRADING_DAYS = 7  # cari tanggal bursa terakhir (skip weekend/libur)


class MarketIntelligenceRepository:
    def __init__(self, provider: Optional[MarketIntelligenceProvider] = None):
        self._provider = provider or MarketIntelligenceProvider()

    # ---------- Dividend (per-ticker) ----------

    async def get_dividend(self, ticker: str) -> Optional[Dict[str, Any]]:
        key = ticker.upper().replace(".JK", "")
        cached = await cache_service.get("dividend", key)
        if cached is not None:
            return cached
        raw = await self._provider.fetch_dividend(key)
        result = None
        if not raw.get("error"):
            result = models.normalize_dividend(raw.get("item"))
        await cache_service.set("dividend", key, result)
        return result

    # ---------- Corporate Action (market-wide → filter per-ticker) ----------

    async def _corp_actions_year(self, year: int) -> Dict[str, Any]:
        cached = await cache_service.get("corp_action", str(year))
        if cached is not None:
            return cached
        raw = await self._provider.fetch_corporate_actions_year(year)
        data = {"splits": [], "rights": []}
        if not raw.get("error"):
            data = {"splits": raw.get("splits") or [], "rights": raw.get("rights") or []}
            await cache_service.set("corp_action", str(year), data)
        return data

    async def get_corporate_actions(self, ticker: str) -> List[Dict[str, Any]]:
        code = ticker.upper().replace(".JK", "")
        this_year = date.today().year
        splits: List[Dict[str, Any]] = []
        rights: List[Dict[str, Any]] = []
        for year in (this_year, this_year - 1):
            data = await self._corp_actions_year(year)
            splits += [
                models.normalize_stock_split(r)
                for r in data["splits"]
                if (r.get("code") or "").upper() == code
            ]
            rights += [
                models.normalize_right_offering(r)
                for r in data["rights"]
                if (r.get("code") or "").upper() == code
            ]
        return models.merge_corporate_actions(splits, rights)

    # ---------- Foreign Flow (per-ticker, dari stock summary terbaru) ----------

    async def _latest_stock_summary(self) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        pointer = await cache_service.get("foreign_flow", "latest_date")
        if pointer is not None:
            cached_map = await cache_service.get("foreign_flow", pointer)
            if cached_map is not None:
                return pointer, cached_map
        for i in range(_LOOKBACK_TRADING_DAYS):
            d = (date.today() - timedelta(days=i)).isoformat()
            summary = await self._provider.fetch_stock_summary(d)
            if summary:
                await cache_service.set("foreign_flow", d, summary)
                await cache_service.set("foreign_flow", "latest_date", d)
                return d, summary
        return None, None

    async def get_foreign_flow(self, ticker: str) -> Optional[Dict[str, Any]]:
        code = ticker.upper().replace(".JK", "")
        d, summary = await self._latest_stock_summary()
        if not summary:
            return None
        return models.normalize_foreign_flow(summary.get(code), d)

    # ---------- Broker Summary (market-wide) ----------

    async def get_broker_summary(self, limit: int = 20) -> List[Dict[str, Any]]:
        pointer = await cache_service.get("broker_summary", "latest_date")
        rows: Optional[List[Dict[str, Any]]] = None
        if pointer is not None:
            rows = await cache_service.get("broker_summary", pointer)
        if rows is None:
            for i in range(_LOOKBACK_TRADING_DAYS):
                d = (date.today() - timedelta(days=i)).isoformat()
                fetched = await self._provider.fetch_broker_summary(d)
                if fetched:
                    rows = fetched
                    await cache_service.set("broker_summary", d, fetched)
                    await cache_service.set("broker_summary", "latest_date", d)
                    break
        if not rows:
            return []
        brokers = [models.normalize_broker(r) for r in rows]
        brokers.sort(key=lambda b: b.get("value") or 0, reverse=True)
        return brokers[:limit]

    # ---------- Earnings (Yahoo, per-ticker) ----------

    async def get_earnings(self, ticker: str) -> Optional[Dict[str, Any]]:
        key = ticker.upper().replace(".JK", "")
        cached = await cache_service.get("earnings", key)
        if cached is not None:
            return cached
        raw = await self._provider.fetch_earnings(key)
        result = None
        if not raw.get("error"):
            result = models.normalize_earnings(raw.get("calendar"))
        await cache_service.set("earnings", key, result)
        return result

    async def clear(self) -> None:
        for cat in ("dividend", "corp_action", "foreign_flow", "broker_summary", "earnings"):
            await cache_service.clear(cat)
