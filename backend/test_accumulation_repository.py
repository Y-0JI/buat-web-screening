"""Test repository akumulasi (SQLite sementara).

Jalan: ./.venv/bin/python test_accumulation_repository.py
"""

import asyncio
import os
import sys
from datetime import date

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models import Base
import app.repositories.accumulation_repository as repo

DB = "/tmp/opencode/test_accum.db"


async def _fresh():
    if os.path.exists(DB):
        os.remove(DB)
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    repo.async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine


async def _test_save_and_read():
    engine = await _fresh()
    try:
        res = await repo.save_scan(
            date(2026, 9, 30), "complete",
            universe_count=10, stage_b_count=5, stage_c_count=2,
            requests_used=21, quota_remaining=935,
            signals=[
                {"ticker": "bbca", "score": 80.0, "depth": "broker",
                 "components": {"obv": 1.2}, "reasons": "uji",
                 "close": 6000.0, "foreign_net": 1e9, "broker_net": 2e9},
                {"ticker": "BBRI", "score": 50.0, "depth": "hv",
                 "components": {"cmf": 0.1}, "reasons": "uji2", "close": 4000.0},
            ],
        )
        assert res["status"] == "complete" and res["skipped"] is False, res

        latest = await repo.get_latest_scan()
        assert latest["scan_date"] == "2026-09-30", latest
        sigs = latest["signals"]
        assert [s["ticker"] for s in sigs] == ["BBCA", "BBRI"], sigs
        assert sigs[0]["components"] == {"obv": 1.2}, sigs[0]
        assert sigs[0]["depth"] == "broker", sigs[0]

        sig = await repo.get_signal("bbri")
        assert sig["score"] == 50.0, sig
    finally:
        await engine.dispose()


async def _test_complete_not_overwritten():
    engine = await _fresh()
    try:
        r1 = await repo.save_scan(
            date(2026, 9, 30), "complete",
            signals=[{"ticker": "AAA", "score": 10.0}],
        )
        r2 = await repo.save_scan(
            date(2026, 9, 30), "complete",
            signals=[{"ticker": "BBB", "score": 20.0}],
        )
        assert r2.get("skipped") is True, r2
        assert r2["id"] == r1["id"], (r1, r2)
        assert [s["ticker"] for s in await repo.list_signals(r1["id"])] == ["AAA"]

        r3 = await repo.save_scan(
            date(2026, 9, 30), "complete",
            signals=[{"ticker": "CCC", "score": 30.0}], force=True,
        )
        assert r3.get("skipped") is False, r3
        # Setelah replace, hanya sinyal baru yang tersisa (id bisa dipakai ulang
        # oleh SQLite, jadi tidak diandalkan).
        assert [s["ticker"] for s in await repo.list_signals(r3["id"])] == ["CCC"]
    finally:
        await engine.dispose()


async def _test_unique_scan_date():
    engine = await _fresh()
    try:
        await repo.save_scan(date(2026, 9, 29), "partial")
        await repo.save_scan(date(2026, 9, 30), "complete")
        # partial untuk tanggal sama -> diganti, bukan dobel.
        r = await repo.save_scan(date(2026, 9, 29), "partial", universe_count=7)
        assert r["universe_count"] == 7, r
        got = await repo.get_scan_by_date(date(2026, 9, 29))
        assert got["universe_count"] == 7, got
    finally:
        await engine.dispose()


async def _test_rotation():
    engine = await _fresh()
    try:
        scan = await repo.save_scan(date(2026, 9, 30), "complete")
        await repo.upsert_rotation(
            [{"ticker": "bbca", "stratum": 0}, {"ticker": "BBRI", "stratum": 2}],
            scan["id"],
        )
        m = await repo.get_rotation_map()
        assert m == {"BBCA": scan["id"], "BBRI": scan["id"]}, m
        m2 = await repo.get_rotation_map(["BBCA"])
        assert list(m2.keys()) == ["BBCA"], m2
    finally:
        await engine.dispose()


def main():
    asyncio.run(_test_save_and_read())
    asyncio.run(_test_complete_not_overwritten())
    asyncio.run(_test_unique_scan_date())
    asyncio.run(_test_rotation())
    print("OK: test_accumulation_repository lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
