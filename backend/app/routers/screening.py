from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["screening"])


@router.post("/compare", response_model=ComparisonResponse)
async def compare(
    req: ComparisonRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
):
    reports = []
    for ticker in req.tickers:
        df, is_simulated = fetch_stock_data(ticker)
        if df is None or df.empty:
            return ComparisonResponse(
                success=False, error=f"Data untuk {ticker} tidak ditemukan"
            )
        info = fetch_company_info(ticker)
        report = calculate_score(df, ticker, is_simulated=is_simulated)
        report.company_name = info.get("name", ticker)
        report.render = "comparison"
        reports.append(report)

        if user:
            session.add(ScanHistory(
                user_id=user.id, ticker=ticker.upper(),
                score=report.score, verdict=report.verdict.value,
            ))

    if user:
        await session.commit()

    return ComparisonResponse(success=True, data=reports)


@router.get("/screen", response_model=ScreeningResponse)
async def screen(
    user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
):
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
                is_simulated=r.get("is_simulated", False),
            ))
        return ScreeningResponse(success=True, data=items)

    raw = []
    for ticker in MOCK_DATA:
        df, is_simulated = fetch_stock_data(ticker)
        if df is None or df.empty:
            continue
        info = fetch_company_info(ticker)
        report = calculate_score(df, ticker, is_simulated=is_simulated)
        report.company_name = info.get("name", ticker)
        raw.append(report)

        if user:
            session.add(ScanHistory(
                user_id=user.id, ticker=ticker.upper(),
                score=report.score, verdict=report.verdict.value,
            ))

    if user:
        await session.commit()

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
            is_simulated=r.is_simulated,
        ))

    return ScreeningResponse(success=True, data=items)
