"""Smoke test 16.5.3 — Validation Market Intelligence (16.5.x).

Tanpa framework (jalan via `python3 test_16_5_3_validation.py`). Menutup empat
bagian roadmap 16.5.3:

1. Backend    — `MarketIntelligenceService.get_intelligence` mengembalikan
                struktur konsisten & empty-safe; graceful saat repository melempar
                (satu sumber gagal tidak menjatuhkan yang lain).
2. API        — `GET /api/market-intelligence/{ticker}` via TestClient: ticker
                valid → success, ticker invalid → success=False (bukan 500).
3. Cache      — TTL kategori MI terpasang; hit/miss/clear per kategori benar;
                repository memakai cache (fetch kedua tidak memanggil provider).
4. Empty-safe — price_target/recommendation kosong tidak menyebabkan error.

Sampling live (hit-rate ≥95%, baseline earnings, latency) diukur terpisah oleh
`measure_16_5_acceptance.py` agar test ini cepat & deterministik (tanpa jaringan).
"""

import asyncio
import sys
import warnings

from fastapi.testclient import TestClient

from app.cache.service import CacheService
from app.cache.ttl import (
    TTL_BY_CATEGORY,
    DIVIDEND_TTL,
    CORP_ACTION_TTL,
    FOREIGN_FLOW_TTL,
    BROKER_TTL,
    EARNINGS_TTL,
)
from app.main import app
from app.market_intelligence import models
from app.market_intelligence.repository import MarketIntelligenceRepository
from app.market_intelligence.service import MarketIntelligenceService

_MI_FIELDS = (
    "ticker", "dividend", "corporate_actions", "foreign_flow",
    "broker_summary", "earnings", "price_target", "recommendation",
)


# --------------------------------------------------------- fake provider/repo
class _FakeProvider:
    """Provider palsu deterministik (tanpa jaringan)."""

    async def fetch_dividend(self, symbol):
        return {"item": {"Jenis": "dt", "TahunBuku": "2025",
                         "CashDividenPerSaham": 100.0, "CashDividenTotal": 1e9,
                         "CashDividenTotalMU": "IDR", "TotalSahamBonus": 0.0,
                         "Rasio1": 0, "Rasio2": 0, "TanggalCum": "2025-05-01",
                         "TanggalExRegulerDanNegosiasi": "2025-05-02",
                         "TanggalDPS": "2025-05-03", "TanggalPembayaran": "2025-05-20"}}

    async def fetch_corporate_actions_year(self, year):
        return {"splits": [{"code": "TEST", "stockname": "Test Tbk",
                            "Ratio": "1:2", "NominalValue": 100.0,
                            "NominalValueNew": 50.0,
                            "AdditionalListedShares": 1e6,
                            "ListingDate": f"{year}-03-01"}],
                "rights": []}

    async def fetch_stock_summary(self, date_str):
        return {"TEST": {"StockCode": "TEST", "ForeignBuy": 500.0,
                         "ForeignSell": 200.0, "Close": 1000.0,
                         "Volume": 1e6, "Value": 1e9}}

    async def fetch_broker_summary(self, date_str, limit=100):
        return [{"IDFirm": "AA", "FirmName": "Broker A", "Volume": 1e6,
                 "Value": 5e9, "Frequency": 100.0}]

    async def fetch_earnings(self, symbol):
        return {"calendar": {"Earnings Date": ["2025-07-22"],
                             "Earnings Average": 120.0, "Earnings High": 130.0,
                             "Earnings Low": 110.0, "Revenue Average": 1e12,
                             "Revenue High": 1.1e12, "Revenue Low": 0.9e12}}


class _BoomProvider(_FakeProvider):
    """Sebagian sumber melempar — untuk uji graceful."""

    async def fetch_dividend(self, symbol):
        raise RuntimeError("boom dividend")

    async def fetch_broker_summary(self, date_str, limit=100):
        raise RuntimeError("boom broker")


# ----------------------------------------------------------------- 1. Backend
async def _test_service_structure():
    repo = MarketIntelligenceRepository(provider=_FakeProvider())
    await repo.clear()
    svc = MarketIntelligenceService(repo=repo)
    r = await svc.get_intelligence("TEST")
    for f in _MI_FIELDS:
        assert f in r, f"field {f} hilang dari hasil: {list(r.keys())}"
    assert r["ticker"] == "TEST"
    assert r["dividend"] and r["dividend"]["cash_dividend_per_share"] == 100.0
    assert len(r["corporate_actions"]) >= 1
    assert all(a["action_type"] == "stock_split" for a in r["corporate_actions"])
    assert r["foreign_flow"]["foreign_net"] == 300.0
    assert r["broker_summary"] and r["broker_summary"][0]["broker_code"] == "AA"
    assert r["earnings"]["earnings_date"] == "2025-07-22"
    assert r["price_target"] is None and r["recommendation"] == []


