import logging
from fastapi import APIRouter
from pydantic import BaseModel
from app.data.fetcher import fetch_news

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock", tags=["stock"])


class NewsItem(BaseModel):
    title: str
    publisher: str = ""
    link: str = ""
    published: str = ""
    summary: str = ""


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
        result = await fetch_news(clean, limit=limit)
        if result.get("error"):
            return StockNewsResponse(
                success=False,
                ticker=clean,
                error=result["error"],
            )
        items = [NewsItem(**item) for item in result.get("items", [])]
        return StockNewsResponse(
            success=True,
            ticker=clean,
            data=items,
            fetched_at=result.get("fetched_at"),
        )
    except Exception as e:
        logger.error("News error for %s: %s", clean, e, exc_info=True)
        return StockNewsResponse(
            success=False,
            ticker=clean,
            error=f"Gagal mengambil berita: {e}",
        )
