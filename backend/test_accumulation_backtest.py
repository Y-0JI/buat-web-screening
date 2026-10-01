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
from app.analysis import accumulation as A

START = date(2026, 1, 1)


def mk_rows(closes, vols, fbuy=None, fsell=None):
    rows = []
    for i, c in enumerate(closes):
        rows.append({
            "date": (START + timedelta(days=i)).isoformat(),
            "open": c, "high": c * 1.005, "low": c * 0.995, "close": c,
            "volume": vols[i], "value": c * vols[i], "freq": 100, "avg": c,
            "f_buy": fbuy[i] if fbuy else 0, "f_sell": fsell[i] if fsell else 0,
            "n_foreign": 0,
        })
    return rows


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
    def __init__(self, fail=(), quota=5000, limit=21000):
        self.calls = {"history": 0, "broker": 0, "market_cap": 0}
        self.fail = set(fail)
        self._q = quota
        self._limit = limit

    def quota_remaining(self):
        return self._q

    def min_ratelimit_remaining(self):
        return self._q

    def ratelimit_limit(self):
        return self._limit

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

    async def fetch_market_cap(self, page=1, per_page=50):
        self.calls["market_cap"] += 1
        return {"date": "2026-01-31", "total": 0, "page": page, "per_page": per_page,
                "total_pages": 1, "data": []}

    async def fetch_market_cap_all(self, max_pages=25, first_page=None):
        rows = []
        if first_page:
            rows.extend(first_page.get("data") or [])
        return rows


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


def _rows_with_split(n=60, split_at=30):
    closes = [1000 + i * 0.5 for i in range(n)]
    vols = [1_000_000] * n
    for i in range(split_at, n):
        closes[i] *= 2.0
        vols[i] *= 3.0
    return mk_rows(closes, vols)


def test_split_zones_exact():
    rows = _rows_with_split()
    zones = A.split_zones(rows)
    assert zones == [rows[30]["date"]], zones


def test_reconstruct_drops_windows_spanning_split():
    hist = _rows_with_split()
    recs = bt.reconstruct_records(hist, None, "AAA0", step=5)
    zones = set(A.split_zones(hist))
    assert zones, "kontrol: harus ada zona split"
    prep = A.prepare(hist)
    bars = prep["bars"]
    by_date = {b["date"]: i for i, b in enumerate(bars)}
    maxh = max(bt.HORIZONS)
    mb = A.MIN_BARS
    dropped = 0
    i = mb - 1
    while i + 1 + maxh < len(bars):
        span = {bars[k]["date"] for k in range(i + 1, min(len(bars), i + 2 + maxh))}
        if span & zones:
            dropped += 1
        i += 5
    assert dropped > 0, "kontrol: harus ada window yang melewati split"
    for r in recs:
        i = by_date[r["as_of"]]
        span = {bars[k]["date"] for k in range(i + 1, min(len(bars), i + 2 + maxh))}
        assert not (span & zones), (r["as_of"], span & zones)
    assert any(r.get("ret_5") is not None for r in recs)


def test_forward_returns_adjusted_series():
    hist = _rows_with_split()
    prep = A.prepare(hist)
    adj, adjusted = A.adjust_splits(prep["bars"])
    assert adjusted is True
    dates = [b["date"] for b in prep["bars"]]
    split_day = prep["bars"][30]["date"]
    late = [r for r in
            bt.reconstruct_records(hist, None, "AAA0", step=1) if r["as_of"] > split_day]
    assert late, "kontrol: harus ada window setelah split"
    by_date = {b["date"]: i for i, b in enumerate(adj)}
    for r in late[:3]:
        i = by_date[r["as_of"]]
        exp = adj[i + 1 + 5]["close"] / adj[i + 1]["open"] - 1
        assert abs(r["ret_5"] - exp) < 1e-9, (r["as_of"], r["ret_5"], exp)


def test_add_business_days():
    assert bt.add_business_days(date(2026, 9, 30), 1) == date(2026, 10, 1)
    assert bt.add_business_days(date(2026, 10, 2), 1) == date(2026, 10, 5)
    assert bt.add_business_days(date(2026, 9, 30), 20) == date(2026, 10, 28)


def _weekday_dates(start, n):
    d = start
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def test_embargo_split_dates():
    dates = _weekday_dates(date(2026, 1, 5), 60)
    split = bt.split_calib_test(dates, ratio=0.6, embargo_days=20)
    cut = date.fromisoformat(split["cut_date"])
    start = date.fromisoformat(split["embargo_start"])
    # embargo = 20 hari bursa: 19 hari di antaranya (strictly) + 1 hari cut.
    biz = [d for d in (date.fromisoformat(x) for x in dates)
           if d.weekday() < 5 and cut < d < start]
    assert len(biz) == 19, len(biz)
    assert split["n_embargo_dates"] == 20, split["n_embargo_dates"]
    assert split["test_start"] > split["cut_date"]
    assert split["n_calib_dates"] + split["n_test_dates"] + split["n_embargo_dates"] == 60


def test_spearman_known_cases():
    assert bt.spearman_rho([1, 2, 3], [1, 2, 3]) == 1.0
    assert bt.spearman_rho([1, 2, 3], [3, 2, 1]) == -1.0
    assert abs(bt.spearman_rho([1, 2, 3, 4], [2, 1, 4, 3]) - 0.6) < 1e-9
    assert abs(bt.spearman_rho([1, 1, 2], [1, 2, 3]) - 0.875) < 1e-9
    assert bt.spearman_rho([1, 1, 1], [2, 3, 4]) is None
    assert bt.spearman_rho([1, 2], [1, 2]) is None


