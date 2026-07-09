import re
from fastapi import APIRouter, HTTPException
from app.schemas.stock import ResearchRequest, ResearchResponse, StockReport
from app.data.fetcher import fetch_stock_data, fetch_company_info
from app.scoring.funnel import calculate_score
from app.ai.orchestrator import enhance_with_ai

router = APIRouter(prefix="/api", tags=["research"])


def extract_ticker(text: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,5})\b", text.upper())
    return match.group(1) if match else None


@router.post("/research", response_model=ResearchResponse)
async def research(req: ResearchRequest):
    ticker = req.ticker or extract_ticker(req.query)
    if not ticker:
        return ResearchResponse(success=False, error="Tidak ada ticker saham ditemukan")

    df = fetch_stock_data(ticker)
    if df is None or df.empty:
        return ResearchResponse(
            success=False, error=f"Data untuk {ticker} tidak ditemukan"
        )

    info = fetch_company_info(ticker)
    report = calculate_score(df, ticker)
    report.company_name = info.get("name", ticker)

    try:
        report = enhance_with_ai(report)
    except Exception as e:
        report.summary += f" | AI enhancement gagal: {str(e)}"

    return ResearchResponse(success=True, data=report)


@router.get("/health")
async def health():
    return {"status": "ok"}
