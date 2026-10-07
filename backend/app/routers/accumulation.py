"""Router akumulasi — trigger scan (token) + baca hasil (DB saja).

POST dijalankan di background, balas 202 + scan_id. GET hanya membaca database
dan tidak memicu request apa pun ke IDX Edge.
"""

import asyncio
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.repositories import accumulation_repository as repo
from app.services import accumulation_scan as scan_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["accumulation"])


def _check_token(provided: Optional[str]) -> None:
    configured = settings.accumulation_scan_token
    if not configured:
        raise HTTPException(status_code=403, detail="Scan token belum dikonfigurasi.")
    if not provided or not hmac.compare_digest(provided, configured):
        raise HTTPException(status_code=403, detail="Token scan tidak valid.")


@router.post("/accumulation/scan")
async def trigger_scan(
    force: bool = False, x_scan_token: Optional[str] = Header(default=None)
):
    if not settings.accumulation_enabled:
        raise HTTPException(status_code=403, detail="Fitur scan tidak aktif.")
    _check_token(x_scan_token)

    out = await scan_svc.trigger_scan_if_stale(force=force, tag="endpoint")
    if out.get("reason") == "busy":
        raise HTTPException(status_code=409, detail="Scan sedang berjalan.")
    if out.get("reason") == "begin-error":
        raise HTTPException(status_code=500, detail="Gagal memulai scan.")
    if not out.get("ok"):
        latest = await repo.get_latest_scan(limit=1)
        return JSONResponse(
            status_code=200,
            content={
                "success": True, "skipped": True,
                "scan_id": (latest or {}).get("id"),
                "scan_date": out.get("scan_date") or (latest or {}).get("scan_date"),
                "reason": out.get("reason", "skip"),
            },
        )
    return JSONResponse(
        status_code=202,
        content={
            "success": True, "accepted": True,
            "scan_id": out.get("scan_id"), "scan_date": out.get("scan_date"),
        },
    )


@router.get("/accumulation/latest")
async def latest(limit: int = 50):
    data = await repo.get_latest_scan(limit=limit)
    if not data:
        return {"success": False, "error": "Belum ada hasil scan."}
    return {"success": True, "data": data}


@router.get("/accumulation/{ticker}")
async def by_ticker(ticker: str):
    data = await repo.get_signal(ticker)
    if not data:
        return {"success": False, "error": f"Tidak ada sinyal untuk {ticker.upper()}."}
    return {"success": True, "data": data}
