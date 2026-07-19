"""Skema response spesifik untuk modul News (dipakai Service & Router)."""

from typing import Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    headline: str
    publisher: str = ""
    published_date: str = ""
    summary: str = ""
    url: str = ""
    related_ticker: str = ""
    source: str = ""


class NewsListData(BaseModel):
    ticker: str
    items: list[NewsItem] = []
    fetched_at: Optional[str] = None
