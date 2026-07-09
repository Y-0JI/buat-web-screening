from fastapi import APIRouter
from app.schemas.stock import (
    ComparisonRequest,
    ComparisonResponse,
    ScreeningResponse,
    RankingItem,
    Verdict,
)
from app.data.fetcher import fetch_stock_data, fetch_company_info, MOCK_DATA
from app.scoring.funnel import calculate_score
from app.scheduler import get_cached_screening, run_batch_scan

router = APIRouter(prefix="/api", tags=["screening"])


@router.post("/compare", response_model=ComparisonResponse)
async def compare(req: ComparisonRequest):
    reports = []
    for ticker in req.tickers:
        df = fetch_stock_data(ticker)
        if df is None or df.empty:
            return ComparisonResponse(
                success=False, error=f"Data untuk {ticker} tidak ditemukan"
            )
        info = fetch_company_info(ticker)
        report = calculate_score(df, ticker)
        report.company_name = info.get("name", ticker)
        report.render = "comparison"
        reports.append(report)

    return ComparisonResponse(success=True, data=reports)


@router.get("/screen", response_model=ScreeningResponse)
async def screen():
    cached = get_cached_screening()
    if cached:
        items = []
        for i, r in enumerate(cached, 1):
            items.append(RankingItem(
                rank=i,
                ticker=r["ticker"],
                company_name=r.get("company_name"),
                score=float(r["score"]),
                verdict=Verdict(r["verdict"]),
                confidence=float(r["confidence"]),
                summary=r["summary"],
                price=r.get("price"),
                change_percent=r.get("change_percent"),
            ))
        return ScreeningResponse(success=True, data=items)

    raw = []
    for ticker in MOCK_DATA:
        df = fetch_stock_data(ticker)
        if df is None or df.empty:
            continue
        info = fetch_company_info(ticker)
        report = calculate_score(df, ticker)
        report.company_name = info.get("name", ticker)
        raw.append(report)

    raw.sort(key=lambda x: x.score, reverse=True)
    top = raw[:10]
    items = []
    for i, r in enumerate(top, 1):
        items.append(RankingItem(
            rank=i,
            ticker=r.ticker,
            company_name=r.company_name,
            score=r.score,
            verdict=r.verdict,
            confidence=r.confidence,
            summary=r.summary,
            price=r.price,
            change_percent=r.change_percent,
        ))

    return ScreeningResponse(success=True, data=items)
