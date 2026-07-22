import asyncio
import time
import logging
from app.config import settings
from app.services import stock_service, company_profile_service
from app.data.idx_stocks import VALID_TICKERS
from app.data.ticker_sync import get_listed_tickers
from app.scoring.funnel import calculate_score
from app.cache.service import cache_service

logger = logging.getLogger(__name__)

_screen_semaphore = asyncio.Semaphore(10)
_SCAN_TIMEOUT = 120

# ponytail: static ticker→name mapping, ganti dengan DB lookup jika performa
# jadi masalah.
_TICKER_NAMES: dict[str, str] | None = None


async def _get_ticker_name(ticker: str) -> str:
    global _TICKER_NAMES
    if _TICKER_NAMES is None:
        _TICKER_NAMES = {}
        try:
            from app.database import get_session
            from app.database.models import ListedTicker
            from sqlalchemy import select
            async for session in get_session():
                rows = await session.execute(
                    select(ListedTicker.ticker, ListedTicker.company_name)
                )
                for t, n in rows:
                    if n:
                        _TICKER_NAMES[t.upper()] = n
                break
        except Exception:
            pass
    return _TICKER_NAMES.get(ticker.upper(), ticker)


async def get_cached_screening(mode: str = "BSJP") -> tuple[list[dict] | None, str | None]:
    cached = await cache_service.get("screen", mode)
    if cached:
        return cached.get("results"), mode
    return None, None


async def get_screening_timestamp(mode: str = "BSJP") -> float | None:
    cached = await cache_service.get("screen", mode)
    if cached:
        return cached.get("ts")
    return None


async def run_batch_scan(mode: str = "BSJP"):
    logger.info("Memulai batch scan (mode=%s)...", mode)

    async def scan_one(ticker: str) -> dict | None:
        async with _screen_semaphore:
            try:
                df, is_simulated = await asyncio.wait_for(
                    stock_service.get_price(ticker), timeout=_SCAN_TIMEOUT
                )
                if df is None or df.empty:
                    return None
                company_name = await _get_ticker_name(ticker)
                report = calculate_score(df, ticker, mode, is_simulated=is_simulated)
                report.company_name = company_name
                return {
                    "ticker": report.ticker,
                    "company_name": report.company_name,
                    "score": report.score,
                    "verdict": report.verdict.value,
                    "confidence": report.confidence,
                    "summary": report.summary,
                    "price": report.price,
                    "change_percent": report.change_percent,
                    "is_simulated": is_simulated,
                    "mode": mode,
                }
            except asyncio.TimeoutError:
                logger.warning("Timeout scan %s (%ss)", ticker, _SCAN_TIMEOUT)
                return None
            except Exception as e:
                logger.warning("Gagal scan %s: %s", ticker, e)
                return None

    tickers = await get_listed_tickers()
    results_list = await asyncio.gather(*[scan_one(t) for t in tickers])
    results = [r for r in results_list if r is not None]

    results.sort(key=lambda x: x["score"], reverse=True)
    await cache_service.set(
        "screen", mode, {"results": results, "mode": mode, "ts": time.time()}
    )
    logger.info("Batch scan selesai: %d saham (mode=%s)", len(results), mode)


async def run_daily_scan():
    """Jalankan scan untuk kedua mode (BSJP dan BPJS) secara paralel."""
    logger.info("Memulai daily scan untuk BSJP dan BPJS...")
    await asyncio.gather(
        run_batch_scan("BSJP"),
        run_batch_scan("BPJS"),
    )
    logger.info("Daily scan selesai untuk kedua mode")
