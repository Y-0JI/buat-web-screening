"""Technical cache — hasil scoring teknikal (16.4.5).

Scoring dihitung dari DataFrame harga; hasilnya di-cache singkat (TTL 1 menit,
lihat `cache.ttl.TECHNICAL_TTL`) per `(ticker, mode)` supaya request beruntun
tidak menghitung ulang. Semua akses lewat `cache_service` (terpusat).
"""

import pandas as pd

from app.cache.service import cache_service
from app.scoring.funnel import calculate_score
from app.schemas.stock import StockReport

_CATEGORY = "technical"


async def calculate_score_cached(
    df: pd.DataFrame,
    ticker: str,
    mode: str = "BSJP",
    is_simulated: bool = False,
) -> StockReport:
    key = f"{ticker.upper().replace('.JK', '')}:{mode}:{is_simulated}"
    cached = await cache_service.get(_CATEGORY, key)
    if cached is not None:
        # Salinan supaya mutasi pemanggil (mis. render/company_name) tidak
        # merusak objek ter-cache yang dipakai bersama.
        return cached.model_copy(deep=True)
    report = calculate_score(df, ticker, mode, is_simulated=is_simulated)
    await cache_service.set(_CATEGORY, key, report)
    return report.model_copy(deep=True)


async def clear() -> None:
    await cache_service.clear(_CATEGORY)
