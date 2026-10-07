"""Test router order-flow + dates (tanpa jaringan asli, data contoh IDX Edge).

Jalan: ./.venv/bin/python test_order_flow.py
"""

import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import order_flow as of_mod
from app.routers.order_flow import (
    done_dates_payload,
    router as order_flow_router,
)


class _FakeProvider:
    def __init__(self, details=None, dates=None):
        self._details = details
        self._dates = dates

    async def fetch_done_details(self, code, date=None, page=1, per_page=100):
        return self._details

    async def fetch_done_detail_dates(self, code):
        return self._dates


def _use(fake):
    real = of_mod.IdxEdgeProvider
    of_mod.IdxEdgeProvider = lambda: fake  # noqa: E731
    return real


def test_dates_payload():
    assert done_dates_payload(None) is None
    assert done_dates_payload({}) is None
    out = done_dates_payload({"code": "BBCA", "count": 2, "dates": ["2026-10-06", "2026-10-05"]})
    assert out is not None
    assert out["code"] == "BBCA"
    assert out["dates"] == ["2026-10-06", "2026-10-05"], out
    out2 = done_dates_payload({"code": "BBCA", "dates": ["2026-10-06", 7, None]})
    assert out2 is not None and out2["dates"] == ["2026-10-06"], out2


def test_dates_route():
    fake = _FakeProvider(
        dates={"code": "BBCA", "count": 2, "dates": ["2026-10-06", "2026-10-05"]}
    )
    real = _use(fake)
    try:
        app = FastAPI()
        app.include_router(order_flow_router)
        r = TestClient(app).get("/api/order-flow/BBCA/dates")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"], data
        assert data["data"]["dates"] == ["2026-10-06", "2026-10-05"], data
    finally:
        of_mod.IdxEdgeProvider = real


def test_dates_route_empty_unsuccessful():
    fake = _FakeProvider(dates={"code": "BBCA", "count": 0, "dates": []})
    real = _use(fake)
    try:
        app = FastAPI()
        app.include_router(order_flow_router)
        data = TestClient(app).get("/api/order-flow/BBCA/dates").json()
        assert data["success"] is False, data
    finally:
        of_mod.IdxEdgeProvider = real


def test_order_flow_date_param_reaches_provider():
    seen = {}

    class _Spy(_FakeProvider):
        async def fetch_done_details(self, code, date=None, page=1, per_page=100):
            seen["args"] = (code, date, page, per_page)
            return {
                "code": code,
                "date": date or "2026-10-06",
                "total": 1,
                "data": [{"time": "09:00:01", "price_num": 100, "lot": 1, "value_raw": 10000, "buyer": "A", "seller": "B"}],
            }

    real = _use(_Spy())
    try:
        app = FastAPI()
        app.include_router(order_flow_router)
        data = TestClient(app).get("/api/order-flow/BBCA?date=2026-10-06&limit=50").json()
        assert data["success"], data
        assert seen["args"][1] == "2026-10-06", seen
        assert data["data"]["date"] == "2026-10-06", data
        assert [r["time"] for r in data["data"]["rows"]] == ["09:00:01"]
    finally:
        of_mod.IdxEdgeProvider = real


def main():
    test_dates_payload()
    test_dates_route()
    test_dates_route_empty_unsuccessful()
    test_order_flow_date_param_reaches_provider()
    print("OK: test_order_flow lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
