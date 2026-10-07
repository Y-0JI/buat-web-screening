"""Test tool get_accumulation_candidates (baca DB tanpa jaringan).

Jalan: ./.venv/bin/python test_accumulation_tool.py
"""

import asyncio
import json
import os
import sys
from datetime import date, timedelta

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models import Base
import app.ai.agent as agent
import app.repositories.accumulation_repository as repo

DB = "/tmp/opencode/test_accum_tool.db"


async def _fresh():
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
    return engine


async def _test_reads_db_no_network():
    engine = await _fresh()
    # provider harus meledak bila tool menyentuh jaringan.
    orig = agent.IdxEdgeProvider

    def boom(*a, **k):
        raise RuntimeError("tool menyentuh jaringan!")

    agent.IdxEdgeProvider = boom
    try:
        await repo.save_scan(
            date.today(), "complete",
            signals=[{
                "ticker": "EMAS", "score": 48.2, "depth": "broker",
                "reasons": "asing beli; broker besar net beli",
                "components": {"raw": {"cmf": -0.05, "obv_slope": 0.01,
                                       "ad_slope": -0.02, "foreign": {"ratio": 0.7},
                                       "runup": -0.09}},
                "foreign_net": 26263600.0,
            }],
        )
        r = await agent._get_accumulation_candidates(limit=10)
        assert r["scan_date"] is not None and r["status"] == "complete", r
        assert r["stale"] is False, r
        assert r["candidates"][0]["ticker"] == "EMAS", r
        assert r["candidates"][0]["depth"] == "broker", r
        note = r["note"].lower()
        assert "bukan saran investasi" in note, r["note"]
        assert "deskriptif" in note, r["note"]
        assert "belum terbukti prediktif" in note, r["note"]
        assert "sedang diakumulasi" not in note, r["note"]
    finally:
        agent.IdxEdgeProvider = orig
        await engine.dispose()


async def _test_empty_and_stale_and_limit():
    engine = await _fresh()
    try:
        r = await agent._get_accumulation_candidates()
        assert r.get("error"), r

        old = date.today() - timedelta(days=30)
        await repo.save_scan(old, "partial", signals=[
            {"ticker": f"T{i}", "score": 10.0 + i, "depth": "hv",
             "components": {"raw": {}}} for i in range(30)
        ])
        r = await agent._get_accumulation_candidates(limit=999)
        assert r["stale"] is True, r
        assert len(r["candidates"]) <= 25, len(r["candidates"])
        assert r["status"] == "partial", r
        assert old.isoformat() in r.get("note", ""), r  # tanggal scan ikut terbawa di note
    finally:
        await engine.dispose()


async def _test_trigger_tidak_menyentuh_jaringan_saat_segar():
    from app.config import settings

    engine = await _fresh()
    orig = agent.IdxEdgeProvider
    saved_enabled = settings.accumulation_enabled
    saved_token = settings.accumulation_scan_token
    settings.accumulation_enabled = True
    settings.accumulation_scan_token = "secret"

    def boom(*a, **k):
        raise RuntimeError("trigger test menyentuh jaringan!")

    agent.IdxEdgeProvider = boom
    try:
        await repo.save_scan(date.today(), "complete", signals=[])
        from app.services import accumulation_scan as scan_mod
        out = await scan_mod.trigger_scan_if_stale()
        assert out == {"ok": False, "reason": "fresh"}, out
    finally:
        agent.IdxEdgeProvider = orig
        settings.accumulation_enabled = saved_enabled
        settings.accumulation_scan_token = saved_token
        await engine.dispose()


def main():
    asyncio.run(_test_reads_db_no_network())
    asyncio.run(_test_empty_and_stale_and_limit())
    asyncio.run(_test_trigger_tidak_menyentuh_jaringan_saat_segar())
    print("OK: test_accumulation_tool lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
