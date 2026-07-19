"""Service untuk Company Profile.

Business logic: validasi ticker, ambil dari repository, kembalikan dict domain
mentah (name, sector, market_cap) untuk dipakai orchestrator / scoring.
"""

from typing import Any, Dict

from app.repositories import company_profile_repository
from app.services.base import validate_ticker


class CompanyProfileService:
    def __init__(self, company_repo=company_profile_repository):
        self._company_repo = company_repo

    async def get_profile(self, symbol: str) -> Dict[str, Any]:
        clean = validate_ticker(symbol)
        return await self._company_repo.get_profile(clean)
