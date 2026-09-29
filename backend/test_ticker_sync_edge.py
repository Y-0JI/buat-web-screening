"""Test sync daftar ticker via IDX Edge PRO (tanpa jaringan).

Jalan: ./.venv/bin/python test_ticker_sync_edge.py
"""

import asyncio
import sys

import httpx

import app.data.ticker_sync as ts
from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider


async def _test_fetch_from_sources_paginates():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(dict(request.url.params).get("page", "1"))
        if page == 1:
            return httpx.Response(200, json={
                "total": 2, "page": 1, "per_page": 50, "total_pages": 2,
                "data": [{"code": "BBCA", "name": "Bank Central Asia Tbk."}],
            })
        return httpx.Response(200, json={
            "total": 2, "page": 2, "per_page": 50, "total_pages": 2,
            "data": [{"code": "BBRI", "name": "Bank Rakyat Indonesia Tbk."}],
        })

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    orig = ts._edge_provider
    ts._edge_provider = lambda: edge
    try:
        out = await ts._fetch_from_sources()
        codes = sorted(r["ticker"] for r in out)
        assert codes == ["BBCA", "BBRI"], out
        assert out[0]["company_name"]
    finally:
        ts._edge_provider = orig
        settings.idx_edge_api_key = old


def main():
    asyncio.run(_test_fetch_from_sources_paginates())
    print("OK: test_ticker_sync_edge lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
