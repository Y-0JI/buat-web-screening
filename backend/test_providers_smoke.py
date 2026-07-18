"""Smoke test Data Layer (tanpa framework — jalan via `python3 test_providers_smoke.py`).

Cek:
1. Semua provider & repository terimport tanpa error.
2. IdxProvider tetap aman saat jaringan gagal: tidak raise, kembalikan dict
   `error` (profile/fundamental) atau (None, False) (price).
"""

import asyncio
import sys

import app.providers as providers
from app.providers.idx_provider import IdxProvider, _fetch_json


def test_imports():
    for name in (
        "StockPriceProvider",
        "CompanyProfileProvider",
        "NewsProvider",
        "FundamentalsProvider",
        "IdxProvider",
    ):
        assert hasattr(providers, name), f"provider {name} tidak ter-export"


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
    asyncio.run(_test_idx_fallback())
    print("OK: semua smoke test lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
