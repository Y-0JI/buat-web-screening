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
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from curl_cffi import requests as curl_requests

from app.providers.scheduler import request_scheduler

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

_MIN_REQUEST_INTERVAL = 1.0
_RATE_LOCK = asyncio.Lock()
_last_request_time: float = 0.0

# Cache screener (semua emiten) supaya fetch_fundamentals tidak download ulang
# 600KB tiap ticker. ponytail: cache in-memory global, refresh 6 jam.
_SCREENER_TTL = 6 * 3600
_screener_cache: Optional[Dict[str, Dict[str, Any]]] = None
_screener_ts: float = 0.0
_screener_lock = asyncio.Lock()

# Session curl_cffi diinisialisasi malas (pertama kali dipakai).
_session = None
_session_lock = asyncio.Lock()


def _get_session() -> curl_requests.Session:
    global _session
    if _session is None:
        _session = curl_requests.Session(impersonate="chrome124")
    return _session


async def _rate_limit() -> None:
    global _last_request_time
    async with _RATE_LOCK:
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()


async def _fetch_json(url: str, timeout: int = 20) -> Any:
    """GET JSON dari IDX dengan retry exponential backoff (3x). Raise pada
    kegagalan total — pemanggil tiap method sudah menangkapnya jadi fallback."""
    await request_scheduler.acquire()
    await _rate_limit()

    def _sync() -> Any:
        s = _get_session()
        resp = s.get(url, headers=_BROWSER_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    delays = [1, 2, 4]
    last_err: Optional[Exception] = None
    for attempt in range(len(delays) + 1):
        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:  # noqa: BLE001 - semua kegagalan jadi fallback
            last_err = e
            if attempt < len(delays):
                await asyncio.sleep(delays[attempt])
    assert last_err is not None
    raise last_err


async def _ensure_session_warm() -> None:
    """Hangatkan cookie session IDX (best-effort, tidak fatal bila gagal)."""
    def _sync() -> None:
        s = _get_session()
        try:
            s.get(f"{_IDX_BASE}/id", headers=_BROWSER_HEADERS, timeout=15)
            s.get(f"{_IDX_BASE}/primary/home/GetIndexList", headers=_BROWSER_HEADERS, timeout=15)
        except Exception:  # noqa: BLE001
            pass

    async with _session_lock:
        await asyncio.to_thread(_sync)


class IdxProvider:
    async def fetch_company_profile(self, symbol: str) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        try:
            await _ensure_session_warm()
            detail = await _fetch_json(
                f"{_IDX_BASE}/primary/ListedCompany/GetCompanyProfilesDetail"
                f"?KodeEmiten={clean}&language=id-id"
            )
            profiles = detail.get("Profiles") or []
            if not profiles:
                raise ValueError("Profil kosong")
            p = profiles[0]
            try:
                screener = await self._get_screener()
                mcap = (screener.get(clean) or {}).get("marketCapital")
            except Exception:  # noqa: BLE001
                mcap = None
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
                "market_cap": mcap,
                "shares_outstanding": sec.get("shares") if sec else None,
                "source": "idx",
            }
        except Exception as e:
            logger.warning("%s | idx fetch_company_profile error: %s", clean, e)
            return {"name": f"PT {clean} Tbk", "symbol": clean, "exchange": "IDX", "error": str(e)}

    async def fetch_fundamentals(self, symbol: str) -> Dict[str, Any]:
        clean = symbol.upper().replace(".JK", "")
        try:
            await _ensure_session_warm()
            screener = await self._get_screener()
            row = screener.get(clean)
            sec = await self._fetch_securities(clean)
            if row is None:
                return {"error": f"Tidak ada data fundamental IDX untuk {clean}", "source": "idx"}
            return {
                "market_cap": row.get("marketCapital"),
                "revenue": row.get("tRevenue"),
                "net_margin": row.get("npm"),
                "pe": row.get("per"),
                "pbv": row.get("pbv"),
                "roa": row.get("roa"),
                "roe": row.get("roe"),
                "debt_to_equity": row.get("der"),
                "week52_change_pct": row.get("week52PC"),
                "mtd_change_pct": row.get("mtdpc"),
                "ytd_change_pct": row.get("ytdpc"),
                "sector": row.get("sector"),
                "industry": row.get("industry"),
                "shares_outstanding": sec.get("shares") if sec else None,
                "source": "idx",
                "fetched_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning("%s | idx fetch_fundamentals error: %s", clean, e)
            return {"error": f"Gagal mengambil fundamental IDX: {e}", "source": "idx", "fetched_at": None}

    async def fetch_company_announcements(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Pengumuman/berita resmi IDX (primary source News Engine, raw only).

        Endpoint: GetProfileAnnouncement. Struktur respons (diverifikasi live):
        `Replies[].{pengumuman:{JudulPengumuman,TglPengumuman,PerihalPengumuman},
        attachments:[{FullSavePath}]}`. URL item = base + FullSavePath (backslash
        → slash). Semua kegagalan aman: return dict ber-key `error`.
        """
        clean = symbol.upper().replace(".JK", "")
        try:
            await _ensure_session_warm()
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
            await _ensure_session_warm()
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
        global _screener_cache, _screener_ts
        async with _screener_lock:
            if _screener_cache is not None and (time.time() - _screener_ts) < _SCREENER_TTL:
                return _screener_cache
            data = await _fetch_json(
                f"{_IDX_BASE}/support/stock-screener/api/v1/stock-screener/get"
                f"?Sector=&SubSector="
            )
            out = {r["stockCode"]: r for r in (data.get("results") or []) if r.get("stockCode")}
            _screener_cache = out
            _screener_ts = time.time()
            return out
