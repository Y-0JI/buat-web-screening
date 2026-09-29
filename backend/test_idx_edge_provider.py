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


def main():
    test_enabled_flag()
    asyncio.run(_test_search())
    asyncio.run(_test_search_error_returns_empty())
    asyncio.run(_test_disabled_returns_none())
    print("OK: test_idx_edge_provider (bagian 1) lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
