"""Test modul analisis akumulasi (murni, tanpa jaringan).

Jalan: ./.venv/bin/python test_accumulation_signals.py
"""

import json
import os
import sys
from datetime import date, timedelta

from app.analysis import accumulation as acc

FIX = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
BASE = date(2026, 1, 1)


def mk(closes, vols=None, fbuy=None, fsell=None, nf=None, spread=0.01, close_pos=0.8):
    """Bar sintetis. `close_pos` = posisi close dalam range (0=dekat low, 1=dekat high)."""
    rows = []
    for i, c in enumerate(closes):
        d = (BASE + timedelta(days=i)).isoformat()
        v = vols[i] if vols else 1_000_000
        hi = c * (1 + (1 - close_pos) * spread)
        lo = c * (1 - close_pos * spread)
        row = {
            "date": d, "open": c, "high": hi, "low": lo,
            "close": c, "volume": v, "value": c * v, "freq": 10, "avg": c,
        }
        if fbuy is not None:
            row["f_buy"] = fbuy[i]
        if fsell is not None:
            row["f_sell"] = fsell[i]
        if nf is not None:
            row["n_foreign"] = nf[i]
        rows.append(row)
    return rows


def _print(name, res):
    print(f"  [{name}] rated={res.get('rated')} depth={res.get('depth')} "
          f"score={res.get('score')} raw={res.get('raw_score')}")
    print(f"      reasons: {'; '.join(res.get('reasons', []))}")


# ------------------------------------------------------------- unit helpers

def test_foreign_convention():
    assert acc.foreign_flow({"f_buy": 100, "f_sell": 40}) == 60
    assert acc.foreign_flow({"n_foreign": 12}) == 12
    assert acc.foreign_flow({}) == 0


def test_prepare_sorts_and_dedupes():
    rows = mk([1000, 1001, 1002] * 12)  # 36 bar
    rows[5]["date"] = rows[4]["date"]  # duplikat
    prep = acc.prepare(rows)
    assert prep["ok"], prep
    dates = [b["date"] for b in prep["bars"]]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))
    assert any("duplikat" in x for x in prep["issues"]), prep["issues"]


def test_cmf_zero_range_no_div_error():
    rows = mk([1000] * 25, spread=0.0)  # high==low -> range nol
    bars = [dict(r) for r in rows]
    assert acc.cmf(bars, 20) == 0.0


def test_split_adjustment():
    closes = [1000] * 24 + [520] * 16
    vols = [1_000_000] * 24 + [2_500_000] * 16
    bars = acc.prepare(mk(closes, vols))["bars"]
    adj, flag = acc.adjust_splits(bars)
    assert flag is True
    assert abs(adj[0]["close"] - 520) < 1, adj[0]["close"]
    assert abs(adj[-1]["close"] - 520) < 1, adj[-1]["close"]


def test_as_of_no_lookahead():
    closes = [1000 + i for i in range(60)]
    rows = mk(closes)
    as_of = rows[49]["date"]
    res = acc.evaluate(rows, as_of=as_of)
    assert res["rated"], res
    assert res["raw_signals"]["close"] == closes[49], res["raw_signals"]["close"]


# ------------------------------------------------------------- dirty data

def test_dirty_dirty_data():
    assert acc.evaluate([])["reasons"][0] == "tidak ada data"
    r = acc.evaluate(mk([1000] * 10))
    assert not r["rated"] and "kurang" in r["reasons"][0], r
    r = acc.evaluate(mk([1000] * 40, vols=[0] * 40))
    assert not r["rated"] and "suspensi" in r["reasons"][0], r
    r = acc.evaluate(mk([1000] * 40, spread=0.0))
    assert not r["rated"] and "range" in r["reasons"][0], r
    # NaN dibuang, sisanya cukup -> tetap dinilai + catatan
    rows = mk([1000] * 40)
    for i in (0, 3, 7, 9, 11):
        rows[i]["close"] = None
    r = acc.evaluate(rows)
    assert r["rated"], r
    assert any("kotor" in x for x in r["reasons"]), r["reasons"]


# ------------------------------------------------------------- patterns

def test_pattern_accumulation():
    closes = [1000] * 20 + [1000 + 2 * i for i in range(20)]  # runup ~3.8%
    vols = [1_000_000 + 20_000 * i for i in range(40)]
    rows = mk(closes, vols, fbuy=[2_000_000] * 40, fsell=[1_000_000] * 40)
    res = acc.evaluate(rows)
    _print("akumulasi", res)
    assert res["rated"], res
    assert res["depth"] == "foreign", res
    assert res["components"]["foreign"] == 1.0, res["components"]
    assert res["score"] <= 60.0 and res["capped"] is True, res


def test_pattern_distribution():
    closes = [1000] * 10 + [1000 - 2 * i for i in range(30)]
    vols = [1_000_000 + 20_000 * i for i in range(40)]
    rows = mk(closes, vols, fbuy=[1_000_000] * 40, fsell=[2_000_000] * 40, close_pos=0.1)
    res = acc.evaluate(rows)
    _print("distribusi", res)
    assert res["rated"], res
    assert res["components"]["foreign"] == 0.0, res["components"]
    assert res["score"] < 45, res


def test_pattern_already_run():
    closes = [1000 + 10 * i for i in range(40)]  # runup ~16.8%
    res = acc.evaluate(mk(closes))
    _print("sudah_lari", res)
    assert not res["rated"] and "sudah naik" in res["reasons"][0], res


def test_pattern_sideways():
    rows = mk([1000] * 40, close_pos=0.5)
    res = acc.evaluate(rows)
    _print("sideways", res)
    assert res["rated"], res
    assert res["depth"] == "hv", res
    assert 20 < res["score"] < 60, res


# ------------------------------------------------------------- real fixtures

def _load(name):
    with open(os.path.join(FIX, name)) as f:
        return json.load(f)


def test_real_fixture_with_broker():
    hist = _load("history_bbca.json")
    brok = _load("broker_accumulation_bbca.json")
    res = acc.evaluate(hist["rows"], broker_payload=brok)
    _print("nyata_bbca", res)
    assert isinstance(res["rated"], bool)
    if res["rated"]:
        assert res["depth"] == "broker", res
        assert res["components"].get("broker") is not None, res
        assert res["raw_signals"]["broker"]["price_vs_buyer_avg"] is not None

    bs = acc.broker_signals(brok, current_close=6000.0, total_value=1e12)
    assert bs and bs["top_buyers"] and bs["concentration"] >= 0, bs


def test_real_fixture_as_of():
    hist = _load("history_bbca.json")
    rows = hist["rows"]
    # as_of salah satu tanggal dalam fixture -> close harus sama dengan bar itu
    as_of = sorted(r["date"] for r in rows)[39]
    res = acc.evaluate(rows, as_of=as_of)
    _print("nyata_as_of", res)
    expected = [r for r in rows if r["date"] == as_of][0]["close"]
    if res["rated"]:
        assert res["raw_signals"]["close"] == expected, (res["raw_signals"]["close"], expected)


def main():
    test_foreign_convention()
    test_prepare_sorts_and_dedupes()
    test_cmf_zero_range_no_div_error()
    test_split_adjustment()
    test_as_of_no_lookahead()
    test_dirty_dirty_data()
    test_pattern_accumulation()
    test_pattern_distribution()
    test_pattern_already_run()
    test_pattern_sideways()
    test_real_fixture_with_broker()
    test_real_fixture_as_of()
    print("OK: test_accumulation_signals lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
