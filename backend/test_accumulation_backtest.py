"""Test offline skrip backtest akumulasi (data sintetis, tanpa jaringan).

Jalan: ./.venv/bin/python test_accumulation_backtest.py
"""

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta

from scripts import backtest_accumulation as bt

START = date(2026, 1, 1)


def mk_hist(code, n=120):
    rows = []
    for i in range(n):
        c = 1000 + i * 0.5
        v = 1_000_000
        rows.append({
            "date": (START + timedelta(days=i)).isoformat(),
            "open": c, "high": c * 1.002, "low": c * 0.99, "close": c,
            "volume": v, "value": c * v, "freq": 100, "avg": c,
            "f_buy": 2_000_000, "f_sell": 1_000_000, "n_foreign": 1_000_000,
        })
    return rows


def mk_bars(opens, closes):
    return [{"open": o, "high": max(o, c), "low": min(o, c), "close": c,
             "volume": 1, "value": 1, "f_buy": 1, "f_sell": 0, "n_foreign": 1}
            for o, c in zip(opens, closes)]


class FakeProvider:
    def __init__(self, fail=(), quota=500):
        self.calls = {"history": 0, "broker": 0}
        self.fail = set(fail)
        self._q = quota

    def quota_remaining(self):
        return self._q

    async def fetch_history(self, code, limit=250):
        self.calls["history"] += 1
        if code in self.fail:
            raise RuntimeError("boom")
        return mk_hist(code)

    async def fetch_broker_accumulation(self, code, start_date=None, end_date=None):
        self.calls["broker"] += 1
        if code in self.fail:
            raise RuntimeError("boom")
        return {"code": code, "start_date": "2026-01-01", "end_date": "2026-04-30",
                "series": [], "top_buyers": [], "top_sellers": []}


def test_stratified_sample():
    universe = [{"code": f"A{i:03d}", "market_cap": 2e11 - i * 1e9} for i in range(30)]
    s1 = bt.stratified_sample(universe, 12, strata=3, seed=42)
    s2 = bt.stratified_sample(universe, 12, strata=3, seed=42)
    assert s1 == s2, "seed tetap harus deterministik"
    assert len(s1) == 12 and len(set(s1)) == 12
    # sebaran strata: minimal 1 dari tiap kelompok (top/mid/bottom market cap)
    codes = [r["code"] for r in universe]
    top = set(codes[:10]); bottom = set(codes[-10:])
    assert any(c in top for c in s1) and any(c in bottom for c in s1), s1


def test_forward_return_no_lookahead():
    bars = mk_bars(opens=[10] * 12, closes=[10 + i for i in range(12)])
    # idx=0 -> entry = open bar1 (=10), exit = close bar 1+5 = bar6 close (=16)
    r = bt.forward_return(bars, 0, 5)
    assert r is not None
    assert abs(r - (16 / 10 - 1)) < 1e-9, r
    # mengubah bar SETELAH exit tidak mengubah hasil
    bars2 = [dict(b) for b in bars]
    bars2[10]["close"] = 999
    assert bt.forward_return(bars2, 0, 5) == r
    # horizon melebihi data -> None (tidak menebak)
    assert bt.forward_return(bars, 0, 20) is None


def test_net_return_sensitivity():
    gross = 0.10
    nets = [bt.net_return(gross, s) for s in bt.SLIP_SENSITIVITY]
    assert nets[0] > nets[1] > nets[2], nets
    assert all(n < gross for n in nets), nets


def test_reconstruct_uses_as_of():
    hist = mk_hist("AAA0", n=120)
    recs = bt.reconstruct_records(hist, None, "AAA0", step=10)
    assert recs, "harus ada record"
    from app.analysis import accumulation as A
    # skor pada as_of harus sama dengan evaluate(as_of=...) -> tidak ada look-ahead
    for r in recs[:3]:
        res = A.evaluate(hist, as_of=r["as_of"])
        assert r["score"] == res["score"], (r["as_of"], r["score"], res["score"])
        assert r["as_of"] <= hist[-1]["date"]
    # forward return hanya ada bila cukup bar setelahnya
    assert any(r.get("ret_5") is not None for r in recs)


def test_report_ci_and_effective_n():
    hist = mk_hist("AAA0", n=120)
    recs = bt.reconstruct_records(hist, None, "AAA0", step=5)
    rep = bt.build_report(recs)
    h5 = rep["h5"]
    assert "baseline_all" in h5 and "by_quintile" in h5
    ci = h5["signal_all"]["ci95"]
    assert ci[0] is not None and ci[0] <= h5["signal_all"]["mean"] <= ci[1], ci
    en = bt.effective_n([r for r in recs if r.get("ret_5") is not None], 5)
    assert 0 < en <= len(recs), (en, len(recs))


def _test_cache_and_resume():
    async def run():
        tmp = tempfile.mkdtemp()
        try:
            prov = FakeProvider()
            d1 = await bt.cached_fetch(tmp, "history", "AAA0",
                                       lambda: prov.fetch_history("AAA0"))
            assert d1 and prov.calls["history"] == 1
            d2 = await bt.cached_fetch(tmp, "history", "AAA0",
                                       lambda: prov.fetch_history("AAA0"))
            assert d2 and prov.calls["history"] == 1, "cache harus dipakai ulang (resume)"
        finally:
            shutil.rmtree(tmp)
    asyncio.run(run())


def _test_run_backtest_resilient():
    async def run():
        tmp = tempfile.mkdtemp()
        try:
            universe = [{"code": f"AAA{i}", "market_cap": 2e11 - i} for i in range(8)]
            prov = FakeProvider(fail={"AAA0"})
            report = await bt.run_backtest(prov, universe, n_samples=8, seed=1,
                                           cache_dir=tmp, step=20)
            assert any(f.startswith("AAA0") for f in report["failures"]), report["failures"]
            assert report["n_records"] > 0, report
            assert "limitations" in report and report["limitations"]
        finally:
            shutil.rmtree(tmp)
    asyncio.run(run())


def _test_broker_range():
    class P:
        def __init__(self, start): self.start = start
        async def fetch_broker_accumulation(self, code, start_date=None, end_date=None):
            return {"start_date": self.start, "series": [{}]}

    ext = asyncio.run(bt.check_broker_range(P("2026-01-01"), requested_start="2026-01-01"))
    assert ext["extended"] is True, ext
    notext = asyncio.run(bt.check_broker_range(P("2026-06-08"), requested_start="2026-01-01"))
    assert notext["extended"] is False, notext


def main():
    test_stratified_sample()
    test_forward_return_no_lookahead()
    test_net_return_sensitivity()
    test_reconstruct_uses_as_of()
    test_report_ci_and_effective_n()
    _test_cache_and_resume()
    _test_run_backtest_resilient()
    _test_broker_range()
    print("OK: test_accumulation_backtest lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
