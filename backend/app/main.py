"""Entrypoint backend chat-first.

Hanya menyajikan: chat (agen streaming), katalog model, threads, dan health.
Layer provider/service/repository tetap dipakai oleh tool agen. Router fitur
lama tidak lagi dipasang.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging import configure_logging, LoggingMiddleware
from app.utils.error_handler import register_exception_handlers
from app.routers.chat import router as chat_router
from app.routers.models import router as models_router
from app.routers.threads import router as threads_router

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.database import engine
        from app.database.models import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as e:  # noqa: BLE001
        logger.warning("Database tidak tersedia: %s", e)
    yield


app = FastAPI(title="IDX Copilot", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
register_exception_handlers(app)

app.include_router(chat_router)
app.include_router(models_router)
app.include_router(threads_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"app": "IDX Copilot", "version": "0.2.0"}
