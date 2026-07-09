import time
import logging
from app.config import settings
from app.data.fetcher import MOCK_DATA, fetch_stock_data, fetch_company_info
from app.scoring.funnel import calculate_score

logger = logging.getLogger(__name__)

_screen_cache: dict = {}
_cache_ts: float = 0
_CACHE_TTL = 7200


def get_cached_screening() -> list[dict] | None:
    if not _screen_cache:
        return None
    if time.time() - _cache_ts > _CACHE_TTL:
        return None
    return _screen_cache.get("results")


def run_batch_scan():
    logger.info("Memulai batch scan...")
    results = []
    for ticker in MOCK_DATA:
        try:
            df = fetch_stock_data(ticker)
            if df is None or df.empty:
                continue
            info = fetch_company_info(ticker)
            report = calculate_score(df, ticker)
            report.company_name = info.get("name", ticker)
            results.append({
                "ticker": report.ticker,
                "company_name": report.company_name,
                "score": report.score,
                "verdict": report.verdict.value,
                "confidence": report.confidence,
                "summary": report.summary,
                "price": report.price,
                "change_percent": report.change_percent,
            })
        except Exception as e:
            logger.warning("Gagal scan %s: %s", ticker, e)

    results.sort(key=lambda x: x["score"], reverse=True)
    global _screen_cache, _cache_ts
    _screen_cache = {"results": results}
    _cache_ts = time.time()
    logger.info("Batch scan selesai: %d saham", len(results))
