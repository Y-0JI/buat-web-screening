"""Service untuk data harga saham.

Business logic: validasi ticker, memanggil repository (satu pintu akses data),
mengembalikan data domain mentah (tuple df + is_simulated) untuk diproses
lebih lanjut oleh scoring/scheduler. Tidak membentuk response API.
"""

import pandas as pd

from app.services.base import BaseService, validate_ticker


class StockService(BaseService):
    async def get_price(
        self, symbol: str, fast_fail: bool = False
    ) -> tuple[pd.DataFrame | None, bool]:
        clean = validate_ticker(symbol)
        return await self._stock_repo.get_price(clean, fast_fail=fast_fail)

    async def get_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        clean = validate_ticker(symbol)
        return await self._stock_repo.get_history(clean, period=period)

    async def verify_ticker(self, candidate: str) -> bool:
        clean = validate_ticker(candidate)
        return await self._stock_repo.verify_ticker(clean)