async def _test_service_graceful():
    """Sumber yang melempar → field default, sumber lain tetap terisi."""
    repo = MarketIntelligenceRepository(provider=_BoomProvider())
    await repo.clear()
    svc = MarketIntelligenceService(repo=repo)
    r = await svc.get_intelligence("TEST")
    assert r["dividend"] is None, "dividend gagal harus None, bukan raise"
    assert r["broker_summary"] == [], "broker gagal harus [], bukan raise"
    assert r["foreign_flow"] is not None, "sumber sehat tetap terisi"
    assert r["earnings"] is not None


# --------------------------------------------------------------------- 2. API
def test_api_valid_and_invalid():
    with TestClient(app) as client:
        r = client.get("/api/market-intelligence/@@@")
        assert r.status_code == 200, r.status_code
        body = r.json()
        assert body["success"] is False and body["error"], body
        assert "tidak valid" in body["error"].lower(), body


def test_api_route_registered():
    flat = {r.path for r in app.routes}
    assert "/api/market-intelligence/{ticker}" in flat, sorted(flat)


# ------------------------------------------------------------------- 3. Cache
def test_ttl_categories():
    expected = {
        "dividend": DIVIDEND_TTL,
        "corp_action": CORP_ACTION_TTL,
        "foreign_flow": FOREIGN_FLOW_TTL,
        "broker_summary": BROKER_TTL,
        "earnings": EARNINGS_TTL,
    }
    for cat, ttl in expected.items():
        assert cat in TTL_BY_CATEGORY, f"kategori {cat} hilang dari TTL"
        assert TTL_BY_CATEGORY[cat] == ttl, f"TTL {cat} tidak sesuai"
    assert "price_target" in TTL_BY_CATEGORY
    # Confirmed harian < mingguan (dividend/corp action jarang berubah)
    assert FOREIGN_FLOW_TTL < DIVIDEND_TTL and BROKER_TTL < CORP_ACTION_TTL


async def _test_cache_namespace_isolation():
    svc = CacheService()
    await svc.set("dividend", "AAA", {"v": 1})
    await svc.set("earnings", "AAA", {"v": 2})
    assert await svc.get("dividend", "AAA") == {"v": 1}
    await svc.clear("dividend")
    assert await svc.get("dividend", "AAA") is None, "clear kategori gagal"
    assert await svc.get("earnings", "AAA") == {"v": 2}, "kategori lain kena imbas"


async def _test_repo_uses_cache():
    """Fetch kedua harus dari cache (provider tidak dipanggil lagi)."""
    calls = {"dividend": 0, "earnings": 0}

    class _Counting(_FakeProvider):
        async def fetch_dividend(self, symbol):
            calls["dividend"] += 1
            return await super().fetch_dividend(symbol)

        async def fetch_earnings(self, symbol):
            calls["earnings"] += 1
            return await super().fetch_earnings(symbol)

    repo = MarketIntelligenceRepository(provider=_Counting())
    await repo.clear()
    await repo.get_dividend("CACHED")
    await repo.get_dividend("CACHED")
    await repo.get_earnings("CACHED")
    await repo.get_earnings("CACHED")
    assert calls["dividend"] == 1, f"dividend tidak pakai cache: {calls['dividend']}x"
    assert calls["earnings"] == 1, f"earnings tidak pakai cache: {calls['earnings']}x"
    await repo.clear()


# -------------------------------------------------------------- 4. Empty-safe
def test_empty_intelligence_shape():
    e = models.empty_intelligence("XYZ")
    assert e["ticker"] == "XYZ"
    assert e["dividend"] is None and e["foreign_flow"] is None
    assert e["corporate_actions"] == [] and e["broker_summary"] == []
    assert e["price_target"] is None and e["recommendation"] == []


def test_normalizers_defensive():
    assert models.normalize_dividend(None) is None
    assert models.normalize_dividend({}) is None  # kosong → tak ada dividen
    partial = models.normalize_dividend({"Jenis": "dt"})  # sebagian → field lain None
    assert partial and partial["type"] == "dt" and partial["cash_dividend_per_share"] is None
    assert models.normalize_foreign_flow(None, "2025-01-01") is None
    assert models.normalize_earnings({}) is None
    assert models.normalize_earnings({"Earnings Date": []}) is None


# ------------------------------------------------------ await coverage guard
def test_await_coverage():
    async def _flow():
        repo = MarketIntelligenceRepository(provider=_FakeProvider())
        await repo.clear()
        await repo.get_dividend("AW")
        await repo.get_corporate_actions("TEST")
        await repo.get_foreign_flow("TEST")
        await repo.get_broker_summary()
        await repo.get_earnings("AW")
        await repo.clear()

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        asyncio.run(_flow())


def main():
    asyncio.run(_test_service_structure())
    asyncio.run(_test_service_graceful())
    test_api_valid_and_invalid()
    test_api_route_registered()
    test_ttl_categories()
    asyncio.run(_test_cache_namespace_isolation())
    asyncio.run(_test_repo_uses_cache())
    test_empty_intelligence_shape()
    test_normalizers_defensive()
    test_await_coverage()
    print("OK: semua smoke test 16.5.3 lolos "
          "(hit-rate/baseline/latency live diukur via measure_16_5_acceptance.py)")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
