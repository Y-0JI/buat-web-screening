"""Test pre-filter kandidat screening via IDX Edge PRO (tanpa jaringan).

Jalan: ./.venv/bin/python test_scheduler_candidates.py
"""

import asyncio
import sys

import httpx

import app.scheduler as sched
from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider


async def _test_candidates_from_screener():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rows": [
            {"stock_code": "ASHA"}, {"stock_code": "RAJA"},
        ]})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    orig = sched._edge_provider
    sched._edge_provider = lambda: edge
    try:
        codes = await sched._get_scan_candidates()
        assert codes == ["ASHA", "RAJA"], codes
    finally:
        sched._edge_provider = orig
        settings.idx_edge_api_key = old


async def _test_candidates_empty_when_api_fails():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    orig = sched._edge_provider
    sched._edge_provider = lambda: edge
    try:
        assert await sched._get_scan_candidates() == []
    finally:
        sched._edge_provider = orig
        settings.idx_edge_api_key = old


def main():
    asyncio.run(_test_candidates_from_screener())
    asyncio.run(_test_candidates_empty_when_api_fails())
    print("OK: test_scheduler_candidates lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
