"""Provider data IDX (primary source) — Opsi B: panggil endpoint IDX langsung di Python.

Satu-satunya tempat yang berinteraksi dengan API IDX. Mengembalikan data mentah
seperti provider Yahoo lainnya: dict untuk profile/fundamental, tuple
(DataFrame, is_simulated) untuk harga. Semua kegagalan jaringan di-handle aman
(return dict ber-key `error` atau `(None, False)`), tidak pernah raise ke caller
— konsisten dengan `CompanyProfileProvider`/`FundamentalsProvider`.

Endpoint (ref: NeaByteLab/IDX-API, diverifikasi respons 200):
- Profile detail : /primary/ListedCompany/GetCompanyProfilesDetail?KodeEmiten={code}&language=id-id
- Securities     : /primary/StockData/GetSecuritiesStock?code={code}
- OHLCV harian   : /primary/ListedCompany/GetTradingInfoSS?code={code}&start=0&length={n}
- Stock screener : /support/stock-screener/api/v1/stock-screener/get (semua emiten, di-cache)

IDX butuh header browser; cookie session dari homepage bersifat opsional (endpoint
data tetap 200 tanpa cookie), tapi kita tetap hangatkan session best-effort.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from curl_cffi import requests as curl_requests

from app.providers.scheduler import batch_scheduler
from app.cache.service import cache_service

logger = logging.getLogger(__name__)

_IDX_BASE = "https://www.idx.co.id"
_BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Referer": "https://www.idx.co.id/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

_screener_lock = asyncio.Lock()


class _IdxRateLimited(Exception):
    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after


async def _fetch_json(url: str, timeout: int = 20) -> Any:
    """GET JSON dari IDX dengan exponential backoff + jitter + 429 detection."""
    await batch_scheduler.acquire()

    max_retries = 4
    base_delay = 2.0

    for attempt in range(max_retries + 1):
        try:
            s = curl_requests.Session(impersonate="chrome124")
            def _sync() -> Any:
                resp = s.get(url, headers=_BROWSER_HEADERS, timeout=timeout)
                if resp.status_code == 429:
                    ra = resp.headers.get("Retry-After")
                    raise _IdxRateLimited(float(ra) if ra else None)
                resp.raise_for_status()
                return resp.json()

            return await asyncio.to_thread(_sync)
        except _IdxRateLimited as e:
            if attempt >= max_retries:
                raise
            delay = e.retry_after if e.retry_after else (base_delay * (2 ** attempt))
            jitter = random.uniform(0, delay * 0.25)
            logger.warning("IDX 429 %s (attempt %d/%d) — retry in %.1fs", url, attempt+1, max_retries, delay+jitter)
            await asyncio.sleep(delay + jitter)
        except Exception as e:
            if attempt >= max_retries:
                raise
            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0, delay * 0.25)
            await asyncio.sleep(delay + jitter)


class IdxProvider:
    async def fetch_company_profile(self, symbol: str) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        try:
            detail = await _fetch_json(
                f"{_IDX_BASE}/primary/ListedCompany/GetCompanyProfilesDetail"
                f"?KodeEmiten={clean}&language=id-id"
            )
            profiles = detail.get("Profiles") or []
            if not profiles:
                raise ValueError("Profil kosong")
            p = profiles[0]
            sec = await self._fetch_securities(clean)
            return {
                "name": p.get("NamaEmiten") or f"PT {clean} Tbk",
                "symbol": clean,
                "exchange": "IDX",
                "country": "Indonesia",
                "sector": p.get("Sektor"),
                "industry": p.get("Industri"),
                "website": p.get("Website"),
                "business_summary": p.get("KegiatanUsahaUtama"),
                "listing_date": p.get("TanggalPencatatan"),
                "market_segment": p.get("PapanPencatatan"),
                "employees": None,
                "logo": None,
                "address": p.get("Alamat"),
                "sub_sector": p.get("SubSektor"),
                "phone": p.get("Telepon"),
                "email": p.get("Email"),
                "status": p.get("Status"),
                "market_cap": None,
                "shares_outstanding": sec.get("shares") if sec else None,
                "source": "idx",
            }
        except Exception as e:
            logger.warning("%s | idx fetch_company_profile error: %s", clean, e)
            return {"name": f"PT {clean} Tbk", "symbol": clean, "exchange": "IDX", "error": str(e)}

    async def fetch_fundamentals(self, symbol: str) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        return {"error": "Screener IDX tidak difetch otomatis", "source": "idx", "fetched_at": None}

    async def fetch_company_announcements(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Pengumuman/berita resmi IDX (primary source News Engine, raw only).

        Endpoint: GetProfileAnnouncement. Struktur respons (diverifikasi live):
        `Replies[].{pengumuman:{JudulPengumuman,TglPengumuman,PerihalPengumuman},
        attachments:[{FullSavePath}]}`. URL item = base + FullSavePath (backslash
        → slash). Semua kegagalan aman: return dict ber-key `error`.
        """
        clean = symbol.upper().replace(".JK", "")
        try:
            data = await _fetch_json(
                f"{_IDX_BASE}/primary/ListedCompany/GetProfileAnnouncement"
                f"?KodeEmiten={clean}&indexFrom=0&pageSize={limit}&lang=id&keyword="
            )
            replies = data.get("Replies") or []
            items = []
            for rep in replies:
                p = rep.get("pengumuman") or {}
                atts = rep.get("attachments") or []
                url = ""
                if atts:
                    path = (atts[0].get("FullSavePath") or "").replace("\\", "/")
                    if path:
                        url = f"{_IDX_BASE}{path if path.startswith('/') else '/' + path}"
                headline = (p.get("JudulPengumuman") or "").strip()
                if not headline:
                    continue
                items.append(
                    {
                        "headline": headline,
                        "publisher": "IDX",
                        "published_date": p.get("TglPengumuman") or "",
                        "summary": (p.get("PerihalPengumuman") or "").strip(),
                        "url": url,
                        "related_ticker": clean,
                    }
                )
            return {"items": items, "fetched_at": datetime.now().isoformat()}
        except Exception as e:
            logger.warning("%s | idx fetch_announcements error: %s", clean, e)
            return {"error": f"Gagal mengambil pengumuman IDX: {e}", "fetched_at": None}

    async def fetch_daily_price(
        self, symbol: str, limit: int = 250
    ) -> Tuple[Optional[pd.DataFrame], bool]:
        """OHLCV harian dari IDX (granularitas daily, bukan intraday).

        Mengembalikan (DataFrame, is_simulated). is_simulated=False karena data
        IDX asli. Pada kegagalan: (None, False) agar caller bisa fallback ke
        Yahoo (intraday tetap dari Yahoo via fetch_history).
        """
        clean = symbol.upper().replace(".JK", "")
        try:
            data = await _fetch_json(
                f"{_IDX_BASE}/primary/ListedCompany/GetTradingInfoSS"
                f"?code={clean}&start=0&length={limit}"
            )
            replies = data.get("replies") or []
            if not replies:
                return None, False
            rows = []
            for r in replies:
                try:
                    rows.append(
                        {
                            "Date": pd.to_datetime(r.get("Date")),
                            "Open": float(r.get("OpenPrice") or 0),
                            "High": float(r.get("High") or 0),
                            "Low": float(r.get("Low") or 0),
                            "Close": float(r.get("Close") or 0),
                            "Volume": float(r.get("Volume") or 0),
                        }
                    )
                except (TypeError, ValueError):
                    continue
            if not rows:
                return None, False
            df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
            return df, False
        except Exception as e:
            logger.warning("%s | idx fetch_daily_price error: %s", clean, e)
            return None, False

    # ----- helper intern -----

    async def _fetch_securities(self, clean: str) -> Optional[Dict[str, Any]]:
        try:
            data = await _fetch_json(
                f"{_IDX_BASE}/primary/StockData/GetSecuritiesStock?code={clean}"
            )
            rows = data.get("data") or []
            if not rows:
                return None
            r = rows[0]
            return {"shares": r.get("Shares"), "listing_board": r.get("ListingBoard")}
        except Exception:  # noqa: BLE001
            return None

    async def _get_screener(self) -> Dict[str, Dict[str, Any]]:
        async with _screener_lock:
            cached = await cache_service.get("screener", "all")
            if cached is not None:
                return cached
            data = await _fetch_json(
                f"{_IDX_BASE}/support/stock-screener/api/v1/stock-screener/get"
                f"?Sector=&SubSector="
            )
            out = {r["stockCode"]: r for r in (data.get("results") or []) if r.get("stockCode")}
            await cache_service.set("screener", "all", out)
            return out
