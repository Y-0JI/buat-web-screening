"""Market Intelligence layer (16.5).

Melengkapi Data Layer (16.4) dengan informasi pasar (dividend, corporate action,
foreign flow, broker summary, earnings) untuk dipakai Intelligence/Scoring/AI.
"""

from app.market_intelligence.provider import MarketIntelligenceProvider
from app.market_intelligence.repository import MarketIntelligenceRepository
from app.market_intelligence.service import MarketIntelligenceService

market_intelligence_repository = MarketIntelligenceRepository()
market_intelligence_service = MarketIntelligenceService(market_intelligence_repository)

__all__ = [
    "MarketIntelligenceProvider",
    "MarketIntelligenceRepository",
    "MarketIntelligenceService",
    "market_intelligence_repository",
    "market_intelligence_service",
]
