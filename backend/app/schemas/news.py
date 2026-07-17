"""Skema response spesifik untuk modul News (dipakai Service & Router)."""

from typing import Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    title: str
    publisher: str = ""
    link: str = ""
    published: str = ""
    summary: str = ""


class NewsListData(BaseModel):
    ticker: str
    items: list[NewsItem] = []
    fetched_at: Optional[str] = None