def test_mean_diff_bootstrap_ci_degenerate():
    diff, lo, hi = bt.mean_diff_bootstrap_ci([0.05] * 40, [0.0] * 100, iters=200, seed=7)
    assert (diff, lo, hi) == (0.05, 0.05, 0.05), (diff, lo, hi)
    diff, lo, hi = bt.mean_diff_bootstrap_ci([0.0] * 40, [0.0] * 100, iters=200, seed=7)
    assert (diff, lo, hi) == (0.0, 0.0, 0.0), (diff, lo, hi)


def _verdict_inputs_true():
    q = {"Q1": [0.0] * 40, "Q2": [0.01] * 40, "Q3": [0.02] * 40,
         "Q4": [0.03] * 40, "Q5": [0.06] * 40}
    base = [0.0] * 100 + [0.01] * 100
    return q, base


def test_edge_verdict_true_case():
    q, base = _verdict_inputs_true()
    v = bt.edge_verdict(q, base, n_effective=40, slip_levels=(0.001,),
                        min_effective=30, min_spearman=0.7)
    assert v["overall"] is True, v
    assert v["per_slip"][0.001]["edge"] is True, v
    assert v["spearman"] == 1.0, v


def test_edge_verdict_false_cases():
    q, _ = _verdict_inputs_true()
    flat = [0.0] * 40
    v = bt.edge_verdict({k: list(flat) for k in ("Q1", "Q2", "Q3", "Q4", "Q5")},
                        [0.0] * 200, n_effective=40,
                        slip_levels=(0.001,), min_effective=30, min_spearman=0.7)
    assert v["overall"] is False, v
    v2 = bt.edge_verdict(q, [0.0] * 200, n_effective=5,
                         slip_levels=(0.001,), min_effective=30, min_spearman=0.7)
    assert v2["overall"] is False and v2["per_slip"][0.001]["n_ok"] is False, v2


def test_quintile_cuts_from_calibration():
    q1 = [{"score": s} for s in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]
    cuts = bt.score_cuts([r["score"] for r in q1])
    assert cuts == [3, 5, 7, 9], cuts
    test_recs = [{"score": 10}, {"score": 1}]
    buckets = bt.score_quintiles(test_recs, cuts=cuts)
    assert [r["score"] for r in buckets["Q5"]] == [10], buckets
    assert [r["score"] for r in buckets["Q1"]] == [1], buckets


def test_quota_ok_for_universe():
    ok, need = bt.quota_ok_for_universe(20000, 463, 200)
    assert (ok, need) == (True, 976 + 200), (ok, need)
    ok, need = bt.quota_ok_for_universe(500, 463, 200)
    assert ok is False, (ok, need)
    assert bt.quota_ok_for_universe(None, 463, 200) == (False, 1176)


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


def _bt_records(n=40):
    return [
        {
            "ticker": "AAA0",
            "as_of": f"2026-{(i % 9) + 1:02d}-01",
            "rated": True,
            "depth": "broker" if i % 2 else "foreign",
            "score": float(50 + (i % 10)),
            "broker_checked": True,
            "broker_confirmed": i % 2 == 0,
            "ret_5": 0.01 * ((i % 5) - 2),
            "ret_10": 0.01 * ((i % 7) - 3),
            "ret_20": 0.01 * ((i % 9) - 4),
        }
        for i in range(n)
    ]


BROKER_WINDOW = {"name": "broker", "start": "2026-01-01", "end": "2026-04-30"}


def test_verdict_for_broker_window_low_power():
    recs = _bt_records()
    v = bt.verdict_for_broker_window(recs, BROKER_WINDOW, horizon=5)
    assert v["window"] == BROKER_WINDOW, v
    assert v["n_signal_dates"] > 0, v
    notes = list(v.get("power_notes") or []) + list(v.get("caveats") or [])
    assert any(x.startswith("daya rendah") for x in notes), notes


def test_random_baseline_matches_date_stratum():
    recs = []
    for d in ("2026-01-05", "2026-01-12"):
        for s in ("A", "B"):
            for k in range(3):
                recs.append({
                    "ticker": f"T{s}{k}", "as_of": d, "stratum": s, "rated": True,
                    "ret_5": (k + 1) * 0.01 + (0.1 if s == "B" else 0.0),
                })
    first = bt.random_baseline(recs, 5, seed=7)
    second = bt.random_baseline(recs, 5, seed=7)
    assert first == second, "seed sama harus deterministik"
    assert len(first) == 4, first  # 2 tanggal x 2 strata
    pool = {}
    for r in recs:
        pool.setdefault((r["as_of"], r["stratum"]), set()).add(r["ret_5"])
    for draw in first:
        key = (draw["as_of"], draw["stratum"])
        assert draw["ret"] in pool[key], (draw, pool[key])


def main():
    test_stratified_sample()
    test_forward_return_no_lookahead()
    test_net_return_sensitivity()
    test_reconstruct_uses_as_of()
    test_split_zones_exact()
    test_reconstruct_drops_windows_spanning_split()
    test_forward_returns_adjusted_series()
    test_add_business_days()
    test_embargo_split_dates()
    test_spearman_known_cases()
    test_mean_diff_bootstrap_ci_degenerate()
    test_edge_verdict_true_case()
    test_edge_verdict_false_cases()
    test_quintile_cuts_from_calibration()
    test_quota_ok_for_universe()
    test_verdict_for_broker_window_low_power()
    test_random_baseline_matches_date_stratum()
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
