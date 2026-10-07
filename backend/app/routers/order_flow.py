"""Router order flow — tape done-details untuk tabel Done Details."""

from typing import Optional

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider

router = APIRouter(prefix="/api", tags=["order-flow"])

_MAX_LIMIT = 100


def order_flow_payload(data: Optional[dict]) -> Optional[dict]:
    """Normalisasi respons /api/done-details → baris cetak per transaksi."""
    if not data:
        return None
    rows = []
    for r in data.get("data") or []:
        price = r.get("price_num")
        if price is None:
            try:
                price = float(str(r.get("price") or "0").replace(",", ""))
            except (TypeError, ValueError):
                price = None
        try:
            lot = float(r.get("lot") or r.get("qty_num") or 0)
        except (TypeError, ValueError):
            lot = 0.0
        rows.append({
            "time": r.get("time"),
            "action": str(r.get("action") or "").upper() or None,
            "price": price,
            "lot": lot,
            "value": r.get("value_raw"),
            "buyer": r.get("buyer"),
            "seller": r.get("seller"),
            "buyer_type": r.get("buyer_type"),
            "seller_type": r.get("seller_type"),
            "board": r.get("market_board"),
        })
    return {
        "code": data.get("code"),
        "date": data.get("date"),
        "total": data.get("total"),
        "page": data.get("page", 1),
        "per_page": data.get("per_page"),
        "total_pages": data.get("total_pages", 1),
        "rows": rows,
    }


@router.get("/order-flow/{ticker}")
async def order_flow(ticker: str, date: Optional[str] = None, limit: int = 50, page: int = 1):
    limit = max(1, min(int(limit or 50), _MAX_LIMIT))
    page = max(1, int(page or 1))
    data = await IdxEdgeProvider().fetch_done_details(
        ticker.upper(), date=date or None, page=page, per_page=limit
    )
    payload = order_flow_payload(data)
    if not payload:
        return {"success": False, "error": "Order flow tidak tersedia."}
    return {"success": True, "data": payload}


def done_dates_payload(data: Optional[dict]) -> Optional[dict]:
    """Normalisasi respons /api/done-details/dates -> daftar tanggal."""
    if not data:
        return None
    dates = [d for d in (data.get("dates") or []) if isinstance(d, str)]
    code = data.get("code")
    return {
        "code": code,
        "count": data.get("count", len(dates)),
        "dates": dates,
    }


@router.get("/order-flow/{ticker}/dates")
async def order_flow_dates(ticker: str):
    data = await IdxEdgeProvider().fetch_done_detail_dates(ticker.upper())
    payload = done_dates_payload(data)
    if not payload or not payload["dates"]:
        return {"success": False, "error": "Daftar tanggal tidak tersedia."}
    return {"success": True, "data": payload}
