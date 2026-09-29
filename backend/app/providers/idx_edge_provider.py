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
