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
            _scheduler.start()
            logger.info("Scheduler batch scan aktif (16:30 WIB, Sen-Jum)")
        except Exception as e:
            logger.warning("Scheduler tidak bisa diaktifkan: %s", e)
    yield
    if _scheduler:
        _scheduler.shutdown()


app = FastAPI(title="BSJP AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(screening_router)
app.include_router(vision_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(history_router)


@app.get("/")
async def root():
    return {"app": "BSJP AI", "version": "0.1.0"}
