"""Router pencarian emiten — untuk autocomplete kotak search dashboard."""

from fastapi import APIRouter

from app.providers.idx_edge_provider import IdxEdgeProvider

router = APIRouter(prefix="/api", tags=["search"])

_MAX_RESULTS = 8


def search_payload(rows: list[dict] | None) -> list[dict]:
    """Normalisasi hasil /api/search → [{code, name, last_date}]."""
    out = []
    for r in rows or []:
        code = str(r.get("stock_code") or "").upper()
        if not code:
            continue
        out.append({
            "code": code,
            "name": r.get("stock_name"),
            "last_date": r.get("last_date"),
        })
        if len(out) >= _MAX_RESULTS:
            break
    return out


@router.get("/search")
async def search_stocks(q: str = ""):
    query = (q or "").strip()
    if not query:
        return {"success": True, "query": "", "data": []}
    rows = await IdxEdgeProvider().search(query)
    return {"success": True, "query": query, "data": search_payload(rows)}
