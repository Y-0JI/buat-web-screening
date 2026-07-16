import asyncio
import time
import logging
from app.config import settings
from app.data.fetcher import fetch_stock_data, fetch_company_info
# from app.data.idx_stocks import VALID_TICKERS
from app.data.ticker_sync import get_listed_tickers
from app.scoring.funnel import calculate_score

logger = logging.getLogger(__name__)

_screen_cache: dict[str, dict] = {}
_cache_ts: dict[str, float] = {}
_CACHE_TTL = 7200
_screen_semaphore = asyncio.Semaphore(10)
_screen_cache_lock = asyncio.Lock()


async def get_cached_screening() -> tuple[list[dict] | None, str | None]:
    async with _screen_cache_lock:
        for mode in ["BSJP", "BPJS"]:
            cached = _screen_cache.get(mode)
            ts = _cache_ts.get(mode, 0)
            if cached and time.time() - ts < _CACHE_TTL:
                return cached.get("results"), mode
        return None, None


def get_screening_timestamp() -> float | None:
    async def _get():
        async with _screen_cache_lock:
            for mode in ["BSJP", "BPJS"]:
                ts = _cache_ts.get(mode, 0)
                if ts > 0 and time.time() - ts < _CACHE_TTL:
                    return ts
            return None
    import asyncio as _aio
    loop = _aio.get_event_loop()
    if loop.is_running():
        return None
    return loop.run_until_complete(_get())


async def run_batch_scan(mode: str = "BSJP"):
    logger.info("Memulai batch scan (mode=%s)...", mode)

    async def scan_one(ticker: str) -> dict | None:
        async with _screen_semaphore:
            try:
                df, is_simulated = await fetch_stock_data(ticker)
                if df is None or df.empty:
                    return None
                info = await fetch_company_info(ticker)
                report = calculate_score(df, ticker, mode, is_simulated=is_simulated)
                report.company_name = info.get("name", ticker)
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
            except Exception as e:
                logger.warning("Gagal scan %s: %s", ticker, e)
                return None

    tickers = await get_listed_tickers()
    results_list = await asyncio.gather(*[scan_one(t) for t in tickers])
    results = [r for r in results_list if r is not None]

    results.sort(key=lambda x: x["score"], reverse=True)
    global _screen_cache, _cache_ts
    async with _screen_cache_lock:
        _screen_cache[mode] = {"results": results, "mode": mode}
        _cache_ts[mode] = time.time()
    logger.info("Batch scan selesai: %d saham (mode=%s)", len(results), mode)


async def run_daily_scan():
    """Jalankan scan untuk kedua mode (BSJP dan BPJS) secara paralel."""
    logger.info("Memulai daily scan untuk BSJP dan BPJS...")
    await asyncio.gather(
        run_batch_scan("BSJP"),
        run_batch_scan("BPJS"),
    )
    logger.info("Daily scan selesai untuk kedua mode")
