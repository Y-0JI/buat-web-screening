"""Provider News dari Yahoo Finance.

Mengembalikan dict mentah:
    {"items": [...], "fetched_at": "..."}  bila sukses
    {"error": "...", "fetched_at": null}   bila gagal
Provider tidak memetakan ke schema response — itu tugas Service.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from app.providers.base import _rate_limit, resolve_ticker

logger = logging.getLogger(__name__)


class NewsProvider:
    async def fetch_news(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        await _rate_limit()

        def _sync() -> Dict[str, Any]:
            try:
                import yfinance as yf

                stock = yf.Ticker(resolve_ticker(symbol))
                raw_news = stock.news
                if not raw_news:
                    return {"items": [], "fetched_at": datetime.now().isoformat()}
                items = []
                for n in raw_news[:limit]:
                    content = n.get("content", {})
                    items.append(
                        {
                            "title": content.get("title", n.get("title", "")),
                            "publisher": content.get("provider", {}).get("displayName", ""),
                            "link": content.get("canonicalUrl", {}).get("url", ""),
                            "published": content.get("pubDate", ""),
                            "summary": content.get("summary", ""),
                        }
                    )
                return {"items": items, "fetched_at": datetime.now().isoformat()}
            except Exception as e:
                logger.warning("%s | fetch_news error: %s", clean, e)
                return {"error": f"Gagal mengambil berita: {e}", "fetched_at": None}

        try:
            return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("%s | fetch_news timeout", clean)
            return {"error": "Timeout mengambil berita", "fetched_at": None}
        except Exception as e:
            logger.warning("%s | fetch_news error: %s", clean, e)
            return {"error": f"Gagal mengambil berita: {e}", "fetched_at": None}
