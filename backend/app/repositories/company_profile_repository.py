"""Repository Company Profile — satu pintu akses data profil perusahaan.

Menentukan ambil dari cache atau provider, lalu menyimpan ke cache. Tidak ada
business logic di sini.
"""

import pandas as pd

from app.cache.memory_cache import MemoryCache
from app.providers import CompanyProfileProvider

_PROFILE_TTL = 3600  # 1 jam


class CompanyProfileRepository:
    def __init__(self, provider: CompanyProfileProvider | None = None, cache: MemoryCache | None = None):
        self._provider = provider or CompanyProfileProvider()
        self._cache = cache or MemoryCache(default_ttl=_PROFILE_TTL)

    async def get_profile(self, symbol: str) -> dict:
        key = symbol.upper().replace(".JK", "")
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        data = await self._provider.fetch_profile(symbol)
        await self._cache.set(key, data)
        return data
