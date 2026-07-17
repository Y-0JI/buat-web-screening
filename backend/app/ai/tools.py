import asyncio
from concurrent.futures import Future
from app.services import (
    stock_service,
    company_profile_service,
    news_service,
    fundamentals_service,
)
from app.utils.errors import AppError
from app.scoring.funnel import calculate_score

# Shared event loop running in main thread — all async work goes here
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop


def _submit_async(coro) -> dict | None:
    """Submit an async coroutine to the main event loop and wait for result."""
    if _main_loop is None or _main_loop.is_closed():
        return None
    future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
    return future.result(timeout=30)


async def _get_stock_data_async(ticker: str, mode: str) -> dict:
    df, is_simulated = await stock_service.get_price(ticker, fast_fail=True)
    if df is None or df.empty or is_simulated:
        return {"error": f"Ticker {ticker} tidak ditemukan atau data tidak tersedia."}
    info = await company_profile_service.get_profile(ticker)
    report = calculate_score(df, ticker, mode, is_simulated=is_simulated)
    return {
        "ticker": ticker,
        "company_name": info.get("name", ticker),
        "price": report.price,
        "change_percent": report.change_percent,
        "score": report.score,
        "verdict": report.verdict.value,
        "confidence": report.confidence,
        "indicators": report.indicators.model_dump(),
    }


def get_stock_data(ticker: str, mode: str = "BSJP") -> dict:
    """Ambil data teknikal & skor funnel untuk satu kode saham IDX.

    Args:
        ticker: Kode saham IDX, 2-5 huruf, contoh "BBCA", "CDIA", tanpa akhiran .JK.
        mode: Profil trading, "BSJP" atau "BPJS".

    Returns:
        Dict berisi harga, skor, verdict, breakdown indikator — atau {"error": "..."}
        kalau ticker tidak ditemukan/tidak valid.
    """
    return _submit_async(_get_stock_data_async(ticker, mode)) or {"error": "Event loop not available"}


def get_company_news(ticker: str, limit: int = 5) -> dict:
    """Ambil berita terbaru untuk satu saham IDX dari Yahoo Finance.

    Args:
        ticker: Kode saham IDX, contoh "BBCA", tanpa akhiran .JK.
        limit: Jumlah berita yang diambil (default 5).

    Returns:
        Dict berisi items [{title, publisher, link, published, summary}]
        atau {"error": "..."} jika gagal.
    """

    async def _run() -> dict:
        try:
            data = await news_service.get_news(ticker, limit=limit)
            return {"items": [item.model_dump() for item in data.items]}
        except AppError as e:
            return {"error": e.message}

    return _submit_async(_run()) or {"error": "Event loop not available"}


def get_fundamentals(ticker: str) -> dict:
    """Ambil data fundamental perusahaan dari Yahoo Finance.

    Args:
        ticker: Kode saham IDX, contoh "BBCA", tanpa akhiran .JK.

    Returns:
        Dict berisi market_cap, pe, pb, dividend_yield, beta, sector, industry,
        description, website, dll — atau {"error": "..."} jika gagal.
    """

    async def _run() -> dict:
        try:
            return await fundamentals_service.get_fundamentals(ticker)
        except AppError as e:
            return {"error": e.message}

    return _submit_async(_run()) or {"error": "Event loop not available"}
