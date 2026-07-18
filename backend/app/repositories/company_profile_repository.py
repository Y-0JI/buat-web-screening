"""Repository Company Profile — satu pintu akses data profil perusahaan.

Primary: IDX (`IdxProvider`, field lengkap). Fallback: Yahoo Finance
(`CompanyProfileProvider`) bila IDX gagal. Menentukan cache vs provider;
tidak ada business logic.
"""

from app.cache.memory_cache import MemoryCache
from app.providers import CompanyProfileProvider, IdxProvider

_PROFILE_TTL = 7 * 24 * 3600  # 7 hari (sesuai arah 16.4.5)


class CompanyProfileRepository:
    def __init__(
        self,
        provider: CompanyProfileProvider | None = None,
        idx_provider: IdxProvider | None = None,
        cache: MemoryCache | None = None,
    ):
        self._provider = provider or CompanyProfileProvider()
        self._idx_provider = idx_provider or IdxProvider()
        self._cache = cache or MemoryCache(default_ttl=_PROFILE_TTL)

    async def get_profile(self, symbol: str) -> dict:
        key = symbol.upper().replace(".JK", "")
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        data = await self._idx_provider.fetch_company_profile(symbol)
        if data.get("error") or not data.get("name"):
            data = await self._provider.fetch_profile(symbol)
        await self._cache.set(key, data)
        return data
