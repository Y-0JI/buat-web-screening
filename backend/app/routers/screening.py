import asyncio
import logging
from datetime import datetime
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
from app.services import stock_service, company_profile_service
from app.repositories.technical_cache import calculate_score_cached
from app.scheduler import (
    get_cached_screening,
    get_screening_timestamp,
    run_batch_scan,
)
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["screening"])


@router.post("/compare", response_model=ComparisonResponse)
async def compare(
    req: ComparisonRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
):
    async def process_ticker(ticker: str) -> tuple | None:
        try:
            df, is_simulated = await stock_service.get_price(ticker)
            if df is None or df.empty:
                return None
            info = await company_profile_service.get_profile(ticker)
            report = await calculate_score_cached(df, ticker, req.mode, is_simulated=is_simulated)
            report.company_name = info.get("name", ticker)
            report.render = "comparison"
            report.mode = req.mode
            return report, ticker
        except Exception as e:
            logger.warning("Gagal proses %s untuk compare: %s", ticker, e)
            return None

    results = await asyncio.gather(*[process_ticker(t) for t in req.tickers])
    reports = []
    histories = []
    for r in results:
        if r is not None:
            report, ticker = r
            reports.append(report)
            if user:
                histories.append(ScanHistory(
                    user_id=user.id, ticker=ticker.upper(),
                    score=report.score, verdict=report.verdict.value,
                ))

    if len(reports) != len(req.tickers):
        return ComparisonResponse(
            success=False, error="Data untuk beberapa saham tidak ditemukan"
        )

    if user and histories:
        for h in histories:
            session.add(h)
        await session.commit()

    return ComparisonResponse(success=True, data=reports)


def _to_ranking_items(rows: list[dict]) -> list[RankingItem]:
    return [
        RankingItem(
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
        )
        for i, r in enumerate(rows, 1)
    ]


@router.get("/screen", response_model=ScreeningResponse)
async def screen(mode: str = "BSJP"):
    cached, cached_mode = await get_cached_screening(mode)
    if not (cached and cached_mode == mode):
        logger.info("Cache cold for mode=%s — triggering background scan", mode)
        asyncio.create_task(run_batch_scan(mode))

    rows = cached or []
    ts = await get_screening_timestamp(mode)
    generated_at = datetime.fromtimestamp(ts).isoformat() if ts else None
    if not rows:
        return ScreeningResponse(
            success=True, data=[], generated_at=generated_at,
            error="Data screening sedang diperbarui, silakan coba lagi dalam beberapa menit."
        )
    return ScreeningResponse(
        success=True, data=_to_ranking_items(rows), generated_at=generated_at
    )
