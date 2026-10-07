"""Penjadwal scan akumulasi harian — stdlib asyncio saja, tanpa dependensi baru.

Satu scan per tanggal data. Dijalankan tiap hari bursa 19:30 WIB
(setelah pasar tutup) + sekali saat startup bila data basi.
Single-flight memakai scan.begin_scan/continue_scan yang sudah ada.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

from app.config import settings
from app.repositories import accumulation_repository as repo
from app.services import accumulation_scan as scan

logger = logging.getLogger(__name__)

_WIB = 7
_RUN_HOUR_WIB = 19
_RUN_MINUTE_WIB = 30
_STARTUP_DELAY_S = 30
_ERROR_RETRY_S = 300


def is_market_day(d: date) -> bool:
    return d.weekday() < 5


def data_date_today_wib(now: datetime) -> date:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now + timedelta(hours=_WIB)).date()


def next_run_at(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    wib = now + timedelta(hours=_WIB)
    candidate = wib.replace(hour=_RUN_HOUR_WIB, minute=_RUN_MINUTE_WIB, second=0, microsecond=0)
    d = wib.date()
    if candidate <= wib or not is_market_day(d):
        d += timedelta(days=1)
        while not is_market_day(d):
            d += timedelta(days=1)
        candidate = candidate.replace(year=d.year, month=d.month, day=d.day)
    return candidate - timedelta(hours=_WIB)


async def _run_one_cycle(tag: str) -> dict:
    """Satu siklus begin->continue. Me-return prep/result, tak pernah raise."""
    if not settings.accumulation_enabled or not settings.accumulation_scan_token:
        logger.info("scheduler akumulasi nonaktif (%s): lewati", tag)
        return {"ok": False, "reason": "disabled"}
    if scan.scan_running():
        logger.info("scheduler akumulasi (%s): scan sedang berjalan, lewati", tag)
        return {"ok": False, "reason": "busy"}
    try:
        prep = await scan.begin_scan(force=False)
    except Exception as e:  # noqa: BLE001
        logger.warning("scheduler akumulasi (%s): begin_scan error: %s", tag, e)
        return {"ok": False, "reason": "begin-error"}
    if not prep.get("ok"):
        return {"ok": False, "skipped": True, "scan_date": prep.get("scan_date"), "reason": prep.get("reason", "skip")}
    try:
        await scan.continue_scan(prep, force=False)
        return {"ok": True, "scan_id": prep.get("scan_id"), "scan_date": prep.get("scan_date")}
    except Exception as e:  # noqa: BLE001
        logger.exception("scheduler akumulasi (%s): continue_scan error", tag)
        return {"ok": False, "reason": "continue-error"}


async def _wait_until(stop: asyncio.Event, target: datetime, now_fn: Callable[[], datetime]) -> bool:
    while not stop.is_set():
        delay = (target - now_fn()).total_seconds()
        if delay <= 0:
            return True
        await asyncio.wait_for(stop.wait(), timeout=min(delay, 60.0))
    return False


async def accumulation_daily_loop(
    stop: asyncio.Event,
    now_fn: Optional[Callable[[], datetime]] = None,
    initial_delay_s: float = _STARTUP_DELAY_S,
    error_retry_s: float = _ERROR_RETRY_S,
) -> None:
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    latest = await repo.get_latest_scan(limit=1)
    today_data = data_date_today_wib(now_fn())
    if not latest or latest.get("scan_date") != today_data.isoformat() or latest.get("status") != "complete":
        await asyncio.sleep(0)
        if stop.is_set():
            return
        await asyncio.sleep(initial_delay_s)
        if not stop.is_set():
            await _run_one_cycle("startup")
    while not stop.is_set():
        target = next_run_at(now_fn())
        if not await _wait_until(stop, target, now_fn):
            return
        result = await _run_one_cycle("jadwal")
        if not result.get("ok") and not result.get("skipped"):
            await asyncio.wait_for(stop.wait(), timeout=error_retry_s)
