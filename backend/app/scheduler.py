import asyncio
import time
import logging
from app.config import settings
from app.data.fetcher import fetch_stock_data, fetch_company_info
# from app.data.idx_stocks import VALID_TICKERS
from app.data.ticker_sync import get_listed_tickers
from app.scoring.funnel import calculate_score

logger = logging.getLogger(__name__)

_screen_cache: dict = {}
_cache_ts: float = 0
_CACHE_TTL = 7200
_screen_semaphore = asyncio.Semaphore(10)


def get_cached_screening() -> list[dict] | None:
    if not _screen_cache:
        return None
    if time.time() - _cache_ts > _CACHE_TTL:
        return None
    return _screen_cache.get("results")


async def run_batch_scan():
    logger.info("Memulai batch scan...")

    async def scan_one(ticker: str) -> dict | None:
        async with _screen_semaphore:
            try:
                df, is_simulated = await fetch_stock_data(ticker)
                if df is None or df.empty:
                    return None
                info = await fetch_company_info(ticker)
                report = calculate_score(df, ticker, is_simulated=is_simulated)
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
                }
            except Exception as e:
                logger.warning("Gagal scan %s: %s", ticker, e)
                return None

    tickers = await get_listed_tickers()
    results_list = await asyncio.gather(*[scan_one(t) for t in tickers])
    results = [r for r in results_list if r is not None]

    results.sort(key=lambda x: x["score"], reverse=True)
    global _screen_cache, _cache_ts
    _screen_cache = {"results": results}
    _cache_ts = time.time()
    logger.info("Batch scan selesai: %d saham", len(results))
