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
import pandas as pd

from app.config import settings
from app.providers.scheduler import request_scheduler

logger = logging.getLogger(__name__)

_QUOTA_WARN_RATIO = 0.9


def rows_to_price_df(rows: Optional[list[dict]]) -> Optional[pd.DataFrame]:
    """Konversi `rows` respons /api/history → DataFrame siap scoring.

    Index = DatetimeIndex terurut naik; kolom = Open/High/Low/Close/Volume
    (kapitalisasi awal, sama seperti `_flatten_columns`).
    """
    if not rows:
        return None
    records = []
    for r in rows:
        date_val = r.get("date")
        if not date_val:
            continue
        try:
            records.append({
                "Date": pd.to_datetime(date_val),
                "Open": float(r.get("open") or 0),
                "High": float(r.get("high") or 0),
                "Low": float(r.get("low") or 0),
                "Close": float(r.get("close") or 0),
                "Volume": float(r.get("volume") or 0),
            })
        except (TypeError, ValueError):
            continue
    if not records:
        return None
    return pd.DataFrame(records).sort_values("Date").set_index("Date")


class IdxEdgeProvider:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self._calls_today = 0
        self._quota_day = date.today()

    @property
    def enabled(self) -> bool:
        return bool(settings.idx_edge_api_key)

    def _roll_quota(self) -> None:
        today = date.today()
        if today != self._quota_day:
            self._quota_day = today
            self._calls_today = 0

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
        data = await self._get_json(
            f"/api/history/{code}", {"frame": frame, "limit": limit}
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
        data = await self._get_json(f"/api/broker-summary/{code}", params)
        return data if isinstance(data, dict) else None
