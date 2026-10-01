"""Provider IDX Edge PRO (stock.arjum.com) — satu-satunya klien REST API-nya.

Mengambil data mentah dari IDX Edge PRO. Tidak ada business logic di sini dan
tidak pernah raise ke caller: setiap kegagalan (timeout, 401, 429, 5xx) ditangani
aman dan mengembalikan None / list kosong, konsisten dengan provider lain.

Auth via header `X-API-Key` (dari settings). Semua request melewati
`request_scheduler` (rate-limit global) dan dihitung terhadap kuota harian
`idx_edge_daily_quota` supaya tidak melebihi batas layanan.
"""

import logging
from datetime import date
from typing import Any, Optional

import httpx

from app.config import settings
from app.providers.scheduler import request_scheduler

logger = logging.getLogger(__name__)

_QUOTA_WARN_RATIO = 0.9

# API IDX Edge PRO menolak limit > 500 (HTTP 422), dan request gagal tetap
# memakan kuota — jadi limit divalidasi (clamp) sebelum dikirim.
_HISTORY_MAX_LIMIT = 500


def history_series(rows: Optional[list[dict]]) -> list[dict]:
    """Normalisasi `rows` /api/history → list OHLCV urut naik & tanggal unik.

    lightweight-charts mewajibkan data urut naik berdasarkan waktu. IDX Edge
    mengembalikan terbaru dulu, jadi di sini di-balik dan duplikat di-dedupe.
    """
    by_date: dict[str, dict] = {}
    for r in rows or []:
        date = r.get("date")
        if not date:
            continue
        try:
            by_date[date] = {
                "date": date,
                "open": float(r.get("open") or 0),
                "high": float(r.get("high") or 0),
                "low": float(r.get("low") or 0),
                "close": float(r.get("close") or 0),
                "volume": float(r.get("volume") or 0),
            }
        except (TypeError, ValueError):
            continue
    return [by_date[d] for d in sorted(by_date)]


def _avg(val: float, vol: float) -> Optional[float]:
    return (val / vol) if vol else None


def broker_summary_payload(data: Optional[dict]) -> Optional[dict]:
    """Normalisasi respons /api/broker-summary → struktur untuk UI kartu."""
    if not data:
        return None
    brokers = []
    buyer_count = seller_count = 0
    net_value = net_volume = total_bval = total_bvol = 0.0
    for b in data.get("brokers") or []:
        bval = float(b.get("bval") or 0)
        bvol = float(b.get("bvol") or 0)
        sval = float(b.get("sval") or 0)
        svol = float(b.get("svol") or 0)
        nval = float(b.get("nval") or 0)
        nvol = float(b.get("nvol") or 0)
        if bval > 0:
            buyer_count += 1
        if sval > 0:
            seller_count += 1
        net_value += nval
        net_volume += nvol
        total_bval += bval
        total_bvol += bvol
        brokers.append({
            "code": b.get("broker_code"),
            "name": b.get("broker_name"),
            "bval": bval, "bvol": bvol, "bavg": _avg(bval, bvol),
            "sval": sval, "svol": svol, "savg": _avg(sval, svol),
            "nval": nval, "nvol": nvol,
        })

    ranked = sorted(brokers, key=lambda x: abs(x["nval"]), reverse=True)
    top = []
    for n in (1, 3, 5):
        chunk = ranked[:n]
        top.append({
            "n": n,
            "net_value": sum(x["nval"] for x in chunk),
            "net_volume": sum(x["nvol"] for x in chunk),
        })

    levels = []
    for lvl in data.get("broker_levels") or []:
        buy = lvl.get("buy") or {}
        sell = lvl.get("sell") or {}
        levels.append({
            "buy": {
                "code": buy.get("broker_code"), "name": buy.get("broker_name"),
                "val": buy.get("bval"), "vol": buy.get("bvol"), "avg": buy.get("bavg"),
            },
            "sell": {
                "code": sell.get("broker_code"), "name": sell.get("broker_name"),
                "val": sell.get("sval"), "vol": sell.get("svol"), "avg": sell.get("savg"),
            },
        })

    return {
        "stock_code": data.get("stock_code"),
        "flow": data.get("flow"),
        "net": data.get("broker_net"),
        "start_date": data.get("broker_start_date"),
        "end_date": data.get("broker_end_date"),
        "summary": {
            "buyer_count": buyer_count,
            "seller_count": seller_count,
            "net_value": net_value,
            "net_volume": net_volume,
            "avg_price": _avg(total_bval, total_bvol),
        },
        "top": top,
        "levels": levels,
        "brokers": brokers,
    }


