"""Service untuk data fundamental.

Business logic: validasi ticker, ambil dari repository, lalu transformasi ke
domain object. Router yang membungkus hasil ke `APIResponse`.
"""

from typing import Any, Dict

from app.repositories import fundamentals_repository
from app.services.base import validate_ticker
from app.utils.errors import DataNotFoundError


class FundamentalsService:
    def __init__(self, fundamentals_repo=fundamentals_repository):
        self._fundamentals_repo = fundamentals_repo

    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        clean = validate_ticker(symbol)
        result = await self._fundamentals_repo.get_fundamentals(clean)
        if result.get("error"):
            raise DataNotFoundError(result["error"])
        return result
