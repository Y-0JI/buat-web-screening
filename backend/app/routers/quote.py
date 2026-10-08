"""Router quote saham — harga terakhir + nama untuk header dashboard."""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider, history_series

router = APIRouter(prefix="/api", tags=["quote"])

_NAME_TTL = 24 * 3600
_name_cache: dict[str, tuple[float, str | None]] = {}

# Cache close sesi sebelumnya + bar terbaru per ticker per hari (1 request history/hari).
_prev_cache: dict[str, tuple[str, Optional[float], Optional[dict]]] = {}

# Tracker O/H/L sesi hari ini dari harga live (reset harian, perkiraan).
_session_cache: dict[str, tuple[str, dict]] = {}


def _today_wib() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=7)).date().isoformat()


def _fnum(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def quote_payload(
    code: str,
    price: dict | None,
    name: str | None,
    prev_close: Optional[float] = None,
    session: Optional[dict] = None,
    bar: Optional[dict] = None,
) -> dict | None:
    """Normalisasi respons /api/price + nama → struktur untuk header UI."""
    if not price:
        return None
    try:
        last = float(price.get("last_price") or 0)
    except (TypeError, ValueError):
        return None
    lot = price.get("lot")
    try:
        lot = float(lot) if lot is not None else None
    except (TypeError, ValueError):
        lot = None
    val = price.get("value")
    try:
        val = float(val) if val is not None else None
    except (TypeError, ValueError):
        val = None
    freq = price.get("freq")
    try:
        freq = float(freq) if freq is not None else None
    except (TypeError, ValueError):
        freq = None
    change = change_pct = None
    if prev_close:
        change = last - prev_close
        change_pct = change / prev_close * 100
    session = session or {}
    avg = _fnum((bar or {}).get("avg"))
    f_buy = _fnum((bar or {}).get("f_buy"))
    f_sell = _fnum((bar or {}).get("f_sell"))
    return {
        "ticker": code,
        "name": name,
        "last_price": last,
        "lot": lot,
        "value": val,
        "freq": freq,
        "market_state": price.get("market_state"),
        "market_label": price.get("market_label"),
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "day_open": session.get("open"),
        "day_high": session.get("high"),
        "day_low": session.get("low"),
        "day_volume": lot,
        "avg": avg,
        "f_buy_value": f_buy * avg if (f_buy is not None and avg is not None) else None,
        "f_sell_value": f_sell * avg if (f_sell is not None and avg is not None) else None,
    }


async def prev_close_and_bar(
    provider: IdxEdgeProvider, code: str
) -> tuple[Optional[float], Optional[dict]]:
    """Close sesi sebelumnya + bar harian terbaru (avg/f_buy/f_sell) dalam 1 fetch."""
    today = _today_wib()
    cached = _prev_cache.get(code)
    if cached and cached[0] == today:
        return cached[1], cached[2]
    prev: Optional[float] = None
    bar: Optional[dict] = None
    try:
        # API menolak limit < 20; ambil 20 bar terakhir lalu pilih yang di bawah hari ini.
        rows = await provider.fetch_history(code, limit=20)
        data = history_series(rows)
        for row in data:
            if str(row.get("date") or "") < today:
                prev = row.get("close")
        if prev is not None:
            try:
                prev = float(prev)
            except (TypeError, ValueError):
                prev = None
        # Bar terbaru mentah (history_series membuang avg/f_buy/f_sell).
        for r in rows or []:
            d = str(r.get("date") or "")
            if d and (bar is None or d > str(bar.get("date") or "")):
                bar = r
    except Exception:  # noqa: BLE001 — pelengkap, bukan fatal
        prev = None
        bar = None
    _prev_cache[code] = (today, prev, bar)
    return prev, bar


def track_session(code: str, last: float) -> dict:
    """Lacak O/H/L sesi hari ini dari harga live (reset tiap ganti hari)."""
    today = _today_wib()
    cached = _session_cache.get(code)
    if not cached or cached[0] != today:
        session = {"open": last, "high": last, "low": last}
    else:
        session = cached[1]
        session["high"] = max(session.get("high", last), last)
        session["low"] = min(session.get("low", last), last)
    _session_cache[code] = (today, session)
    return session


async def resolve_name(provider: IdxEdgeProvider, code: str) -> str | None:
    """Cari nama emiten, pertama lewat /api/search lalu /api/market-cap."""
    try:
        for row in await provider.search(code):
            if str(row.get("stock_code") or "").upper() == code:
                return row.get("stock_name")
    except Exception:  # noqa: BLE001 — nama pelengkap, bukan fatal
        pass
    try:
        data = await provider.fetch_market_cap(page=1, per_page=50, codes=[code])
        for row in (data or {}).get("data") or []:
            if str(row.get("code") or "").upper() == code:
                return row.get("name")
    except Exception:  # noqa: BLE001
        pass
    return None


@router.get("/quote/{ticker}")
async def get_quote(ticker: str):
    code = ticker.upper()
    provider = IdxEdgeProvider()
    price = await provider.fetch_price(code)
    name: str | None = None
    cached = _name_cache.get(code)
    if cached and time.time() - cached[0] < _NAME_TTL:
        name = cached[1]
    else:
        name = await resolve_name(provider, code)
        _name_cache[code] = (time.time(), name)
    prev, bar = await prev_close_and_bar(provider, code)
    session: dict = {}
    try:
        last = float((price or {}).get("last_price") or 0)
        session = track_session(code, last)
    except (TypeError, ValueError):
        session = {}
    payload = quote_payload(code, price, name, prev, session, bar)
    return {"success": payload is not None, "ticker": code, "data": payload}
