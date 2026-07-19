"""Repository Company Profile — satu pintu akses data profil perusahaan.

Primary: IDX (`IdxProvider`, field lengkap). Fallback: Yahoo Finance
(`CompanyProfileProvider`) bila IDX gagal. Menentukan cache vs provider;
tidak ada business logic.
"""

from app.cache.service import cache_service
from app.providers import CompanyProfileProvider, IdxProvider

_CATEGORY = "profile"


class CompanyProfileRepository:
    def __init__(
        self,
        provider: CompanyProfileProvider | None = None,
        idx_provider: IdxProvider | None = None,
    ):
        self._provider = provider or CompanyProfileProvider()
        self._idx_provider = idx_provider or IdxProvider()

    async def get_profile(self, symbol: str) -> dict:
        key = symbol.upper().replace(".JK", "")
        cached = await cache_service.get(_CATEGORY, key)
        if cached is not None:
            return cached
        data = await self._idx_provider.fetch_company_profile(symbol)
        if data.get("error") or not data.get("name"):
            data = await self._provider.fetch_profile(symbol)
        await cache_service.set(_CATEGORY, key, data)
        return data

    async def clear(self) -> None:
        await cache_service.clear(_CATEGORY)
