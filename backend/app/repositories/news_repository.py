"""Repository News — satu pintu akses data berita (raw aggregator 16.4.4).

Agregasi multi-source: IDX (primary, `IdxProvider.fetch_company_announcements`)
+ Yahoo Finance (`NewsProvider`) + Google News RSS (`RssProvider`). Tiap sumber
di-fetch mandiri; satu gagal tidak menggagalkan lainnya. Hasil dinormalisasi ke
field kanonik 16.4.4 (`headline`, `publisher`, `published_date`, `summary`,
`url`, `related_ticker`, `source`), di-dedupe lintas-sumber, dan diurutkan
terbaru dulu. Sentiment/category BUKAN di sini — itu Intelligence Engine (16.8).
"""

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.cache.memory_cache import MemoryCache
from app.providers import IdxProvider, NewsProvider, RssProvider

_NEWS_TTL = 3600  # 1 jam (sesuai arah 16.4.5)


def _normalize_item(raw: dict, source: str, ticker: str) -> dict:
    """Petakan item mentah tiap provider ke bentuk kanonik 16.4.4.

    Menerima key gaya IDX (`headline`/`url`/`published_date`) maupun gaya
    Yahoo/RSS (`title`/`link`/`published`). `related_ticker` SELALU diisi dari
    argumen `ticker` (tidak bergantung provider) & `source` ditandai eksplisit.
    """
    return {
        "headline": (raw.get("headline") or raw.get("title") or "").strip(),
        "publisher": raw.get("publisher") or "",
        "published_date": raw.get("published_date") or raw.get("published") or "",
        "summary": raw.get("summary") or "",
        "url": raw.get("url") or raw.get("link") or "",
        "related_ticker": ticker,
        "source": source,
    }


def _norm_headline(headline: str) -> str:
    """Kunci dedupe headline: lowercase, buang non-alfanumerik & whitespace."""
    return re.sub(r"[^a-z0-9]", "", headline.lower())


def _norm_url(url: str) -> str:
    """Kunci dedupe URL: buang skema & trailing slash, lowercase."""
    u = re.sub(r"^https?://", "", url.strip().lower())
    return u.rstrip("/")


def _dedupe(items: list[dict]) -> list[dict]:
    """Buang duplikat lintas-sumber. Item pertama (prioritas IDX) menang.

    Kuat walau URL tiap sumber beda: cocokkan headline ternormalisasi dulu,
    lalu URL ternormalisasi.
    """
    seen_h: set[str] = set()
    seen_u: set[str] = set()
    out: list[dict] = []
    for it in items:
        hk = _norm_headline(it["headline"])
        uk = _norm_url(it["url"])
        if hk and hk in seen_h:
            continue
        if uk and uk in seen_u:
            continue
        if hk:
            seen_h.add(hk)
        if uk:
            seen_u.add(uk)
        out.append(it)
    return out


def _parse_date(s: str):
    """Parse tanggal ISO (IDX/Yahoo) atau RFC-2822 (RSS) → datetime naive UTC.

    Return None bila tak terbaca (item tsb diletakkan di akhir saat sort).
    """
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            d = parsedate_to_datetime(s)
        except (ValueError, TypeError):
            return None
    if d is not None and d.tzinfo is not None:
        d = d.astimezone(timezone.utc).replace(tzinfo=None)
    return d


def _sort_items(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda x: _parse_date(x["published_date"]) or datetime.min,
        reverse=True,
    )


class NewsRepository:
    def __init__(
        self,
        provider: NewsProvider | None = None,
        idx_provider: IdxProvider | None = None,
        rss_provider: RssProvider | None = None,
        cache: MemoryCache | None = None,
    ):
        self._provider = provider or NewsProvider()
        self._idx_provider = idx_provider or IdxProvider()
        self._rss_provider = rss_provider or RssProvider()
        self._cache = cache or MemoryCache(default_ttl=_NEWS_TTL)

    async def get_news(self, symbol: str, limit: int = 10) -> dict:
        clean = symbol.upper().replace(".JK", "")
        key = f"{clean}:{limit}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        idx = await self._safe(self._idx_provider.fetch_company_announcements(clean, limit))
        yf = await self._safe(self._provider.fetch_news(clean, limit))
        rss = await self._safe(self._rss_provider.fetch_rss(clean, limit))

        collected: list[dict] = []
        for data, source in ((idx, "IDX"), (yf, "Yahoo"), (rss, "Google RSS")):
            if data.get("error"):
                continue
            for raw in data.get("items", []):
                collected.append(_normalize_item(raw, source, clean))

        if not collected:
            # Semua sumber error → sampaikan error. Bila hanya kosong (tanpa
            # error), kembalikan list kosong sebagai sukses.
            errors = [d.get("error") for d in (idx, yf, rss) if d.get("error")]
            if len(errors) == 3:
                return {"error": errors[0], "fetched_at": None}
            return {"items": [], "fetched_at": datetime.now().isoformat()}

        result = {
            "items": _sort_items(_dedupe(collected))[:limit],
            "fetched_at": datetime.now().isoformat(),
        }
        await self._cache.set(key, result)
        return result

    async def _safe(self, coro) -> dict:
        try:
            return await coro
        except Exception as e:  # noqa: BLE001 - satu sumber gagal tidak fatal
            return {"error": str(e)}
