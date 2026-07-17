import logging
from fastapi import APIRouter
from pydantic import BaseModel
from app.schemas.news import NewsItem
from app.services import news_service
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock", tags=["stock"])


class StockNewsResponse(BaseModel):
    success: bool
    ticker: str
    data: list[NewsItem] | None = None
    fetched_at: str | None = None
    error: str | None = None


@router.get("/{ticker}/news", response_model=StockNewsResponse)
async def stock_news(ticker: str, limit: int = 10):
    clean = ticker.upper().strip()
    try:
        result = await news_service.get_news(clean, limit=limit)
        return StockNewsResponse(
            success=True,
            ticker=clean,
            data=result.items,
            fetched_at=result.fetched_at,
        )
    except AppError as e:
        logger.warning("News error for %s: %s", clean, e.message)
        return StockNewsResponse(success=False, ticker=clean, error=e.message)
    except Exception as e:
        logger.error("News error for %s: %s", clean, e, exc_info=True)
        return StockNewsResponse(
            success=False,
            ticker=clean,
            error=f"Gagal mengambil berita: {e}",
        )
