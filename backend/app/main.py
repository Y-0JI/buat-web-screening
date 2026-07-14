import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.research import router as research_router
from app.routers.screening import router as screening_router
from app.routers.vision import router as vision_router
from app.routers.auth import router as auth_router
from app.routers.watchlist import router as watchlist_router
from app.routers.history import router as history_router
from app.data.ticker_sync import fetch_and_store_tickers
from app.routers.chart import router as chart_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.database import engine
        from app.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as e:
        logger.warning("Database tidak tersedia: %s", e)

    # Bootstrap: kalau tabel listed_tickers kosong, seed dari VALID_TICKERS
    # supaya screening & /api/research tetap pakai daftar lengkap walaupun
    # sync eksternal (idx.co.id/sectors.app) gagal.
    try:
        from sqlalchemy import text
        from app.database import get_session
        from app.database.models import ListedTicker
        from app.data.idx_stocks import VALID_TICKERS
        from datetime import datetime

        async for session in get_session():
            count = (await session.execute(text("SELECT COUNT(*) FROM listed_tickers"))).scalar()
            if not count:
                logger.info("listed_tickers kosong — seeding dari VALID_TICKERS (%d ticker)", len(VALID_TICKERS))
                for t in VALID_TICKERS:
                    session.merge(ListedTicker(
                        ticker=t,
                        company_name=None,
                        sector=None,
                        is_active=1,
                        last_synced_at=datetime.utcnow(),
                    ))
                await session.commit()
                logger.info("Seeding selesai: %d ticker", len(VALID_TICKERS))
            else:
                logger.info("listed_tickers sudah terisi (%d ticker)", count)
            break
    except Exception as e:
        logger.warning("Bootstrap listed_tickers gagal: %s", e)

    if settings.scheduler_enabled:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            from app.scheduler import run_batch_scan

            global _scheduler
            _scheduler = AsyncIOScheduler()
            _scheduler.add_job(
                run_batch_scan,
                CronTrigger(day_of_week="mon-fri", hour=16, minute=30, timezone="Asia/Jakarta"),
                id="batch_scan",
                replace_existing=True,
            )
            _scheduler.add_job(
                fetch_and_store_tickers,
                CronTrigger(day_of_week="mon-fri", hour=16, minute=0, timezone="Asia/Jakarta"),
                id="ticker_sync",
                replace_existing=True,
            )
            _scheduler.start()
            logger.info("Scheduler aktif: ticker_sync 16:00, batch_scan 16:30 WIB (Sen-Jum)")
        except Exception as e:
            logger.warning("Scheduler tidak bisa diaktifkan: %s", e)
    yield
    if _scheduler:
        _scheduler.shutdown()


app = FastAPI(title="BSJP AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(screening_router)
app.include_router(vision_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(history_router)
app.include_router(chart_router)


@app.get("/")
async def root():
    return {"app": "BSJP AI", "version": "0.1.0"}
