"""Agregator berita emiten dari RSS penerbit Indonesia + Bing News + ekstraksi artikel.

Sumber daftar:
1. Bing News RSS (per emiten, dipaging): jangkauan sampai ~1 tahun, URL
   penerbit asli diambil dari parameter `url=` pada link.
2. Feed RSS penerbit (CNBC Indonesia, Detik Finance, Tempo Bisnis, Katadata,
   Antara Ekonomi): berita terbaru, langsung terbaca.

Item difilter bila judul/snippet memuat kode saham / nama emiten, dibuang
bila lebih tua dari 365 hari, diurut terbaru dulu. Ekstraksi teks memakai
`trafilatura` dengan guard SSRF (blokir host privat/loopback/link-local).
"""

import email.utils
import html
import asyncio
import ipaddress
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

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

_BING_URL = "https://www.bing.com/news/search"
_BING_MAX_PAGES = 7
_BING_PAGE_SIZE = 15
_MAX_AGE_DAYS = 365

_FEED_TTL = 120
_ARTICLE_TTL = 3600

_feed_cache: dict = {"ts": 0.0, "items": []}
_bing_cache: dict[str, dict] = {}


async def _fetch_publisher_feeds(
    client: httpx.AsyncClient,
) -> list[dict]:
    """Feed penerbit (tidak tergantung emiten) — cache global bersama."""
    now = time.time()
    if _feed_cache["items"] and now - _feed_cache["ts"] < _FEED_TTL:
        return list(_feed_cache["items"])
    pool: list[dict] = []
    for url, source in FEEDS:
        pool.extend(await _fetch_feed(client, url, source))
    _feed_cache["ts"] = now
    _feed_cache["items"] = pool
    return list(pool)


async def _fetch_bing_all(
    client: httpx.AsyncClient, code: str
) -> list[dict]:
    """Bing News per emiten — cache per kode agar tidak tercampur."""
    now = time.time()
    entry = _bing_cache.get(code)
    if entry and now - entry["ts"] < _FEED_TTL:
        return list(entry["items"])
    pages = await asyncio.gather(*[
        _fetch_bing_page(client, code, page * _BING_PAGE_SIZE)
        for page in range(_BING_MAX_PAGES)
    ])
    pool: list[dict] = []
    for rows in pages:
        if rows:
            pool.extend(rows)
        else:
            break
    _bing_cache[code] = {"ts": now, "items": pool}
    return list(pool)


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


def _parse_pubdate(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _bing_real_url(link: str) -> str:
    """Ambil URL penerbit asli dari parameter `url=` link Bing."""
    try:
        qs = parse_qs(urlparse(link).query)
        raw = (qs.get("url") or [""])[0]
        return unquote(raw).strip() or link
    except (TypeError, ValueError):
        return link


def _parse_bing(content: bytes) -> list[dict]:
    """Parse RSS Bing News; source dari elemen `Source`."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    out = []
    ns = {"ns": "https://www.bing.com/news"}
    for it in root.findall(".//item"):
        link = (it.findtext("link") or "").strip()
        if not link:
            continue
        src = it.findtext("ns:Source", namespaces=ns) or it.findtext("source")
        out.append({
            "title": (it.findtext("title") or "").strip(),
            "url": _bing_real_url(link),
            "published": (it.findtext("pubDate") or "").strip() or None,
            "snippet": _strip_html(it.findtext("description") or "")[:300] or None,
            "source": (src or "").strip() or "Bing News",
        })
    return out


async def _fetch_bing_page(
    client: httpx.AsyncClient, query: str, first: int
) -> list[dict]:
    try:
        resp = await client.get(
            _BING_URL,
            params={"q": query, "format": "RSS", "count": "100", "first": str(first)},
            headers={"User-Agent": _NEWS_UA},
        )
        resp.raise_for_status()
        return _parse_bing(resp.content)
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil Bing page %s: %s", first, e)
        return []


async def fetch_news(
    code: str, name: Optional[str] = None, limit: int = 100
) -> list[dict]:
    """Ambil berita dari Bing (dipaging) + feed penerbit, maks 1 tahun.

    Kembalikan pool penuh (terbaru dulu); pemotongan halaman dilakukan
    pemanggil/route agar tombol 'More' bisa memuat batch lama.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        pool = await _fetch_publisher_feeds(client)
        pool.extend(await _fetch_bing_all(client, code))

    cutoff = datetime.now(timezone.utc).timestamp() - _MAX_AGE_DAYS * 86400
    code_l = code.lower()
    full, acronyms, tokens = _name_matchers(name)
    hits = []
    seen_urls = set()
    for it in pool:
        if it["url"] in seen_urls:
            continue
        dt = _parse_pubdate(it.get("published"))
        if dt is not None and dt.timestamp() < cutoff:
            continue
        hay = f"{it['title']} {it['snippet'] or ''}".lower()
        if (
            code_l in hay
            or (full and full in hay)
            or any(a in hay for a in acronyms)
            or (len(tokens) >= 2 and all(t in hay for t in tokens))
        ):
            seen_urls.add(it["url"])
            hits.append((dt.timestamp() if dt else 0.0, it))
    hits.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in hits][: max(1, min(int(limit or 100), 200))]


_article_cache: dict[str, dict] = {}


def _host_is_private(host: str) -> bool:
    host = (host or "").lower().strip().rstrip(".")
    if host in {"localhost"} or host.endswith((".localhost", ".internal", ".local", ".lan")):
        return True
    try:
        return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback or ipaddress.ip_address(host).is_link_local or ipaddress.ip_address(host).is_multicast or ipaddress.ip_address(host).is_reserved
    except ValueError:
        return False


def article_allowed(url: str) -> bool:
    """Tolak URL non-http dan host privat/loopback/link-local (anti SSRF)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        host = (parsed.hostname or "").lower()
    except (TypeError, ValueError):
        return False
    if not host:
        return False
    return not _host_is_private(host)


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
