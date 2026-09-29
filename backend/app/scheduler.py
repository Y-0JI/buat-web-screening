import asyncio
import time
import logging
from app.config import settings
from app.services import stock_service
from app.data.ticker_sync import get_listed_tickers
from app.scoring.funnel import calculate_score
from app.cache.service import cache_service

logger = logging.getLogger(__name__)

_screen_semaphore = asyncio.Semaphore(10)
_SCAN_TIMEOUT = 120

# ponytail: static ticker→name mapping, ganti dengan DB lookup jika perlu
_TICKER_NAMES: dict[str, str] | None = None


def _edge_provider():
    """Pabrik provider IDX Edge PRO — dapat diganti pada test."""
    from app.providers.idx_edge_provider import IdxEdgeProvider

    return IdxEdgeProvider()


async def _get_scan_candidates() -> list[str]:
    """Kandidat scan: pre-filter `screener/latest` saat IDX Edge aktif.

    Bila API gagal/key kosong → fallback whitelist lama hanya saat IDX Edge
    TIDAK aktif; saat aktif tapi gagal, kembalikan [] agar cache lama dipakai
    dan kuota tidak jebol karena scan seluruh emiten.
    """
    provider = _edge_provider()
    if provider.enabled:
        data = await provider.fetch_screener()
        if data and data.get("rows"):
            codes = [
                str(r.get("stock_code")).upper()
                for r in data["rows"]
                if r.get("stock_code")
            ]
            if codes:
                return codes
        logger.warning("Screener IDX Edge PRO gagal/kosong — pakai hasil cache terakhir")
        return []
    return await get_listed_tickers()


async def _persist_screening(mode: str, results: list[dict], ts: float) -> None:
    try:
        from app.database import async_session
        from app.database.models import ScreeningResult
        async with async_session() as session:
            await session.merge(ScreeningResult(mode=mode, results=results, updated_at=ts))
            await session.commit()
    except Exception as e:
        logger.warning("Persist screening %s gagal: %s", mode, e)


async def _load_screening(mode: str) -> dict | None:
    try:
        from app.database import async_session
        from app.database.models import ScreeningResult
        async with async_session() as session:
            row = await session.get(ScreeningResult, mode)
            if row is None:
                return None
            return {"results": row.results, "mode": mode, "ts": row.updated_at}
    except Exception as e:
        logger.warning("Baca screening %s dari DB gagal: %s", mode, e)
        return None


async def _get_screen(mode: str) -> dict | None:
    cached = await cache_service.get("screen", mode)
    if cached:
        return cached
    from_db = await _load_screening(mode)
    if from_db:
        await cache_service.set("screen", mode, from_db)
        return from_db
    return None


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
    s = await _get_screen(mode)
    if s:
        return s.get("results"), mode
    return None, None


async def get_screening_timestamp(mode: str = "BSJP") -> float | None:
    s = await _get_screen(mode)
    if s:
        return s.get("ts")
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

    tickers = await _get_scan_candidates()
    if not tickers:
        logger.error("Tidak ada kandidat scan (mode=%s) — cache tidak diubah", mode)
        return

    total = len(tickers)
    # ponytail: stagger 100ms antar ticker biar rate limiter gak kaget
    async def start_one(t: str, i: int):
        await asyncio.sleep(i * 0.1)
        return await scan_one(t)
    results_list = await asyncio.gather(*[start_one(t, i) for i, t in enumerate(tickers)])
    results = [r for r in results_list if r is not None]
    failed = total - len(results)

    if not results:
        logger.error(
            "Batch scan %s: %d/%d gagal — cache tidak diperbarui",
            mode, failed, total,
        )
        return

    results.sort(key=lambda x: x["score"], reverse=True)
    payload = {"results": results, "mode": mode, "ts": time.time()}
    await cache_service.set("screen", mode, payload)
    await _persist_screening(mode, results, payload["ts"])
    logger.info(
        "Batch scan selesai: %d berhasil, %d gagal (mode=%s)",
        len(results), failed, mode,
    )


async def run_daily_scan():
    logger.info("Memulai daily scan: BSJP dulu, lalu BPJS...")
    await run_batch_scan("BSJP")
    await run_batch_scan("BPJS")
    logger.info("Daily scan selesai untuk kedua mode")
