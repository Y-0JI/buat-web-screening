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
        "rows": rows,
    }


@router.get("/order-flow/{ticker}")
async def order_flow(ticker: str, date: Optional[str] = None, limit: int = 50):
    limit = max(1, min(int(limit or 50), _MAX_LIMIT))
    data = await IdxEdgeProvider().fetch_done_details(
        ticker.upper(), date=date or None, per_page=limit
    )
    payload = order_flow_payload(data)
    if not payload:
        return {"success": False, "error": "Order flow tidak tersedia."}
    return {"success": True, "data": payload}
