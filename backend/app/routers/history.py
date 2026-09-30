"""Router riwayat harga — proxy IDX Edge PRO untuk chart di frontend."""

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider, history_series

router = APIRouter(prefix="/api", tags=["history"])

_PERIOD_LIMITS = {"1mo": 22, "3mo": 66, "6mo": 126, "1y": 252}


@router.get("/history/{ticker}")
async def get_history(ticker: str, period: str = "3mo"):
    limit = _PERIOD_LIMITS.get(period, 66)
    rows = await IdxEdgeProvider().fetch_history(ticker.upper(), limit=limit)
    data = history_series(rows)
    return {
        "success": bool(data),
        "ticker": ticker.upper(),
        "period": period,
        "data": data,
    }
