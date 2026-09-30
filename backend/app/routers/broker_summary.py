"""Router broker summary — proxy IDX Edge PRO untuk kartu di frontend."""

from typing import Optional

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider, broker_summary_payload

router = APIRouter(prefix="/api", tags=["broker-summary"])


@router.get("/broker-summary/{ticker}")
async def broker_summary(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    flow: str = "all",
    net: bool = False,
    limit: int = 20,
):
    data = await IdxEdgeProvider().fetch_broker_summary(
        ticker.upper(),
        start_date=start_date,
        end_date=end_date,
        flow=flow,
        net=net,
        broker_limit=limit,
        level_limit=5,
    )
    payload = broker_summary_payload(data)
    if not payload:
        return {"success": False, "error": "Broker summary tidak tersedia."}
    return {"success": True, "data": payload}
