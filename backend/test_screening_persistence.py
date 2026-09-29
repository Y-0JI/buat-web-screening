"""T1 (issue #176): hasil batch scan tersimpan di DB — restart server tidak membuang data.

RED: `ScreeningResult` sudah ada di models, tapi `get_cached_screening` belum membaca
DB → assertion hasil dari DB setelah cache clear akan FAIL.
GREEN: scheduler persist ke DB + `get_cached_screening` fallback DB → PASS.

Jalan: `python test_screening_persistence.py`
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import delete

from app.cache.service import cache_service
from app.database import async_session, engine
from app.database.models import Base, ScreeningResult
from app.scheduler import get_cached_screening, get_screening_timestamp

_MODE = "testpersist"
_TS = 123.0
_SAMPLE = [
    {"ticker": "BBCA", "company_name": "Bank Central Asia",
     "score": 41.0, "verdict": "BUY", "confidence": 70.0,
     "summary": "s", "price": 9000.0, "change_percent": 0.5,
     "is_simulated": False, "mode": _MODE},
]


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_db():
    async with async_session() as session:
        await session.merge(
            ScreeningResult(mode=_MODE, results=_SAMPLE, updated_at=_TS)
        )
        await session.commit()


async def _clear_db():
    async with async_session() as session:
        await session.execute(
            delete(ScreeningResult).where(ScreeningResult.mode == _MODE)
        )
        await session.commit()


async def _clear_cache():
    await cache_service.clear("screen")


async def main():
    await _create_tables()
    await _clear_db()
    await _clear_cache()

    # simulate restart: row ada di DB, memory cache kosong
    await _seed_db()
    await _clear_cache()

    rows, mode = await get_cached_screening(_MODE)
    assert rows == _SAMPLE, f"FAIL: hasil scan tidak didapat dari DB, dapat {rows}"
    assert mode == _MODE, f"FAIL: mode tak dikenal, dapat {mode}"
    ts = await get_screening_timestamp(_MODE)
    assert ts == _TS, f"FAIL: timestamp tak dikenal, dapat {ts}"

    await _clear_db()
    await _clear_cache()
    print("PASS: hasil scan selamat dari restart server, dibaca dari DB")


if __name__ == "__main__":
    asyncio.run(main())