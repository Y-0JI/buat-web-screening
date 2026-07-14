import re
import time
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.stock import ResearchRequest, ResearchResponse, StockReport
from app.data.fetcher import fetch_stock_data, fetch_company_info
from app.data.idx_stocks import VALID_TICKERS
from app.data.ticker_sync import get_listed_tickers
from app.scoring.funnel import calculate_score
from app.ai.orchestrator import enhance_with_ai
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["research"])


_valid_tickers_cache: set[str] | None = None
_valid_tickers_cache_ts: float = 0
_VALID_CACHE_TTL = 300


async def extract_ticker(text: str) -> str | None:
    global _valid_tickers_cache, _valid_tickers_cache_ts
    now = time.time()
    if _valid_tickers_cache is None or (now - _valid_tickers_cache_ts > _VALID_CACHE_TTL):
        raw = await get_listed_tickers()
        _valid_tickers_cache = set(raw)
        _valid_tickers_cache_ts = now
    candidates = re.findall(r"\b([A-Z]{2,5})\b", text.upper())
    for c in candidates:
        if c in _valid_tickers_cache:
            return c
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

    try:
        report = await enhance_with_ai(report)
    except Exception as e:
        report.summary += f" | AI enhancement gagal: {str(e)}"

    return ResearchResponse(success=True, data=report)


@router.get("/health")
async def health():
    return {"status": "ok"}
