"""T2 (issue #176): insight tidak mencacahkan hasil kosong & membaca screening dari DB.

RED: `market_insight` menyimpan hasil "belum tersedia" ke `_insight_cache` walau
tidak ada data → hasil kosong beku 30 menit → RED assert cache tetap kosong FAIL.
GREEN: hanya cache bila ada data (total_stocks > 0).

Jalan: `python test_insight_persistence.py`
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app.routers.insight as insight_mod
from sqlalchemy import delete

from app.cache.service import cache_service
from app.database import async_session, engine
from app.database.models import Base, ScreeningResult

_MODE_EMPTY = "testempty"
_MODE_DATA = "testins"
_TS = 456.0
_SAMPLE = [{"ticker": "BBCA", "score": 41.0, "verdict": "BUY", "confidence": 70.0,
            "summary": "s", "mode": _MODE_DATA}]


class _FakeAI:
    """Stub AI — jalankan tanpa panggil 9router (network-free, deterministik)."""

    class _Completions:
        def create(self, **kwargs):
            class _Msg:
                content = "SENTIMEN: bullish\nRINGKASAN: Pasar menguat di mode test."
            class _Choice:
                message = _Msg()
            class _Resp:
                choices = [_Choice()]
            return _Resp()

    chat = type("_Chat", (), {"completions": _Completions()})


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed(mode, results):
    from app.database.models import ScreeningResult
    async with async_session() as session:
        await session.merge(ScreeningResult(mode=mode, results=results, updated_at=_TS))
        await session.commit()


async def _clear():
    from app.database.models import ScreeningResult
    async with async_session() as session:
        await session.execute(
            delete(ScreeningResult).where(ScreeningResult.mode.in_([_MODE_EMPTY, _MODE_DATA]))
        )
        await session.commit()
    await cache_service.clear("screen")
    insight_mod._insight_cache.clear()


async def main():
    await _create_tables()
    insight_mod.get_client = lambda: _FakeAI()

    # Tanpa data → respons kosong TAPI tidak boleh masuk _insight_cache
    await _clear()
    await insight_mod.market_insight(_MODE_EMPTY)
    assert not insight_mod._insight_cache, (
        f"FAIL: hasil kosong masuk cache ({len(insight_mod._insight_cache)} entri)"
    )

    # Ada data di DB + memory cache kosong (simulasi restart) → insight dapat data
    await _clear()
    await _seed(_MODE_DATA, _SAMPLE)
    resp = await insight_mod.market_insight(_MODE_DATA)
    assert resp.success is True, "FAIL: insight gagal walau ada data screening"
    assert (resp.data or {}).get("total_stocks", 0) == 1, (
        f"FAIL: total_stocks harus 1 dari data DB, dapat {resp.data}"
    )
    assert insight_mod._insight_cache, "FAIL: hasil berisi data harus tetap dicache"
    assert "belum tersedia" not in (resp.data or {}).get("summary", "").lower()

    await _clear()
    print("PASS: insight tak mencacah kosong & membaca hasil scan dari DB")


if __name__ == "__main__":
    asyncio.run(main())