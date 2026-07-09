from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.database.models import User, Watchlist
from app.routers.auth import get_current_user
from app.schemas.stock import WatchlistItem, AddWatchlistRequest, WatchlistResponse

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
async def list_watchlist(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Watchlist).where(Watchlist.user_id == user.id).order_by(Watchlist.added_at.desc())
    )
    items = result.scalars().all()
    data = [
        WatchlistItem(
            id=w.id,
            ticker=w.ticker,
            note=w.note,
            added_at=w.added_at.isoformat() if w.added_at else "",
        )
        for w in items
    ]
    return WatchlistResponse(success=True, data=data)


@router.post("", response_model=WatchlistResponse)
async def add_watchlist(
    req: AddWatchlistRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(Watchlist).where(
            Watchlist.user_id == user.id, Watchlist.ticker == req.ticker.upper()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Saham sudah di watchlist")

    w = Watchlist(user_id=user.id, ticker=req.ticker.upper(), note=req.note)
    session.add(w)
    await session.commit()
    await session.refresh(w)

    return WatchlistResponse(
        success=True,
        data=[
            WatchlistItem(
                id=w.id, ticker=w.ticker, note=w.note, added_at=w.added_at.isoformat() if w.added_at else ""
            )
        ],
    )


@router.delete("/{ticker}", response_model=WatchlistResponse)
async def remove_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(Watchlist).where(
            Watchlist.user_id == user.id, Watchlist.ticker == ticker.upper()
        )
    )
    await session.commit()
    return WatchlistResponse(success=True, data=[])
