"""Provider News dari Google News RSS (secondary source, raw only).

Mengembalikan dict mentah persis seperti `NewsProvider`:
    {"items": [...], "fetched_at": "..."}  bila sukses
    {"error": "...", "fetched_at": null}   bila gagal
Tidak ada tagging sentiment/category — itu di Intelligence Engine (16.8).

Parse pakai `xml.etree` (stdlib), tanpa dependency baru. Hanya ambil
headline, publisher, published, summary, url, related_ticker.
"""

import asyncio
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict

from app.providers.scheduler import request_scheduler

logger = logging.getLogger(__name__)

_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"


class RssProvider:
    async def fetch_rss(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        query = urllib.parse.quote(f"{clean} IDX")
        url = _RSS_TEMPLATE.format(query=query)

        def _sync() -> Dict[str, Any]:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml, */*"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                root = ET.fromstring(data)
                items = []
                for item in root.iter("item"):
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    published = (item.findtext("pubDate") or "").strip()
                    summary = (item.findtext("description") or "").strip()
                    publisher = (item.findtext("source") or "").strip()
                    if title:
                        items.append(
                            {
                                "title": title,
                                "publisher": publisher,
                                "link": link,
                                "published": published,
                                "summary": summary,
                                "related_ticker": clean,
                            }
                        )
                    if len(items) >= limit:
                        break
                return {"items": items, "fetched_at": datetime.now().isoformat()}
            except Exception as e:
                logger.warning("%s | fetch_rss error: %s", clean, e)
                return {"error": "Gagal mengambil RSS berita", "fetched_at": None}

        await request_scheduler.acquire()
        return await asyncio.to_thread(_sync)

