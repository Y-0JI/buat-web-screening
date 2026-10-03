"""Test router history (periode) + quote (tanpa jaringan).

Jalan: ./.venv/bin/python test_dashboard_market.py
"""

import asyncio
import sys
from datetime import date

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider, history_series
from app.routers import history as history_mod
from app.routers.history import period_to_limit, router as history_router
from app.routers import quote as quote_mod
from app.routers.quote import quote_payload, router as quote_router


def test_history_series_keeps_value_freq():
    out = history_series([
        {"date": "2026-10-02", "open": 1, "high": 2, "low": 1, "close": 2,
         "volume": 100, "value": 200, "freq": 5, "change": 1, "change_pct": 50.0},
        {"date": "2026-10-01", "open": 1, "high": 1, "low": 1, "close": 1,
         "volume": 50},
    ])
    assert [r["date"] for r in out] == ["2026-10-01", "2026-10-02"]
    assert out[1]["value"] == 200.0
    assert out[1]["freq"] == 5.0
    assert out[1]["change_pct"] == 50.0
    assert out[0]["value"] is None


def test_period_to_limit():
    assert period_to_limit("1W") == 20  # API menolak limit < 20
    assert period_to_limit("1M") == 22
    assert period_to_limit("3M") == 66
    assert period_to_limit("1Y") == 252
    assert period_to_limit("3mo") == 66
    ytd = period_to_limit("YTD")
    assert 20 <= ytd <= 500, ytd


def _provider(handler):
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"
    p = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://stock.arjum.com",
    ))
    return p, old


def test_history_route_uses_period_limit():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"rows": []})

    p, old = _provider(handler)
    real_history = history_mod.IdxEdgeProvider
    history_mod.IdxEdgeProvider = lambda: p  # noqa: E731
    try:
        app = FastAPI()
        app.include_router(history_router)
        r = TestClient(app).get("/api/history/BBCA?period=1W")
        assert r.status_code == 200, r.text
        assert "limit=20" in seen["url"], seen  # API menolak limit < 20
    finally:
        history_mod.IdxEdgeProvider = real_history
        settings.idx_edge_api_key = old


def test_quote_payload_and_route():
    price = {"last_price": 6100.0, "lot": 1290293.91, "value": 781124815800,
             "freq": 26154, "market_state": "closed", "market_label": "Market tutup"}
    payload = quote_payload("BBCA", price, "Bank Central Asia Tbk.")
    assert payload is not None
    assert payload["ticker"] == "BBCA"
    assert payload["last_price"] == 6100.0
    assert payload["name"] == "Bank Central Asia Tbk."
    assert quote_payload("BBCA", None, None) is None
    assert quote_payload("BBCA", {"last_price": "rusak"}, None) is None

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/api/price/BBCA"):
            return httpx.Response(200, json=price)
        if "/api/search" in url:
            return httpx.Response(200, json=[
                {"stock_code": "BBCA", "stock_name": "Bank Central Asia Tbk."}])
        return httpx.Response(404, json={"detail": "x"})

    p, old = _provider(handler)
    real_quote = quote_mod.IdxEdgeProvider
    quote_mod.IdxEdgeProvider = lambda: p  # noqa: E731
    try:
        app = FastAPI()
        app.include_router(quote_router)
        r = TestClient(app).get("/api/quote/BBCA")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] and data["data"]["last_price"] == 6100.0
        assert data["data"]["name"] == "Bank Central Asia Tbk."
    finally:
        quote_mod.IdxEdgeProvider = real_quote
        settings.idx_edge_api_key = old


def test_quote_disabled_returns_unsuccessful():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = ""
    try:
        app = FastAPI()
        app.include_router(quote_router)
        r = TestClient(app).get("/api/quote/BBCA")
        assert r.json()["success"] is False
    finally:
        settings.idx_edge_api_key = old


def main():
    test_history_series_keeps_value_freq()
    test_period_to_limit()
    test_history_route_uses_period_limit()
    test_quote_payload_and_route()
    test_quote_disabled_returns_unsuccessful()
    print("OK: test_dashboard_market lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
