"""Router seasonality — return bulanan per tahun untuk tab Seasonality."""

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider

router = APIRouter(prefix="/api", tags=["seasonality"])

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def seasonal_payload(code: str, data: dict | None) -> dict | None:
    """Normalisasi respons /api/seasonal -> tabel bulan x tahun."""
    if not data:
        return None
    monthly = data.get("monthly_returns") or {}
    if not isinstance(monthly, dict) or not monthly:
        return None
    years: list[str] = data.get("years") or sorted(
        {str(y) for m in monthly.values() if isinstance(m, dict) for y in m},
        reverse=True,
    )[:10]
    avg = data.get("yearly_avg")
    return {
        "ticker": code,
        "years": years,
        "months": _MONTHS,
        "monthly_returns": monthly,
        "summary": data.get("summary"),
        "yearly_avg": avg if isinstance(avg, (int, float)) else None,
    }


@router.get("/seasonal/{ticker}")
async def seasonal(ticker: str):
    code = ticker.upper()
    data = await IdxEdgeProvider().fetch_seasonal(code)
    payload = seasonal_payload(code, data)
    if not payload:
        return {"success": False, "error": "Data seasonality tidak tersedia."}
    return {"success": True, "data": payload}
