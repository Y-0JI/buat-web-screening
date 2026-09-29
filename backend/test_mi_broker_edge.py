"""Test broker summary MI dari IDX Edge PRO (tanpa jaringan).

Jalan: ./.venv/bin/python test_mi_broker_edge.py
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.market_intelligence.repository import MarketIntelligenceRepository
from app.providers.idx_edge_provider import IdxEdgeProvider


async def _test_repo_broker_from_edge():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"stock_code": "BBCA", "brokers": [
            {"broker_code": "ZP", "broker_name": "Maybank", "bval": 100,
             "bvol": 10, "bfrq": 5, "sval": 0, "svol": 0, "nval": 100, "nvol": 10},
            {"broker_code": "AK", "broker_name": "UBS", "bval": 300,
             "bvol": 30, "bfrq": 8, "sval": 0, "svol": 0, "nval": 300, "nvol": 30},
        ]})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    repo = MarketIntelligenceRepository(edge_provider=edge)
    try:
        items = await repo.get_broker_summary("BBCA", limit=2)
        assert items[0]["broker_code"] == "AK", items  # urut value desc
        for f in ("broker_code", "broker_name", "volume", "value", "frequency"):
            assert f in items[0], (f, items[0])
    finally:
        settings.idx_edge_api_key = old


def main():
    asyncio.run(_test_repo_broker_from_edge())
    print("OK: test_mi_broker_edge lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
