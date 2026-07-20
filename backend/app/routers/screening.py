import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
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
    is_scanning,
    run_batch_scan,
)
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
    async def process_ticker(ticker: str):
        df, is_simulated = await stock_service.get_price(ticker)
        if df is None or df.empty:
            return None
        info = await company_profile_service.get_profile(ticker)
        report = await calculate_score_cached(df, ticker, req.mode, is_simulated=is_simulated)
        report.company_name = info.get("name", ticker)
        report.render = "comparison"
        report.mode = req.mode
        if user:
            session.add(ScanHistory(
                user_id=user.id, ticker=ticker.upper(),
                score=report.score, verdict=report.verdict.value,
            ))
        return report

    results = await asyncio.gather(*[process_ticker(t) for t in req.tickers])
    reports = [r for r in results if r is not None]

    if len(reports) != len(req.tickers):
        return ComparisonResponse(
            success=False, error="Data untuk beberapa saham tidak ditemukan"
        )

    if user:
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
async def screen(background: BackgroundTasks, mode: str = "BSJP"):
    cached, cached_mode = await get_cached_screening(mode)
    if not (cached and cached_mode == mode) and not await is_scanning(mode):
        # cold miss: scan universe (~978 ticker @ 60/menit ≈ 16 mnt)
        # di background, jangan di dalam request (axios FE timeout 45s).
        # Cache scheduler 16:30 WIB + pre-warm startup yg menghangatkan;
        # request langsung balik (data bisa kosong sekali) tanpa timeout.
        # Guard is_scanning agar reload beruntun tak memicu scan duplikat.
        background.add_task(run_batch_scan, mode)

    rows = cached or []
    ts = await get_screening_timestamp(mode)
    generated_at = datetime.fromtimestamp(ts).isoformat() if ts else None
    return ScreeningResponse(
        success=True, data=_to_ranking_items(rows), generated_at=generated_at
    )
