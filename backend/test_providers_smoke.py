"""Smoke test Data Layer (tanpa framework — jalan via `python3 test_providers_smoke.py`).

Cek:
1. Semua provider & repository terimport tanpa error (termasuk wiring IDX).
2. Repository profile/fundamental/price sudah terhubung ke IdxProvider.
3. IdxProvider tetap aman saat jaringan gagal: tidak raise, kembalikan dict
   `error` (profile/fundamental) atau (None, False) (price).
4. RssProvider terdaftar.
"""

import asyncio
import sys

import app.providers as providers
import app.repositories as repositories
from app.providers.idx_provider import IdxProvider, _fetch_json
from app.providers.rss_provider import RssProvider


def test_imports():
    for name in (
        "StockPriceProvider",
        "CompanyProfileProvider",
        "NewsProvider",
        "FundamentalsProvider",
        "IdxProvider",
        "RssProvider",
    ):
        assert hasattr(providers, name), f"provider {name} tidak ter-export"


def test_repository_wiring():
    assert isinstance(repositories.company_profile_repository._idx_provider, IdxProvider)
    assert isinstance(repositories.fundamentals_repository._idx_provider, IdxProvider)
    assert isinstance(repositories.stock_price_repository._idx_provider, IdxProvider)


async def _test_idx_fallback():
    provider = IdxProvider()

    async def _boom(*a, **k):
        raise RuntimeError("simulasi offline")

    orig = providers.idx_provider._fetch_json
    providers.idx_provider._fetch_json = _boom
    try:
        prof = await provider.fetch_company_profile("BBCA")
        assert isinstance(prof, dict) and "name" in prof, prof
        assert "error" in prof, "profile harus catat error saat offline"

        fund = await provider.fetch_fundamentals("BBCA")
        assert isinstance(fund, dict) and "error" in fund, fund

        df, sim = await provider.fetch_daily_price("BBCA")
        assert df is None and sim is False, (df, sim)
    finally:
        providers.idx_provider._fetch_json = orig


def main():
    test_imports()
    test_repository_wiring()
    asyncio.run(_test_idx_fallback())
    print("OK: semua smoke test lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
