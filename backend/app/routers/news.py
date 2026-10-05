"""Router berita emiten (RSS penerbit) + ekstraksi artikel."""

from typing import Optional

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider
from app.providers import news_provider

router = APIRouter(prefix="/api", tags=["news"])


async def _resolve_name(code: str) -> Optional[str]:
    p = IdxEdgeProvider()
    try:
        for row in await p.search(code):
            if str(row.get("stock_code") or "").upper() == code:
                return row.get("stock_name")
    except Exception:  # noqa: BLE001
        pass
    try:
        data = await p.fetch_market_cap(page=1, per_page=50, codes=[code])
        for row in (data or {}).get("data") or []:
            if str(row.get("code") or "").upper() == code:
                return row.get("name")
    except Exception:  # noqa: BLE001
        pass
    return None


@router.get("/news/{ticker}")
async def news_list(ticker: str, limit: int = 100, page: int = 1, per_page: int = 15):
    code = ticker.upper()
    name = await _resolve_name(code)
    pool = await news_provider.fetch_news(code, name=name, limit=200)
    per_page = max(1, min(int(per_page or 15), 50))
    page = max(1, int(page or 1))
    start = (page - 1) * per_page
    items = pool[start:start + per_page]
    return {
        "success": True,
        "ticker": code,
        "data": items,
        "page": page,
        "per_page": per_page,
        "has_more": start + per_page < len(pool),
        "error": None if items or page > 1 else "Belum ada berita untuk emiten ini di sumber yang dipantau.",
    }


@router.get("/news/article/read")
async def news_article(url: str):
    art = await news_provider.fetch_article(url)
    if not art:
        return {"success": False, "error": "Artikel tidak bisa dibaca penuh.", "data": None}
    return {"success": True, "data": art}
