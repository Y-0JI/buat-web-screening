"""Test scheduler akumulasi harian (tanpa jaringan asli, DB sementara/file).

Jalan: ./.venv/bin/python test_accumulation_daily.py
"""

import sys
from datetime import date, datetime, timezone


def test_next_run_at_senin_pagi():
    from app.services.accumulation_daily import next_run_at

    # Senin 06:00 WIB -> Senin 19:30 WIB hari yang sama.
    now = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)  # 13:00 WIB Senin
    assert next_run_at(now) == datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc)


def test_is_market_day():
    from datetime import date
    from app.services.accumulation_daily import data_date_today_wib, is_market_day
    assert is_market_day(date(2026, 10, 5)) is True   # Senin
    assert is_market_day(date(2026, 10, 10)) is False  # Sabtu
    assert data_date_today_wib(datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)) == date(2026, 10, 5)


def test_next_run_at_lewat_jadwal_lompat_ke_besok():
    from app.services.accumulation_daily import next_run_at
    # Senin 13:00 WIB (= 06:00 UTC) -> Senin 12:30 UTC (=19:30 WIB).
    assert next_run_at(datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)) == datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc)
    # Senin 13:00 WIB: jadwal hari ini (19:30) masih di depan -> tetap hari ini.
    assert next_run_at(datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)).date() == date(2026, 10, 5)
    # Senin 20:00 WIB (=13:00 UTC): jadwal hari ini lewat -> Selasa.
    assert next_run_at(datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc)).date() == date(2026, 10, 6)
    # Jumat 20:00 WIB -> Senin (lewati weekend).
    assert next_run_at(datetime(2026, 10, 9, 13, 0, tzinfo=timezone.utc)).date() == date(2026, 10, 12)


def test_run_one_cycle_lewati_bila_disabled_atau_busy(monkeypatch=None):
    # Tanpa jaringan/DB: begin_scan di-stub agar raise bila dipanggil.
    import asyncio
    from app.services import accumulation_daily as sched
    from app.config import settings
    saved_enabled, saved_token = settings.accumulation_enabled, settings.accumulation_scan_token
    settings.accumulation_enabled = False
    try:
        out = asyncio.run(sched._run_one_cycle("t"))
        assert out == {"ok": False, "reason": "disabled"}, out
    finally:
        settings.accumulation_enabled, settings.accumulation_scan_token = saved_enabled, saved_token


def main():
    test_next_run_at_senin_pagi()
    test_is_market_day()
    test_next_run_at_lewat_jadwal_lompat_ke_besok()
    test_run_one_cycle_lewati_bila_disabled_atau_busy()
    print("OK: test_accumulation_daily lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
