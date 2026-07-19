"""Service untuk data berita.

Business logic: validasi ticker, ambil dari repository, lalu transformasi ke
domain object `NewsListData`. Router yang membungkus hasil ini ke `APIResponse`.
"""

from app.repositories import news_repository
from app.schemas.news import NewsItem, NewsListData
from app.services.base import validate_ticker
from app.utils.errors import DataNotFoundError


class NewsService:
    def __init__(self, news_repo=news_repository):
        self._news_repo = news_repo

    async def get_news(self, symbol: str, limit: int = 10) -> NewsListData:
        clean = validate_ticker(symbol)
        result = await self._news_repo.get_news(clean, limit=limit)
        if result.get("error"):
            raise DataNotFoundError(result["error"])
        items = [NewsItem(**item) for item in result.get("items", [])]
        return NewsListData(
            ticker=clean,
            items=items,
            fetched_at=result.get("fetched_at"),
        )
