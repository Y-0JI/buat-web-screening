import asyncio
from app.data.fetcher import (
    fetch_stock_data,
    fetch_company_info,
    fetch_news,
    fetch_fundamentals,
)
from app.scoring.funnel import calculate_score


async def _get_stock_data_async(ticker: str, mode: str) -> dict:
    df, is_simulated = await fetch_stock_data(ticker, fast_fail=True)
    if df is None or df.empty or is_simulated:
        return {"error": f"Ticker {ticker} tidak ditemukan atau data tidak tersedia."}
    info = await fetch_company_info(ticker)
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
    return asyncio.run(_get_stock_data_async(ticker, mode))


async def _get_company_news_async(ticker: str, limit: int) -> dict:
    result = await fetch_news(ticker, limit=limit)
    return result


def get_company_news(ticker: str, limit: int = 5) -> dict:
    """Ambil berita terbaru untuk satu saham IDX dari Yahoo Finance.

    Args:
        ticker: Kode saham IDX, contoh "BBCA", tanpa akhiran .JK.
        limit: Jumlah berita yang diambil (default 5).

    Returns:
        Dict berisi items [{title, publisher, link, published, summary}]
        atau {"error": "..."} jika gagal.
    """
    return asyncio.run(_get_company_news_async(ticker, limit))


async def _get_fundamentals_async(ticker: str) -> dict:
    result = await fetch_fundamentals(ticker)
    return result


def get_fundamentals(ticker: str) -> dict:
    """Ambil data fundamental perusahaan dari Yahoo Finance.

    Args:
        ticker: Kode saham IDX, contoh "BBCA", tanpa akhiran .JK.

    Returns:
        Dict berisi market_cap, pe, pb, dividend_yield, beta, sector, industry,
        description, website, dll — atau {"error": "..."} jika gagal.
    """
    return asyncio.run(_get_fundamentals_async(ticker))
