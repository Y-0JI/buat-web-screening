"""Service untuk Company Profile.

Business logic: validasi ticker, ambil dari repository, kembalikan dict domain
mentah (name, sector, market_cap) untuk dipakai orchestrator / scoring.
"""

from typing import Any, Dict

from app.services.base import BaseService, validate_ticker


class CompanyProfileService(BaseService):
    async def get_profile(self, symbol: str) -> Dict[str, Any]:
        clean = validate_ticker(symbol)
        return await self._company_repo.get_profile(clean)
