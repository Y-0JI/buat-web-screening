"""Repository akumulasi — CRUD tipis untuk scans/signals/rotation.

Tanpa logika skor: skor & komponen dihitung di lapisan analisis, di sini hanya
disimpan/dibaca. Semua fungsi mengembalikan dict polos.
"""

from datetime import date
from typing import Optional

from sqlalchemy import desc, select

from app.database import async_session
from app.database.models import (
    AccumulationRotation,
    AccumulationScan,
    AccumulationSignal,
)


def _signal_dict(s: AccumulationSignal) -> dict:
    return {
        "id": s.id,
        "scan_id": s.scan_id,
        "ticker": s.ticker,
        "score": s.score,
        "depth": s.depth,
        "components": s.components,
        "reasons": s.reasons,
        "close": s.close,
        "foreign_net": s.foreign_net,
        "broker_net": s.broker_net,
    }


def _scan_dict(scan: AccumulationScan, signals: Optional[list[dict]] = None) -> dict:
    data = {
        "id": scan.id,
        "scan_date": scan.scan_date.isoformat() if scan.scan_date else None,
        "status": scan.status,
        "universe_count": scan.universe_count,
        "stage_b_count": scan.stage_b_count,
        "stage_c_count": scan.stage_c_count,
        "requests_used": scan.requests_used,
        "quota_remaining": scan.quota_remaining,
        "note": scan.note,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
    }
    if signals is not None:
        data["signals"] = signals
    return data


async def save_scan(
    scan_date: date,
    status: str,
    universe_count: int = 0,
    stage_b_count: int = 0,
    stage_c_count: int = 0,
    requests_used: int = 0,
    quota_remaining: Optional[int] = None,
    note: Optional[str] = None,
    signals: Optional[list[dict]] = None,
    force: bool = False,
) -> dict:
    """Simpan satu scan. Unik per `scan_date`.

    Scan `complete` yang sudah ada TIDAK ditimpa kecuali `force=True`.
    Scan `partial` yang ada akan diganti (refresh).
    """
    async with async_session() as session:
        existing = (
            await session.execute(
                select(AccumulationScan).where(AccumulationScan.scan_date == scan_date)
            )
        ).scalar_one_or_none()

        if existing is not None:
            if existing.status == "complete" and not force:
                result = _scan_dict(existing)
                result["skipped"] = True
                return result
            await session.delete(existing)
            await session.flush()

        scan = AccumulationScan(
            scan_date=scan_date,
            status=status,
            universe_count=universe_count,
            stage_b_count=stage_b_count,
            stage_c_count=stage_c_count,
            requests_used=requests_used,
            quota_remaining=quota_remaining,
            note=note,
        )
        session.add(scan)
        await session.flush()

        for s in signals or []:
            session.add(
                AccumulationSignal(
                    scan_id=scan.id,
                    ticker=str(s.get("ticker", "")).upper()[:16],
                    score=float(s.get("score") or 0.0),
                    depth=str(s.get("depth") or "hv"),
                    components=s.get("components"),
                    reasons=s.get("reasons"),
                    close=s.get("close"),
                    foreign_net=s.get("foreign_net"),
                    broker_net=s.get("broker_net"),
                )
            )
        await session.commit()
        await session.refresh(scan)
        result = _scan_dict(scan)
        result["skipped"] = False
        return result


async def get_scan_by_date(scan_date: date) -> Optional[dict]:
    async with async_session() as session:
        scan = (
            await session.execute(
                select(AccumulationScan).where(AccumulationScan.scan_date == scan_date)
            )
        ).scalar_one_or_none()
        if scan is None:
            return None
        return _scan_dict(scan)


async def get_latest_scan(limit: int = 50) -> Optional[dict]:
    """Scan terbaru beserta sinyalnya, diurut skor menurun."""
    async with async_session() as session:
        scan = (
            await session.execute(
                select(AccumulationScan)
                .order_by(desc(AccumulationScan.scan_date))
                .limit(1)
            )
        ).scalar_one_or_none()
        if scan is None:
            return None
        signals = (
            await session.execute(
                select(AccumulationSignal)
                .where(AccumulationSignal.scan_id == scan.id)
                .order_by(desc(AccumulationSignal.score))
                .limit(limit)
            )
        ).scalars().all()
        return _scan_dict(scan, [_signal_dict(s) for s in signals])


async def list_signals(scan_id: int, limit: int = 50) -> list[dict]:
    async with async_session() as session:
        signals = (
            await session.execute(
                select(AccumulationSignal)
                .where(AccumulationSignal.scan_id == scan_id)
                .order_by(desc(AccumulationSignal.score))
                .limit(limit)
            )
        ).scalars().all()
        return [_signal_dict(s) for s in signals]


async def get_signal(ticker: str) -> Optional[dict]:
    """Sinyal terbaru untuk satu ticker (dari scan terbaru)."""
    ticker = ticker.upper()
    async with async_session() as session:
        scan = (
            await session.execute(
                select(AccumulationScan)
                .order_by(desc(AccumulationScan.scan_date))
                .limit(1)
            )
        ).scalar_one_or_none()
        if scan is None:
            return None
        sig = (
            await session.execute(
                select(AccumulationSignal)
                .where(
                    AccumulationSignal.scan_id == scan.id,
                    AccumulationSignal.ticker == ticker,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return _signal_dict(sig) if sig else None


async def upsert_rotation(entries: list[dict], scan_id: int) -> None:
    """Catat kapan tiap ticker terakhir dicek: entries=[{ticker, stratum}]."""
    async with async_session() as session:
        for e in entries:
            ticker = str(e.get("ticker", "")).upper()[:16]
            if not ticker:
                continue
            row = await session.get(AccumulationRotation, ticker)
            if row is None:
                row = AccumulationRotation(ticker=ticker)
                session.add(row)
            row.stratum = int(e.get("stratum") or 0)
            row.last_checked_scan_id = scan_id
        await session.commit()


async def get_rotation_map(tickers: Optional[list[str]] = None) -> dict[str, int]:
    """Peta ticker -> last_checked_scan_id (None jadi -1)."""
    async with async_session() as session:
        stmt = select(AccumulationRotation)
        if tickers:
            stmt = stmt.where(
                AccumulationRotation.ticker.in_([t.upper() for t in tickers])
            )
        rows = (await session.execute(stmt)).scalars().all()
        return {
            r.ticker: (r.last_checked_scan_id if r.last_checked_scan_id is not None else -1)
            for r in rows
        }
