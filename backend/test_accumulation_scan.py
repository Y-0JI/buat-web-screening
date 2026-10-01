"""Test orkestrator scan akumulasi + endpoint (httpx.MockTransport, DB sementara).

Jalan: ./.venv/bin/python test_accumulation_scan.py
"""

import asyncio
import os
import sys
from datetime import date, timedelta

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import Base
from app.main import app
from app.providers.idx_edge_provider import IdxEdgeProvider
import app.repositories.accumulation_repository as repo
import app.services.accumulation_scan as scan

DB = "/tmp/opencode/test_accum_scan.db"
BASE = date(2026, 8, 1)

CFG = {
    "accumulation_enabled": True,
    "accumulation_scan_token": "secret",
    "accumulation_history_limit": 10,
    "accumulation_broker_limit": 3,
    "accumulation_history_bars": 40,
    "accumulation_market_cap_min": 1e11,
    "accumulation_min_daily_value": 1.0,
    "accumulation_quota_reserve": 0,
    "accumulation_rotation_strata": 2,
    "accumulation_lookback_days": 20,
}


def _hist_rows(code, n=40):
    rows = []
    for i in range(n):
        c = 1000 + i
        rows.append({
            "date": (BASE + timedelta(days=i)).isoformat(),
            "open": c, "high": c * 1.002, "low": c * 0.99, "close": c,
            "volume": 1_000_000 + 10_000 * i, "value": c * (1_000_000 + 10_000 * i),
            "freq": 100, "avg": c, "f_buy": 2_000_000, "f_sell": 1_000_000,
            "n_foreign": 1_000_000,
        })
    return rows


def _brok_payload():
    return {
        "code": "AAA0", "start_date": "2026-08-01", "end_date": "2026-09-30",
        "series": [{
            "broker_code": "ZZ", "broker_name": "BIG BROKER",
            "points": [{"date": "2026-09-30", "nval": 1e12, "nvol": 1e6,
                        "bavg": 1000.0, "savg": 1000.0}],
        }],
        "top_buyers": [{"broker_code": "ZZ", "total_nval": 1e12}],
        "top_sellers": [],
    }


def make_handler(quota):
    state = {"remaining": quota}
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        state["remaining"] -= 1
        calls.append(path)
        hdr = {"x-ratelimit-remaining": str(state["remaining"]),
               "x-ratelimit-limit": "1000"}
        if path == "/api/health":
            return httpx.Response(200, json={"status": "ok"}, headers=hdr)
        if path == "/api/screener/latest":
            return httpx.Response(200, json={"date": "2026-09-30",
                                             "rows": [{"stock_code": "SEED1"}]}, headers=hdr)
        if path == "/api/market-cap":
            page = request.url.params.get("page", "1")
            data = ([{"code": f"AAA{i}", "market_cap": 2e11, "turnover_ratio": 0.01}
                     for i in range(10)] if page == "1" else [])
            return httpx.Response(200, json={"total": 10, "page": int(page),
                                             "per_page": 50, "total_pages": 1,
                                             "data": data}, headers=hdr)
        if path.startswith("/api/history/"):
            code = path.split("/")[-1]
            return httpx.Response(200, json={"stock_code": code, "rows": _hist_rows(code)}, headers=hdr)
        if path.startswith("/api/broker-accumulation/"):
            return httpx.Response(200, json=_brok_payload(), headers=hdr)
        return httpx.Response(404, json={"detail": "not mocked"}, headers=hdr)

    handler.calls = calls
    return handler


async def _fresh(handler):
    if os.path.exists(DB):
        os.remove(DB)
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB}")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    repo.async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    scan._provider = lambda: IdxEdgeProvider(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler),
                                 base_url="https://stock.arjum.com")
    )
    scan._in_progress = False
    return engine


def _apply_cfg(overrides=None):
    saved = {}
    for k, v in {**CFG, **(overrides or {})}.items():
        saved[k] = getattr(settings, k)
        setattr(settings, k, v)
    return saved


def _restore(saved):
    for k, v in saved.items():
        setattr(settings, k, v)


# --------------------------------------------------------------- endpoint

