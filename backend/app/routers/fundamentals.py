"""Router fundamental — ringkasan fundamental dari IDX Edge PRO (untuk kartu chat)."""

from fastapi import APIRouter

from app.fundamentals import build_fundamentals

router = APIRouter(prefix="/api", tags=["fundamentals"])


@router.get("/fundamentals/{ticker}")
async def fundamentals(ticker: str):
    data = await build_fundamentals(ticker.upper())
    if not data:
        return {"success": False, "error": "Data fundamental tidak tersedia."}
    return {"success": True, "data": data}
