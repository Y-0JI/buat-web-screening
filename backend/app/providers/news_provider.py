"""Agregator berita emiten dari RSS penerbit Indonesia + ekstraksi artikel.

Sumber: feed RSS yang dapat diakses tanpa kunci (CNBC Indonesia, Detik
Finance, Tempo Bisnis, Katadata, Antara Ekonomi). Item difilter bila judul
atau deskripsi memuat kode saham / nama emiten. Ekstraksi teks memakai
`trafilatura` (hanya domain penerbit yang diizinkan -> anti SSRF).
"""

import html
import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15
_NEWS_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"

FEEDS: list[tuple[str, str]] = [
    ("https://www.cnbcindonesia.com/rss", "CNBC Indonesia"),
    ("https://finance.detik.com/rss", "Detik Finance"),
    ("https://rss.tempo.co/bisnis", "Tempo Bisnis"),
    ("https://katadata.co.id/rss", "Katadata"),
    ("https://www.antaranews.com/rss/ekonomi", "Antara Ekonomi"),
]

# Host yang boleh diekstrak artikelnya (SSRF guard).
ALLOWED_HOSTS = {
    "www.cnbcindonesia.com",
    "cnbcindonesia.com",
    "finance.detik.com",
    "www.detik.com",
    "detik.com",
    "rss.tempo.co",
    "bisnis.tempo.co",
    "www.tempo.co",
    "katadata.co.id",
    "www.katadata.co.id",
    "www.antaranews.com",
    "antaranews.com",
}

_FEED_TTL = 300
_ARTICLE_TTL = 3600

_feed_cache: dict = {"ts": 0.0, "items": []}


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _parse_feed(content: bytes, source: str) -> list[dict]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    out = []
    for it in root.findall(".//item"):
        link = (it.findtext("link") or "").strip()
        if not link:
            continue
        out.append({
            "title": (it.findtext("title") or "").strip(),
            "url": link,
            "published": (it.findtext("pubDate") or "").strip() or None,
            "snippet": _strip_html(it.findtext("description") or "")[:300] or None,
            "source": source,
        })
    return out


async def _fetch_feed(client: httpx.AsyncClient, url: str, source: str) -> list[dict]:
    try:
        resp = await client.get(url, headers={"User-Agent": _NEWS_UA})
        resp.raise_for_status()
        return _parse_feed(resp.content, source)
    except Exception as e:  # noqa: BLE001 — satu feed gagal tidak fatal
        logger.warning("Gagal mengambil feed %s: %s", source, e)
        return []


_STOPWORDS = {
    "bank", "saham", "indonesia", "tbk", "persero", "group", "grup", "utama",
    "nasional", "jaya", "makmur", "sejahtera", "nusantara", "media", "digital",
    "holdings", "tuna", "sari", "raya", "guna", "dana", "karya", "mitra",
    "citra", "prima", "baru", "besar", "muda", "setia", "sama",
}


def _name_matchers(name: Optional[str]) -> tuple[str, list[str], list[str]]:
    """Kembalikan (frasa penuh, singkatan, token bermakna) dari nama emiten."""
    if not name:
        return "", [], []
    clean = re.sub(r"\b(tbk\.?|persero|pt)\b", " ", name, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip().lower()
    words = re.findall(r"[a-z]{2,}", clean)
    acronym = "".join(w[0] for w in words)
    acronyms = (
        [acronym]
        if 3 <= len(acronym) <= 4 and acronym not in _STOPWORDS
        else []
    )
    tokens = [w for w in words if len(w) >= 5 and w not in _STOPWORDS]
    return clean, acronyms, tokens


async def fetch_news(
    code: str, name: Optional[str] = None, limit: int = 20
) -> list[dict]:
    """Ambil berita dari semua feed, filter yang benar-benar menyebut emiten."""
    now = time.time()
    if _feed_cache["items"] and now - _feed_cache["ts"] < _FEED_TTL:
        pool = list(_feed_cache["items"])
    else:
        pool = []
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for url, source in FEEDS:
                pool.extend(await _fetch_feed(client, url, source))
        _feed_cache["ts"] = now
        _feed_cache["items"] = pool

    code_l = code.lower()
    full, acronyms, tokens = _name_matchers(name)
    hits = []
    seen_urls = set()
    for it in pool:
        if it["url"] in seen_urls:
            continue
        hay = f"{it['title']} {it['snippet'] or ''}".lower()
        if (
            code_l in hay
            or (full and full in hay)
            or any(a in hay for a in acronyms)
            or (len(tokens) >= 2 and all(t in hay for t in tokens))
        ):
            seen_urls.add(it["url"])
            hits.append(it)
    return hits[: max(1, min(int(limit or 20), 50))]


_article_cache: dict[str, dict] = {}


def article_allowed(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except (TypeError, ValueError):
        return False
    return host in ALLOWED_HOSTS or any(
        host.endswith(f".{h}") for h in ALLOWED_HOSTS
    )


async def fetch_article(url: str) -> Optional[dict]:
    """Ekstrak teks artikel. None bila gagal/paywall/diblokir."""
    if not article_allowed(url):
        return None
    cached = _article_cache.get(url)
    if cached and time.time() - cached["ts"] < _ARTICLE_TTL:
        return cached["data"]

    try:
        from trafilatura import extract, fetch_url
    except ImportError:
        logger.warning("trafilatura belum terpasang")
        return None

    try:
        downloaded = fetch_url(url)
        if not downloaded:
            return None
        text = extract(downloaded, include_comments=False, include_tables=False)
        if not text or len(text.strip()) < 200:
            return None
        data = {"url": url, "text": text.strip()}
        _article_cache[url] = {"ts": time.time(), "data": data}
        return data
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengekstrak artikel %s: %s", url, e)
        return None