class IdxEdgeProvider:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self._calls_today = 0
        self._quota_day = date.today()
        # Sisa kuota dari header `x-ratelimit-remaining` (sumber kebenaran).
        self.last_ratelimit_remaining: Optional[int] = None
        # Nilai TERKECIL yang terlihat hari ini. Request paralel bisa datang tidak
        # berurutan, jadi yang dipakai untuk keputusan adalah minimum, bukan yang
        # terakhir.
        self.min_ratelimit_remaining: Optional[int] = None

    @property
    def enabled(self) -> bool:
        return bool(settings.idx_edge_api_key)

    @property
    def calls_today(self) -> int:
        self._roll_quota()
        return self._calls_today

    def reset_quota(self) -> None:
        self._quota_day = date.today()
        self._calls_today = 0
        self.last_ratelimit_remaining = None
        self.min_ratelimit_remaining = None

    def quota_remaining(self) -> Optional[int]:
        """Sisa kuota terpercaya, atau None bila belum diketahui (jangan menebak).

        Sumber kebenaran = header `x-ratelimit-remaining` (minimum yang terlihat
        hari ini). Bila belum ada request sama sekali, kembalikan None supaya
        pemanggil bisa probe/berhenti, bukan mengarang angka.
        """
        return self.min_ratelimit_remaining

    def _roll_quota(self) -> None:
        today = date.today()
        if today != self._quota_day:
            self._quota_day = today
            self._calls_today = 0
            self.last_ratelimit_remaining = None
            self.min_ratelimit_remaining = None

    async def _get_json(
        self, path: str, params: Optional[dict] = None
    ) -> Any:
        if not self.enabled:
            return None
        self._roll_quota()
        budget = settings.idx_edge_daily_quota
        if self._calls_today >= budget:
            logger.warning("Kuota IDX Edge PRO harian habis — request dilewati: %s", path)
            return None
        if budget and self._calls_today >= budget * _QUOTA_WARN_RATIO:
            logger.warning(
                "Kuota IDX Edge PRO hampir habis: %d/%d", self._calls_today, budget
            )

        await request_scheduler.acquire()
        url = f"{settings.idx_edge_base_url}{path}"
        headers = {
            "Accept": "application/json",
            "X-API-Key": settings.idx_edge_api_key,
        }
        try:
            if self._client is not None:
                resp = await self._client.get(
                    url, params=params, headers=headers,
                    timeout=settings.idx_edge_timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=settings.idx_edge_timeout) as client:
                    resp = await client.get(url, params=params, headers=headers)
            self._calls_today += 1
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining is not None:
                try:
                    value = int(remaining)
                    self.last_ratelimit_remaining = value
                    if (
                        self.min_ratelimit_remaining is None
                        or value < self.min_ratelimit_remaining
                    ):
                        self.min_ratelimit_remaining = value
                except ValueError:
                    pass
            if resp.status_code == 401:
                logger.error("IDX Edge PRO: API key tidak valid/absen (401) di %s", path)
                return None
            if resp.status_code == 429:
                logger.warning("IDX Edge PRO: rate limit (429) di %s", path)
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 — kegagalan tidak fatal
            logger.warning("IDX Edge PRO error %s: %s", path, e)
            return None

    async def health(self) -> Optional[dict]:
        data = await self._get_json("/api/health")
        return data if isinstance(data, dict) else None

    async def search(self, q: str) -> list[dict]:
        data = await self._get_json("/api/search", {"q": q})
        return data if isinstance(data, list) else []

    async def fetch_history(
        self, code: str, frame: str = "daily", limit: int = 160
    ) -> Optional[list[dict]]:
        # Validasi sebelum request: limit > 500 ditolak API (422) tapi tetap
        # memakan kuota.
        safe_limit = max(1, min(int(limit), _HISTORY_MAX_LIMIT))
        data = await self._get_json(
            f"/api/history/{code}", {"frame": frame, "limit": safe_limit}
        )
        if isinstance(data, dict):
            return data.get("rows") or []
        return None

    async def fetch_market_cap(
        self, page: int = 1, per_page: int = 50, codes: Optional[list[str]] = None
    ) -> Optional[dict]:
        params: dict = {"page": page, "per_page": per_page}
        if codes:
            params["codes"] = ",".join(codes)
        data = await self._get_json("/api/market-cap", params)
        return data if isinstance(data, dict) else None

    async def fetch_market_cap_all(self, max_pages: int = 25) -> list[dict]:
        """Ambil seluruh emiten dengan paginasi market-cap."""
        rows: list[dict] = []
        page = 1
        total_pages = 1
        while page <= total_pages and page <= max_pages:
            data = await self.fetch_market_cap(page=page, per_page=50)
            if not data:
                break
            rows.extend(data.get("data") or [])
            total_pages = int(data.get("total_pages") or 1)
            page += 1
        return rows

    async def fetch_screener(self) -> Optional[dict]:
        data = await self._get_json("/api/screener/latest")
        return data if isinstance(data, dict) else None

    async def fetch_broker_summary(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        flow: str = "all",
        net: bool = False,
        broker_limit: Optional[int] = None,
        level_limit: Optional[int] = None,
    ) -> Optional[dict]:
        params: dict = {"net": str(net).lower()}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if flow != "all":
            params["flow"] = flow
        if broker_limit:
            params["broker_limit"] = broker_limit
        if level_limit:
            params["level_limit"] = level_limit
        data = await self._get_json(f"/api/broker-summary/{code}", params)
        return data if isinstance(data, dict) else None

    async def fetch_broker_accumulation(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[dict]:
        params: dict = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        data = await self._get_json(
            f"/api/broker-accumulation/{code}", params or None
        )
        return data if isinstance(data, dict) else None

    async def fetch_analysis(self, code: str) -> Optional[dict]:
        data = await self._get_json(f"/api/analysis/{code}")
        return data if isinstance(data, dict) else None

    async def fetch_seasonal(self, code: str) -> Optional[dict]:
        data = await self._get_json(f"/api/seasonal/{code}")
        return data if isinstance(data, dict) else None

    async def fetch_insiders(
        self, code: str, page: int = 1, limit: int = 20,
        action_type: Optional[str] = None,
    ) -> Optional[dict]:
        params: dict = {"page": page, "limit": limit}
        if action_type:
            params["action_type"] = action_type
        data = await self._get_json(f"/api/insiders/{code}", params)
        return data if isinstance(data, dict) else None

    async def fetch_financial_statements(
        self, code: str, report_type: Optional[str] = None,
        period: Optional[str] = None, limit: Optional[int] = None,
        year: Optional[str] = None,
    ) -> Optional[dict]:
        params: dict = {}
        if report_type:
            params["report_type"] = report_type
        if period:
            params["period"] = period
        if limit:
            params["limit"] = limit
        if year:
            params["year"] = year
        data = await self._get_json(f"/api/financial-statements/{code}", params)
        return data if isinstance(data, dict) else None

    async def fetch_done_details(
        self, code: str, date: Optional[str] = None,
        page: int = 1, per_page: int = 100,
    ) -> Optional[dict]:
        params: dict = {"code": code, "page": page, "per_page": per_page}
        if date:
            params["date"] = date
        data = await self._get_json("/api/done-details", params)
        return data if isinstance(data, dict) else None
