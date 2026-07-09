from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user
from app.schemas.stock import HistoryItem, HistoryResponse

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryResponse)
async def list_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
):
    result = await session.execute(
        select(ScanHistory)
        .where(ScanHistory.user_id == user.id)
        .order_by(ScanHistory.created_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    data = [
        HistoryItem(
            id=h.id,
            ticker=h.ticker,
            score=h.score,
            verdict=h.verdict,
            created_at=h.created_at.isoformat() if h.created_at else "",
        )
        for h in items
    ]
    return HistoryResponse(success=True, data=data)