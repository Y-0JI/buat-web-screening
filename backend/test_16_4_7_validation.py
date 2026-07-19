"""Smoke test 16.4.7 — Testing & Validation Data Intelligence 16.4.x.

Tanpa framework (jalan via `python3 test_16_4_7_validation.py`). Menutup 6
sub-bagian roadmap:
1. API Test            — endpoint HTTP via FastAPI TestClient (cache refresh) +
                         wiring route research/stock.
2. Cache Test          — MemoryCache TTL/clear(prefix) + CacheService namespace
                         & TTL per-kategori.
3. Error Handling Test — cache aman saat key hilang; entry kadaluarsa → None;
                         type refresh tak dikenal tidak error.
4. Frontend Rendering  — dijalankan terpisah (`npx tsc --noEmit && npm run build`),
                         bukan di file ini. Lihat catatan main().
5. Performance Test    — technical_cache: panggilan kedua pakai cache (scoring
                         tidak dihitung ulang).
6. Await Coverage Test — jalur async inti tidak meninggalkan coroutine tak
                         di-await (RuntimeWarning dijadikan error).
"""

import asyncio
import sys
import time
import warnings

import pandas as pd
from fastapi.testclient import TestClient

from app.cache.memory_cache import MemoryCache
from app.cache.service import CacheService, cache_service
from app.cache.ttl import TTL_BY_CATEGORY, TECHNICAL_TTL
from app.main import app
import app.repositories.technical_cache as technical_cache
from app.schemas.stock import StockReport, Verdict


# ---------------------------------------------------------------- 1. API Test
def test_api_cache_refresh():
    client = TestClient(app)

    r = client.post("/api/cache/refresh")
    assert r.status_code == 200, r.status_code
    assert r.json() == {"success": True, "cleared": "all"}, r.json()

    r = client.post("/api/cache/refresh", params={"type": "news"})
    assert r.json() == {"success": True, "cleared": "news"}, r.json()

    r = client.post("/api/cache/refresh", params={"type": "bogus"})
    body = r.json()
    assert body["success"] is False and "valid_types" in body, body


def test_api_routes_registered():
    paths = {(r.path, tuple(sorted(getattr(r, "methods", []) or [])))
             for r in app.routes}
    flat = {p for p, _ in paths}
    for p in ("/api/research", "/api/stock/{ticker}/fundamentals",
              "/api/stock/{ticker}/news", "/api/cache/refresh"):
        assert p in flat, f"route {p} tidak terdaftar: {sorted(flat)}"
    assert any(p == "/api/research" and "POST" in m for p, m in paths), paths


# -------------------------------------------------------------- 2. Cache Test
async def _test_memory_cache_ttl():
    c = MemoryCache()
    await c.set("k", "v", ttl=60)
    assert await c.get("k") == "v"

    await c.set("gone", "x", ttl=0)  # kedaluwarsa seketika
    assert await c.get("gone") is None, "entry ttl=0 harus kadaluarsa"

    await c.set("a:1", 1, ttl=60)
    await c.set("a:2", 2, ttl=60)
    await c.set("b:1", 3, ttl=60)
    await c.clear(prefix="a:")
    assert await c.get("a:1") is None and await c.get("a:2") is None
    assert await c.get("b:1") == 3, "clear(prefix) tak boleh sentuh prefix lain"


async def _test_cache_service_namespace():
    svc = CacheService()
    await svc.set("profile", "BBCA", {"name": "BCA"})
    await svc.set("news", "BBCA", [{"h": 1}])
    assert await svc.get("profile", "BBCA") == {"name": "BCA"}

    await svc.clear("profile")
    assert await svc.get("profile", "BBCA") is None, "clear kategori gagal"
    assert await svc.get("news", "BBCA") == [{"h": 1}], "kategori lain kena imbas"

    await svc.clear()
    assert await svc.get("news", "BBCA") is None, "clear global gagal"


def test_ttl_categories():
    for cat in ("profile", "fundamental", "news", "price", "verify",
                "technical", "screener", "screen"):
        assert cat in TTL_BY_CATEGORY, f"kategori {cat} hilang dari TTL"
    assert TTL_BY_CATEGORY["technical"] == TECHNICAL_TTL == 60


# ------------------------------------------------------ 3. Error Handling Test
async def _test_cache_safe_on_miss():
    svc = CacheService()
    assert await svc.get("news", "TIDAK-ADA") is None, "miss harus None, bukan raise"
    await svc.delete("news", "TIDAK-ADA")  # delete key hilang tidak boleh raise


# --------------------------------------------------------- 5. Performance Test
def _fake_report(ticker: str) -> StockReport:
    return StockReport(ticker=ticker, score=50, verdict=Verdict.HOLD,
                       confidence=50, summary="fake")


async def _test_technical_cache_reuse():
    await cache_service.clear("technical")
    calls = {"n": 0}

    def _counting_score(df, ticker, mode, is_simulated=False):
        calls["n"] += 1
        return _fake_report(ticker)

    orig = technical_cache.calculate_score
    technical_cache.calculate_score = _counting_score
    try:
        df = pd.DataFrame({"close": [1, 2, 3]})
        r1 = await technical_cache.calculate_score_cached(df, "BBCA", "BSJP")
        r2 = await technical_cache.calculate_score_cached(df, "BBCA", "BSJP")
        assert calls["n"] == 1, f"scoring dihitung ulang: {calls['n']}x"
        assert r1.ticker == r2.ticker == "BBCA"
        assert r1 is not r2, "harus deep-copy (bukan objek cache yang sama)"
    finally:
        technical_cache.calculate_score = orig
        await cache_service.clear("technical")


# ------------------------------------------------------ 6. Await Coverage Test
async def _await_flow():
    svc = CacheService()
    await svc.set("price", "BBCA", 123, ttl=60)
    await svc.get("price", "BBCA")
    await svc.clear()
    c = MemoryCache()
    await c.set("x", 1, ttl=60)
    await c.invalidate()


def test_await_coverage():
    """Jalur async inti tidak meninggalkan coroutine tak di-await."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        asyncio.run(_await_flow())


def main():
    test_api_cache_refresh()
    test_api_routes_registered()
    asyncio.run(_test_memory_cache_ttl())
    asyncio.run(_test_cache_service_namespace())
    test_ttl_categories()
    asyncio.run(_test_cache_safe_on_miss())
    asyncio.run(_test_technical_cache_reuse())
    test_await_coverage()
    print("OK: semua smoke test 16.4.7 lolos "
          "(Frontend Rendering diverifikasi terpisah: "
          "cd frontend && npx tsc --noEmit && npm run build)")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
