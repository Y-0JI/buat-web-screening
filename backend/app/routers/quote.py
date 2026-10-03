"""Router quote saham — harga terakhir + nama untuk header dashboard."""

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider

router = APIRouter(prefix="/api", tags=["quote"])


def quote_payload(code: str, price: dict | None, name: str | None) -> dict | None:
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
    return {
        "ticker": code,
        "name": name,
        "last_price": last,
        "lot": lot,
        "value": val,
        "freq": freq,
        "market_state": price.get("market_state"),
        "market_label": price.get("market_label"),
    }


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
    payload = quote_payload(code, price, await resolve_name(provider, code))
    return {"success": payload is not None, "ticker": code, "data": payload}
