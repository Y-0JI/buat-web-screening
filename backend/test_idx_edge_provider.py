"""Test unit IdxEdgeProvider (tanpa jaringan, pakai httpx.MockTransport).

Jalan: ./.venv/bin/python test_idx_edge_provider.py
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider


def _client(handler):
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://stock.arjum.com",
    )


def _with_key(key="test-key"):
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = key
    return old


def test_enabled_flag():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = ""
    assert IdxEdgeProvider().enabled is False
    settings.idx_edge_api_key = "abc"
    assert IdxEdgeProvider().enabled is True
    settings.idx_edge_api_key = old


async def _test_search():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json=[{"stock_code": "BBCA", "stock_name": "Bank Central Asia Tbk."}])

    p = IdxEdgeProvider(client=_client(handler))
    try:
        res = await p.search("BBCA")
        assert res == [{"stock_code": "BBCA", "stock_name": "Bank Central Asia Tbk."}], res
        assert seen["key"] == "test-key", seen
        assert "/api/search" in seen["url"] and "q=BBCA" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


async def _test_search_error_returns_empty():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "down"})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        assert await p.search("BBCA") == []
    finally:
        settings.idx_edge_api_key = old


async def _test_disabled_returns_none():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = ""
    try:
        p = IdxEdgeProvider()
        assert await p.search("BBCA") == []
        assert await p.health() is None
    finally:
        settings.idx_edge_api_key = old


async def _test_fetch_history():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={
            "stock_code": "BBCA", "frame": "daily",
            "rows": [{"date": "2026-09-29", "open": 6100, "high": 6200,
                      "low": 6050, "close": 6150, "volume": 150000000}],
        })

    p = IdxEdgeProvider(client=_client(handler))
    try:
        rows = await p.fetch_history("BBCA", limit=120)
        assert isinstance(rows, list) and len(rows) == 1, rows
        assert "/api/history/BBCA" in seen["url"] and "limit=120" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


async def _test_fetch_history_error():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        assert await p.fetch_history("BBCA") is None
    finally:
        settings.idx_edge_api_key = old


async def _test_market_cap():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"total": 963, "page": 1, "per_page": 50,
                                         "total_pages": 20, "data": [{"code": "BBCA"}]})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = await p.fetch_market_cap(page=2, per_page=50)
        assert data["total"] == 963 and data["data"][0]["code"] == "BBCA", data
        assert "/api/market-cap" in seen["url"] and "page=2" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


async def _test_screener():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"date": "2026-09-29",
                                         "rows": [{"stock_code": "ASHA"}]})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = await p.fetch_screener()
        assert data["rows"][0]["stock_code"] == "ASHA", data
    finally:
        settings.idx_edge_api_key = old


async def _test_broker_summary():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"stock_code": "BBCA", "brokers": [
            {"broker_code": "ZP", "broker_name": "Maybank", "bval": 202, "bvol": 10,
             "bfrq": 5, "sval": 0, "svol": 0, "nval": 202, "nvol": 10},
        ]})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = await p.fetch_broker_summary("BBCA", broker_limit=20)
        assert data["brokers"][0]["broker_code"] == "ZP", data
        assert "/api/broker-summary/BBCA" in seen["url"] and "broker_limit=20" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


def _test_fetch_history_clamps_limit():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"rows": []})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        asyncio.run(p.fetch_history("BBCA", limit=1000))
        assert "limit=500" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


def _test_ratelimit_header():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[],
            headers={"x-ratelimit-remaining": "777", "x-ratelimit-limit": "1000"},
        )

    p = IdxEdgeProvider(client=_client(handler))
    try:
        asyncio.run(p.search("BBCA"))
        assert p.last_ratelimit_remaining == 777, p.last_ratelimit_remaining
        assert p.quota_remaining() == 777, p.quota_remaining()
    finally:
        settings.idx_edge_api_key = old


def _test_ratelimit_min_tracking():
    old = _with_key()
    seq = iter(["900", "700", "800"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[], headers={"x-ratelimit-remaining": next(seq)},
        )

    p = IdxEdgeProvider(client=_client(handler))
    try:
        # Sebelum ada request: belum diketahui -> None (jangan menebak).
        assert p.quota_remaining() is None, p.quota_remaining()
        asyncio.run(p.search("A"))
        asyncio.run(p.search("B"))
        asyncio.run(p.search("C"))
        assert p.last_ratelimit_remaining == 800, p.last_ratelimit_remaining
        assert p.min_ratelimit_remaining == 700, p.min_ratelimit_remaining
        assert p.quota_remaining() == 700, p.quota_remaining()
    finally:
        settings.idx_edge_api_key = old


def _test_broker_accumulation():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={
            "code": "BBCA", "series": [{"broker_code": "AK", "points": []}],
            "top_buyers": [], "top_sellers": [],
        })

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = asyncio.run(p.fetch_broker_accumulation("BBCA"))
        assert data["series"][0]["broker_code"] == "AK", data
        assert "/api/broker-accumulation/BBCA" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


def _test_market_cap_all():
    old = _with_key()
    pages_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        pages_seen.append(page)
        if page == "1":
            return httpx.Response(200, json={
                "total": 2, "page": 1, "per_page": 50, "total_pages": 2,
                "data": [{"code": "AAA"}],
            })
        return httpx.Response(200, json={
            "total": 2, "page": 2, "per_page": 50, "total_pages": 2,
            "data": [{"code": "BBB"}],
        })

    p = IdxEdgeProvider(client=_client(handler))
    try:
        rows = asyncio.run(p.fetch_market_cap_all(max_pages=25))
        assert [r["code"] for r in rows] == ["AAA", "BBB"], rows
        assert pages_seen == ["1", "2"], pages_seen
    finally:
        settings.idx_edge_api_key = old


def _test_ratelimit_limit_header():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[],
            headers={"x-ratelimit-remaining": "19900", "x-ratelimit-limit": "20000"},
        )

    p = IdxEdgeProvider(client=_client(handler))
    try:
        assert p.ratelimit_limit is None, p.ratelimit_limit
        asyncio.run(p.search("BBCA"))
        assert p.ratelimit_limit == 20000, p.ratelimit_limit
        assert p.quota_remaining() == 19900, p.quota_remaining()
        p.reset_quota()
        assert p.ratelimit_limit is None, p.ratelimit_limit
    finally:
        settings.idx_edge_api_key = old


def _test_ratelimit_limit_bad_header_ignored():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[], headers={"x-ratelimit-limit": "bukan-angka"},
        )

    p = IdxEdgeProvider(client=_client(handler))
    try:
        asyncio.run(p.search("BBCA"))
        assert p.ratelimit_limit is None, p.ratelimit_limit
    finally:
        settings.idx_edge_api_key = old


def _test_calls_today_and_reset():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    p = IdxEdgeProvider(client=_client(handler))
    try:
        asyncio.run(p.search("A"))
        asyncio.run(p.search("B"))
        assert p.calls_today == 2, p.calls_today
        p.reset_quota()
        assert p.calls_today == 0, p.calls_today
    finally:
        settings.idx_edge_api_key = old


def main():
    test_enabled_flag()
    asyncio.run(_test_search())
    asyncio.run(_test_search_error_returns_empty())
    asyncio.run(_test_disabled_returns_none())
    asyncio.run(_test_fetch_history())
    asyncio.run(_test_fetch_history_error())
    asyncio.run(_test_market_cap())
    asyncio.run(_test_screener())
    asyncio.run(_test_broker_summary())
    _test_fetch_history_clamps_limit()
    _test_ratelimit_header()
    _test_ratelimit_min_tracking()
    _test_broker_accumulation()
    _test_market_cap_all()
    _test_calls_today_and_reset()
    print("OK: test_idx_edge_provider (lengkap) lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
