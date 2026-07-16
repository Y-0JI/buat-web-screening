import asyncio
import re
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.stock import ResearchRequest, ResearchResponse
from app.data.fetcher import fetch_stock_data, fetch_company_info, fetch_news, fetch_fundamentals, verify_ticker
from app.scoring.funnel import calculate_score
from app.ai.orchestrator import enhance_with_ai
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["research"])


async def extract_ticker(text: str) -> str | None:
    candidates = re.findall(r"\b([A-Z]{2,5})\b", text.upper())
    if not candidates:
        return None
    results = await asyncio.gather(*[verify_ticker(c) for c in candidates], return_exceptions=True)
    for candidate, result in zip(candidates, results):
        if result is True:
            return candidate
    try:
        from app.data.idx_stocks import VALID_TICKERS
        for c in candidates:
            if c in VALID_TICKERS:
                return c
    except ImportError:
        pass
    return None


@router.post("/research", response_model=ResearchResponse)
async def research(
    req: ResearchRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
):
    ticker = req.ticker or await extract_ticker(req.query)
    if not ticker:
        return ResearchResponse(success=False, error="Tidak ada ticker saham ditemukan")

    df, is_simulated = await fetch_stock_data(ticker)
    if df is None or df.empty:
        return ResearchResponse(
            success=False, error=f"Data untuk {ticker} tidak ditemukan"
        )

    info = await fetch_company_info(ticker)
    mode = (req.mode or "BSJP").upper()
    report = calculate_score(df, ticker, mode, is_simulated=is_simulated)
    report.company_name = info.get("name", ticker)
    report.mode = mode

    if user:
        session.add(ScanHistory(
            user_id=user.id, ticker=ticker.upper(),
            score=report.score, verdict=report.verdict.value,
        ))
        await session.commit()

    if not is_simulated:
        news_result, fund_result = await asyncio.gather(
            fetch_news(ticker, limit=10),
            fetch_fundamentals(ticker),
        )
        report.news = news_result.get("items") if not news_result.get("error") else None
        report.fundamentals = fund_result if not fund_result.get("error") else None

    try:
        report = await enhance_with_ai(report)
    except Exception as e:
        report.summary += f" | AI enhancement gagal: {str(e)}"

    return ResearchResponse(success=True, data=report)


@router.post("/resolve-tickers")
async def resolve_tickers(req: dict):
    text_in = req.get("text", "")
    candidates = re.findall(r"\b([A-Z]{2,5})\b", text_in.upper())
    results = await asyncio.gather(*[verify_ticker(c) for c in candidates], return_exceptions=True)
    valid = [c for c, ok in zip(candidates, results) if ok is True]
    try:
        from app.data.idx_stocks import VALID_TICKERS
        for c in candidates:
            if c in VALID_TICKERS and c not in valid:
                valid.append(c)
    except ImportError:
        pass
    return {"tickers": valid[:5]}


@router.get("/health")
async def health():
    return {"status": "ok"}
