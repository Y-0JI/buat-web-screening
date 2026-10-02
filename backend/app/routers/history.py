"""Router riwayat harga — proxy IDX Edge PRO untuk chart di frontend."""

from datetime import date

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider, history_series

router = APIRouter(prefix="/api", tags=["history"])

_PERIOD_LIMITS = {
    "1w": 5, "1m": 22, "1mo": 22, "3m": 66, "3mo": 66, "6mo": 126, "1y": 252,
}


def period_to_limit(period: str) -> int:
    """Petakan periode UI (1D/1W/1M/3M/YTD/1Y) ke jumlah bar harian.

    API menolak limit < 20 dan > 500, jadi selalu di-clamp.
    """
    p = (period or "").lower()
    if p in _PERIOD_LIMITS:
        limit = _PERIOD_LIMITS[p]
    elif p == "1d":
        limit = 20
    elif p == "ytd":
        start = date(date.today().year, 1, 1).toordinal()
        limit = date.today().toordinal() - start
    else:
        limit = 66
    return max(20, min(500, limit))


@router.get("/history/{ticker}")
async def get_history(ticker: str, period: str = "3mo"):
    limit = period_to_limit(period)
    rows = await IdxEdgeProvider().fetch_history(ticker.upper(), limit=limit)
    data = history_series(rows)
    return {
        "success": bool(data),
        "ticker": ticker.upper(),
        "period": period,
        "data": data,
    }
