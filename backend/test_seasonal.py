"""Test router seasonality (tanpa jaringan asli, data contoh IDX Edge).

Jalan: ./.venv/bin/python test_seasonal.py
"""

import asyncio
import sys

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.routers import seasonal as seasonal_mod
from app.routers.seasonal import seasonal_payload, router as seasonal_router

SAMPLE = {
    "stock_code": "BBCA",
    "years": ["2024", "2025", "2026"],
    "monthly_returns": {
        "Jan": {"2024": 1.33, "2025": -4.55, "2026": -7.79},
        "Feb": {"2024": 1.8, "2025": 0.5},
    },
    "summary": "Ringkasan musiman.",
    "yearly_avg": 2.5,
}


def _provider(handler):
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"
    from app.providers.idx_edge_provider import IdxEdgeProvider
    p = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://stock.arjum.com",
    ))
    return p, old


def test_seasonal_payload():
    p = seasonal_payload("BBCA", SAMPLE)
    assert p is not None
    assert p["ticker"] == "BBCA"
    assert p["years"] == ["2024", "2025", "2026"]
    assert len(p["months"]) == 12
    assert p["monthly_returns"]["Jan"]["2026"] == -7.79
    assert p["yearly_avg"] == 2.5
    assert seasonal_payload("BBCA", None) is None
    assert seasonal_payload("BBCA", {}) is None
    # years dihitung dari data bila tidak ada
    q = seasonal_payload("BBCA", {"monthly_returns": {"Mar": {"2023": 1.0}}})
    assert q is not None and q["years"] == ["2023"]


def test_seasonal_route():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE)

    p, old = _provider(handler)
    real = seasonal_mod.IdxEdgeProvider
    seasonal_mod.IdxEdgeProvider = lambda: p  # noqa: E731
    try:
        app = FastAPI()
        app.include_router(seasonal_router)
        r = TestClient(app).get("/api/seasonal/BBCA")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] and data["data"]["ticker"] == "BBCA"
    finally:
        seasonal_mod.IdxEdgeProvider = real
        settings.idx_edge_api_key = old


def test_seasonal_empty_returns_unsuccessful():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    p, old = _provider(handler)
    real = seasonal_mod.IdxEdgeProvider
    seasonal_mod.IdxEdgeProvider = lambda: p  # noqa: E731
    try:
        app = FastAPI()
        app.include_router(seasonal_router)
        r = TestClient(app).get("/api/seasonal/BBCA")
        assert r.json()["success"] is False
    finally:
        seasonal_mod.IdxEdgeProvider = real
        settings.idx_edge_api_key = old


def main():
    test_seasonal_payload()
    test_seasonal_route()
    test_seasonal_empty_returns_unsuccessful()
    print("OK: test_seasonal lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
