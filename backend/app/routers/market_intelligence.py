"""Router Market Intelligence (16.5.2).

Membuka data Market Intelligence lewat REST: `GET /api/market-intelligence/{ticker}`.
Graceful — kegagalan dibungkus `success=False` (tidak melempar 500).
"""

import logging

from fastapi import APIRouter

from app.market_intelligence import market_intelligence_service
from app.schemas.market_intelligence import (
    MarketIntelligenceData,
    MarketIntelligenceResponse,
)
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["market-intelligence"])


@router.get("/market-intelligence/{ticker}", response_model=MarketIntelligenceResponse)
async def market_intelligence(ticker: str):
    clean = ticker.upper().strip()
    try:
        data = await market_intelligence_service.get_intelligence(clean)
        return MarketIntelligenceResponse(
            success=True, data=MarketIntelligenceData(**data)
        )
    except AppError as e:
        logger.warning("Market intelligence error for %s: %s", clean, e.message)
        return MarketIntelligenceResponse(success=False, error=e.message)
    except Exception as e:
        logger.error("Market intelligence error for %s: %s", clean, e, exc_info=True)
        return MarketIntelligenceResponse(
            success=False, error=f"Gagal mengambil market intelligence: {e}"
        )
