"""Service Market Intelligence (16.5) — business logic di atas Repository.

Validasi ticker lalu kumpulkan seluruh komponen intelligence secara paralel.
Setiap komponen graceful: kegagalan satu sumber tidak menggagalkan yang lain —
field yang gagal diisi nilai kosong (None / list kosong), aplikasi tetap jalan.

Price Target & Recommendation belum punya sumber reliabel (lihat doc 16.5);
di fase ini sengaja dibiarkan kosong dan empty-safe (diisi di 16.5.3).
"""

import asyncio
import logging
from typing import Any, Dict

from app.market_intelligence import models
from app.market_intelligence.repository import MarketIntelligenceRepository
from app.services.base import validate_ticker

logger = logging.getLogger(__name__)


class MarketIntelligenceService:
    def __init__(self, repo: MarketIntelligenceRepository | None = None):
        self._repo = repo or MarketIntelligenceRepository()

    async def get_intelligence(self, symbol: str) -> Dict[str, Any]:
        ticker = validate_ticker(symbol)
        result = models.empty_intelligence(ticker)

        dividend, corp_actions, foreign_flow, broker, earnings = await asyncio.gather(
            self._repo.get_dividend(ticker),
            self._repo.get_corporate_actions(ticker),
            self._repo.get_foreign_flow(ticker),
            self._repo.get_broker_summary(),
            self._repo.get_earnings(ticker),
            return_exceptions=True,
        )

        result["dividend"] = self._safe(dividend, None, "dividend", ticker)
        result["corporate_actions"] = self._safe(corp_actions, [], "corporate_actions", ticker)
        result["foreign_flow"] = self._safe(foreign_flow, None, "foreign_flow", ticker)
        result["broker_summary"] = self._safe(broker, [], "broker_summary", ticker)
        result["earnings"] = self._safe(earnings, None, "earnings", ticker)
        return result

    @staticmethod
    def _safe(value: Any, default: Any, field: str, ticker: str) -> Any:
        if isinstance(value, Exception):
            logger.warning("%s | MI %s gagal: %s", ticker, field, value)
            return default
        return value if value is not None else default