def test_endpoint_token_and_single_flight():
    saved = _apply_cfg()
    client = TestClient(app)
    orig = (scan.begin_scan, scan.continue_scan, scan.scan_running)
    try:
        settings.accumulation_scan_token = ""
        assert client.post("/api/accumulation/scan").status_code == 403

        settings.accumulation_scan_token = "secret"
        assert client.post("/api/accumulation/scan").status_code == 403
        assert client.post("/api/accumulation/scan",
                           headers={"X-Scan-Token": "salah"}).status_code == 403

        async def fake_begin(force=False):
            return {"ok": True, "scan_id": 123, "scan_date": "2026-09-30", "screener": {}}

        async def fake_continue(prep, force=False):
            return None

        scan.begin_scan = fake_begin
        scan.continue_scan = fake_continue
        scan.scan_running = lambda: False
        r = client.post("/api/accumulation/scan", headers={"X-Scan-Token": "secret"})
        assert r.status_code == 202 and r.json()["scan_id"] == 123, r.text

        scan.scan_running = lambda: True
        assert client.post("/api/accumulation/scan",
                           headers={"X-Scan-Token": "secret"}).status_code == 409
    finally:
        scan.begin_scan, scan.continue_scan, scan.scan_running = orig
        _restore(saved)


def test_get_reads_db_only():
    saved = _apply_cfg()
    handler = make_handler(quota=500)
    engine = asyncio.run(_fresh(handler))
    client = TestClient(app)

    def explode():
        raise RuntimeError("network!")

    try:
        # provider yang meledak bila dipakai -> GET tidak boleh menyentuhnya.
        scan._provider = explode
        empty = client.get("/api/accumulation/latest")
        assert empty.status_code == 200 and empty.json()["success"] is False, empty.text
        miss = client.get("/api/accumulation/ZZZZ")
        assert miss.status_code == 200 and miss.json()["success"] is False, miss.text
    finally:
        asyncio.run(engine.dispose())
        _restore(saved)


# --------------------------------------------------------------- funnel

def test_funnel_complete_and_rotation():
    saved = _apply_cfg()
    handler = make_handler(quota=500)
    engine = asyncio.run(_fresh(handler))
    try:
        async def run():
            prep = await scan.begin_scan(force=False)
            assert prep["ok"] and prep["scan_date"] == "2026-09-30", prep
            await scan.continue_scan(prep)
            latest = await repo.get_latest_scan()
            assert latest and latest["status"] in ("complete", "partial"), latest
            assert latest["signals"], latest
            # tier ordering: broker dulu
            depths = [s["depth"] for s in latest["signals"]]
            assert depths == sorted(depths, key=lambda d: {"broker": 0, "foreign": 1, "hv": 2}.get(d, 3)), depths
            assert latest["requests_used"] > 0, latest
            rot = await repo.get_rotation_map()
            assert rot, "rotasi kosong"
            assert scan.scan_running() is False
            return latest
        latest = asyncio.run(run())
        print(f"  [funnel] status={latest['status']} signals={len(latest['signals'])} "
              f"req={latest['requests_used']} quota={latest['quota_remaining']}")
    finally:
        asyncio.run(engine.dispose())
        _restore(saved)


def test_funnel_idempotent_skip():
    saved = _apply_cfg()
    handler = make_handler(quota=500)
    engine = asyncio.run(_fresh(handler))
    try:
        async def run():
            prep = await scan.begin_scan(force=False)
            await scan.continue_scan(prep)
            first = await repo.get_latest_scan()
            prep2 = await scan.begin_scan(force=False)
            assert prep2.get("skipped") is True, prep2
            assert prep2["scan_id"] == first["id"], (prep2, first["id"])
            # force menjalankan ulang
            prep3 = await scan.begin_scan(force=True)
            assert prep3["ok"] is True, prep3
            await scan.continue_scan(prep3)
        asyncio.run(run())
        print("  [idempotent] skip tanpa force OK")
    finally:
        asyncio.run(engine.dispose())
        _restore(saved)


def test_funnel_partial_quota():
    saved = _apply_cfg({"accumulation_quota_reserve": 50})
    handler = make_handler(quota=55)
    engine = asyncio.run(_fresh(handler))
    try:
        async def run():
            prep = await scan.begin_scan(force=False)
            await scan.continue_scan(prep)
            latest = await repo.get_latest_scan()
            assert latest["status"] == "partial", latest
            assert latest["note"] and "kuota" in latest["note"], latest
            return latest
        latest = asyncio.run(run())
        print(f"  [partial] status={latest['status']} req={latest['requests_used']} "
              f"quota={latest['quota_remaining']} note={latest['note']}")
    finally:
        asyncio.run(engine.dispose())
        _restore(saved)


def main():
    test_endpoint_token_and_single_flight()
    test_get_reads_db_only()
    test_funnel_complete_and_rotation()
    test_funnel_idempotent_skip()
    test_funnel_partial_quota()
    print("OK: test_accumulation_scan lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
