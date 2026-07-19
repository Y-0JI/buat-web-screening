import asyncio
import logging
import re
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.stock import ResearchRequest, ResearchResponse
from app.services import (
    stock_service,
    company_profile_service,
    news_service,
    fundamentals_service,
)
from app.utils.errors import AppError
from app.repositories.technical_cache import calculate_score_cached
from app.ai.orchestrator import enhance_with_ai
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["research"])


async def extract_ticker(text: str) -> str | None:
    candidates = re.findall(r"\b([A-Z]{2,5})\b", text.upper())
    if not candidates:
        return None
    results = await asyncio.gather(*[stock_service.verify_ticker(c) for c in candidates], return_exceptions=True)
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

    df, is_simulated = await stock_service.get_price(ticker)
    if df is None or df.empty:
        return ResearchResponse(
            success=False, error=f"Data untuk {ticker} tidak ditemukan"
        )

    info = await company_profile_service.get_profile(ticker)
    mode = (req.mode or "BSJP").upper()
    report = await calculate_score_cached(df, ticker, mode, is_simulated=is_simulated)
    report.company_name = info.get("name", ticker)
    report.mode = mode

    if user:
        session.add(ScanHistory(
            user_id=user.id, ticker=ticker.upper(),
            score=report.score, verdict=report.verdict.value,
        ))
        await session.commit()

    if not is_simulated:
        try:
            news_data = await news_service.get_news(ticker, limit=10)
            report.news = [item.model_dump() for item in news_data.items]
        except AppError:
            report.news = None
        try:
            report.fundamentals = await fundamentals_service.get_fundamentals(ticker)
        except AppError:
            report.fundamentals = None

    try:
        report = await enhance_with_ai(report)
    except Exception as e:
        logger.error("AI enhancement gagal untuk %s: %s", ticker, e, exc_info=True)
        report.ai_available = False
        report.summary += " | Insight AI sedang tidak tersedia, silakan coba lagi."

    return ResearchResponse(success=True, data=report)


@router.post("/resolve-tickers")
async def resolve_tickers(req: dict):
    text_in = req.get("text", "")
    candidates = re.findall(r"\b([A-Z]{2,5})\b", text_in.upper())
    results = await asyncio.gather(*[stock_service.verify_ticker(c) for c in candidates], return_exceptions=True)
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
