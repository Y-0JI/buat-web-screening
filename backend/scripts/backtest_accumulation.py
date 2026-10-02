"""Backtest sinyal akumulasi (offline-capable, tanpa look-ahead).

Dua backtest terpisah:
  (i)  harga-volume + arus asing dari history 250 hari, banyak tanggal sinyal.
  (ii) tier broker dari window broker-accumulation (pendek -> "daya rendah/indikatif").

Prinsip:
- Titik masuk = OPEN hari bursa BERIKUTNYA setelah `as_of`; keluar = CLOSE `N`
  hari bursa setelah masuk. ARA/ARB dan ketidakmungkinan beli TIDAK dimodelkan.
- Sampel acak berstrata per market cap (seed tetap), filter sama dengan produksi;
  TIDAK dipilih dari hasil scan / bucket screener.
- Cache ke disk; bisa dilanjutkan (resume); kegagalan satu ticker tidak menghentikan.
- Laporkan CI bootstrap + n efektif; jangan klaim edge dari rata-rata.
- Bobot TIDAK diubah otomatis; rekomendasi saja.

Jalankan (hanya saat kuota segar): ./.venv/bin/python -m scripts.backtest_accumulation
"""

import argparse
import asyncio
import json
import math
import os
import random
import statistics
from datetime import date, timedelta
from typing import Any, Callable, Optional

from app.analysis import accumulation as A
from app.config import settings

HORIZONS = (5, 10, 20)
DEFAULT_SAMPLES = 120
DEFAULT_STEP = 5
MIN_FRESH_QUOTA = 900
DEFAULT_CACHE = os.environ.get("ACCUMULATION_BACKTEST_CACHE", "/tmp/opencode/acc_backtest_cache")
SLIP_SENSITIVITY = (0.001, 0.003, 0.005)
FEE_BUY = 0.0015
FEE_SELL = 0.0025


# ------------------------------------------------------------------ sampling

def _split_groups(items: list[dict], strata: int) -> list[list[dict]]:
    n = max(1, strata)
    size = max(1, len(items) // n) if items else 1
    groups = [items[i * size:(i + 1) * size] for i in range(n)]
    if items and n * size < len(items):
        groups[-1].extend(items[n * size:])
    return [g for g in groups if g]


def stratified_sample(universe: list[dict], n: int, strata: int = 3, seed: int = 42) -> list[str]:
    """Sampel ACAK BERSTRATA per market cap, deterministik (seed tetap)."""
    items = sorted(universe, key=lambda r: r.get("market_cap") or 0, reverse=True)
    if not items:
        return []
    groups = _split_groups(items, strata)
    rnd = random.Random(seed)
    chosen: list[dict] = []
    for g in groups:
        take = round(n * len(g) / len(items))
        take = max(0, min(take, len(g)))
        chosen.extend(rnd.sample(g, take))
    if len(chosen) < n:
        pool = [r for r in items if r not in chosen]
        chosen.extend(rnd.sample(pool, min(n - len(chosen), len(pool))))
    return [r["code"] for r in chosen[:n]]


# ------------------------------------------------------------ forward return

def add_business_days(d: date, n: int) -> date:
    cur = d
    step = 1 if n >= 0 else -1
    left = abs(n)
    while left:
        cur += timedelta(days=step)
        if cur.weekday() < 5:
            left -= 1
    return cur


def split_calib_test(
    dates: list[str], ratio: float = 0.6, embargo_days: int = 20
) -> dict:
    """Bagi tanggal sinyal -> kalibrasi / embargo / uji (hari bursa).

    Kalibrasi = 60% tanggal sinyal paling awal. Periode uji dimulai `embargo_days`
    HARI BURSA setelah tanggal cut, agar tidak ada kebocoran jendela.
    """
    ordered = sorted(dates)
    cut_idx = int(len(ordered) * ratio)
    cut_date = ordered[cut_idx] if ordered else None
    embargo_start = (
        add_business_days(date.fromisoformat(cut_date), embargo_days).isoformat()
        if cut_date
        else None
    )
    calib = [d for d in ordered if cut_date is None or d < cut_date]
    test = [
        d for d in ordered
        if embargo_start is not None and d >= embargo_start
    ]
    embargo = [
        d for d in ordered
        if cut_date is not None and embargo_start is not None
        and not (d < cut_date) and d < embargo_start
    ]
    return {
        "cut_date": cut_date,
        "embargo_start": embargo_start,
        "test_start": embargo_start,
        "n_calib_dates": len(calib),
        "n_embargo_dates": len(embargo),
        "n_test_dates": len(test),
    }


def forward_return(bars: list[dict], idx: int, horizon: int, entry: str = "open") -> Optional[float]:
    """Return dari OPEN hari berikutnya (idx+1) ke CLOSE `horizon` hari sesudah masuk."""
    if idx + 1 >= len(bars):
        return None
    e = bars[idx + 1]["open"] if entry == "open" else bars[idx + 1]["close"]
    if not e or e <= 0:
        return None
    j = idx + 1 + horizon
    if j >= len(bars):
        return None
    return bars[j]["close"] / e - 1


def net_return(gross: float, slip: float, fee_buy: float = FEE_BUY, fee_sell: float = FEE_SELL) -> float:
    """Return bersih: beli mahal (slippage) + fee, jual murah + fee."""
    return (1 + gross) * ((1 - slip) * (1 - fee_sell)) / ((1 + slip) * (1 + fee_buy)) - 1


def quota_ok_for_universe(remaining: Optional[int], n_tickers: int,
                          reserve: int, overhead: int = 50) -> tuple[bool, int]:
    """Perlu = 2 request/ticker (history + broker) + overhead tetap + reserve."""
    need = 2 * n_tickers + overhead + reserve
    ok = remaining is not None and remaining >= need
    return ok, need


# ------------------------------------------------------------- reconstruction

def reconstruct_records(
    history_rows: list[dict],
    broker_payload: Optional[dict],
    ticker: str,
    step: int = DEFAULT_STEP,
    horizons=HORIZONS,
    lookback: int = A.LOOKBACK,
    min_bars: int = A.MIN_BARS,
    max_runup: float = 0.15,
    weights: Optional[dict] = None,
    cap_no_broker: float = A.SCORE_CAP_NO_BROKER,
    broker_confirm_min: float = 0.5,
) -> list[dict]:
    """Banyak tanggal as_of untuk satu saham. Return tidak memakai data > as_of.

    Seri forward return DISESUAIKAN split; setiap tanggal yang, bersama jendela
    sinyal atau jendela return-nya, melewati aksi korporasi -> window dibuang,
    bukan dinilai.
    """
    prep = A.prepare(history_rows)
    if not prep["ok"] or len(prep["bars"]) < min_bars:
        return []
    bars = prep["bars"]
    adj, _adjusted = A.adjust_splits(bars)
    adj_by_date = {b["date"]: i for i, b in enumerate(adj)}
    zones = set(A.split_zones(history_rows))
    maxh = max(horizons)

    def _span_has_zone(i: int) -> bool:
        # Hanya JENDELA RETURN yang tidak boleh melewati split; sinyal sudah
        # dihitung pada seri yang disesuaikan split (evaluate).
        lo = i + 1
        hi = min(len(bars), i + 2 + maxh)
        return any(bars[k]["date"] in zones for k in range(lo, hi))

    recs: list[dict] = []
    i = min_bars - 1
    while i + 1 + maxh < len(bars):
        as_of = bars[i]["date"]
        if _span_has_zone(i):
            i += step
            continue
        res = A.evaluate(
            history_rows, broker_payload=broker_payload, as_of=as_of,
            weights=weights, cap_no_broker=cap_no_broker, min_bars=min_bars,
            lookback=lookback, max_runup=max_runup, broker_confirm_min=broker_confirm_min,
        )
        rec: dict[str, Any] = {
            "ticker": ticker, "as_of": as_of, "rated": res["rated"],
            "depth": res.get("depth"), "score": res.get("score"),
            "broker_checked": res.get("broker_checked"),
            "broker_confirmed": res.get("broker_confirmed"),
        }
        for h in horizons:
            ai = adj_by_date[as_of]
            rec[f"ret_{h}"] = forward_return(adj, ai, h)
        recs.append(rec)
        i += step
    return recs


# -------------------------------------------------------------------- metrics

def bootstrap_ci(values: list[float], iters: int = 1000, seed: int = 7, alpha: float = 0.05):
    if not values:
        return (None, None)
    rnd = random.Random(seed)
    n = len(values)
    means = sorted(statistics.mean(rnd.choices(values, k=n)) for _ in range(iters))
    lo = means[int(alpha / 2 * iters)]
    hi = means[min(len(means) - 1, int((1 - alpha / 2) * iters))]
    return (lo, hi)


def _metrics(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "mean": None, "median": None, "hit": None}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "hit": sum(1 for v in values if v > 0) / len(values),
        "ci95": bootstrap_ci(values),
    }


def _rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(x: list[float], y: list[float]) -> Optional[float]:
    if len(x) != len(y) or len(x) < 3:
        return None
    n = len(x)
    if len(set(x)) == 1 or len(set(y)) == 1:
        return None
    rx, ry = _rankdata(x), _rankdata(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    denom = n * (n * n - 1)
    if denom == 0:
        return None
    return 1 - 6 * d2 / denom


def score_cuts(scores: list[float]) -> list[float]:
    ordered = sorted(scores)
    return [ordered[int(len(ordered) * q)] for q in (0.2, 0.4, 0.6, 0.8)]


def score_quintiles(records: list[dict], cuts: Optional[list[float]] = None) -> dict[str, list[dict]]:
    rated = [r for r in records if r.get("rated", True) and r.get("score") is not None]
    if not rated:
        return {}
    if cuts is None:
        cuts = score_cuts([r["score"] for r in rated])
    buckets: dict[str, list[dict]] = {f"Q{i+1}": [] for i in range(5)}
    for r in rated:
        s = r["score"]
        idx = 0
        while idx < 4 and s >= cuts[idx]:
            idx += 1
        buckets[f"Q{idx+1}"].append(r)
    return buckets


def mean_diff_bootstrap_ci(
    a: list[float], b: list[float], iters: int = 1000, seed: int = 7, alpha: float = 0.05
) -> tuple[float, float, float]:
    if not a or not b:
        return (0.0, 0.0, 0.0)
    diff = statistics.mean(a) - statistics.mean(b) if a and b else 0.0
    rnd = random.Random(seed)
    na, nb = len(a), len(b)
    boots = sorted(
        (statistics.mean(rnd.choices(a, k=na)) - statistics.mean(rnd.choices(b, k=nb)))
        for _ in range(iters)
    )
    return (diff, boots[int(alpha / 2 * iters)],
            boots[min(len(boots) - 1, int((1 - alpha / 2) * iters))])


def eval_group(values: list[float], baseline: list[float], n_effective: int,
               slip_levels=SLIP_SENSITIVITY, min_effective: int = 30) -> dict:
    out: dict[str, Any] = {"n": len(values), "n_effective": n_effective}
    if not values or not baseline:
        out.update({"gross": _metrics([]), "net": {}, "baseline": _metrics([]),
                    "mean_diff": None, "mean_diff_ci95": (None, None),
                    "n_ok": False, "edge": False})
        return out
    gross = _metrics(values)
    net: dict[str, dict] = {}
    for slip in slip_levels:
        net[f"slip_{slip}"] = _metrics([net_return(v, slip) for v in values])
    diff, lo, hi = mean_diff_bootstrap_ci(values, baseline)
    out.update({
        "gross": gross, "net": net, "baseline": _metrics(baseline),
        "mean_diff": diff, "mean_diff_ci95": (lo, hi),
        "n_ok": n_effective >= min_effective,
    })
    out["edge"] = out["n_ok"] and lo is not None and hi is not None and lo > 0
    return out


def _gross_values(entries: list) -> list[float]:
    """Normalisasi entri kuantil mentah: dict berisi `ret` atau angka mentah."""
    values: list[float] = []
    for entry in entries or []:
        if isinstance(entry, dict):
            value = entry.get("ret")
        elif isinstance(entry, (int, float)) and not isinstance(entry, bool):
            value = float(entry)
        else:
            value = None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return values


def edge_verdict(
    quintiles: dict[str, list],
    baseline: list,
    n_effective: int,
    slip_levels=SLIP_SENSITIVITY,
    min_effective: int = 30,
    min_spearman: float = 0.7,
) -> dict:
    per_slip: dict[float, dict] = {}
    for slip in slip_levels:
        q5 = [net_return(v, slip) for v in _gross_values(quintiles.get("Q5", []))]
        bnet = [net_return(v, slip) for v in _gross_values(baseline)]
        diff, lo, hi = mean_diff_bootstrap_ci(q5, bnet)
        n_ok = n_effective >= min_effective and len(q5) > 0
        per_slip[slip] = {
            "q5_minus_base": diff, "q5_minus_base_ci95": (lo, hi),
            "ci_ok": lo is not None and lo > 0, "n_ok": n_ok,
            "edge": bool(n_ok and lo is not None and lo > 0),
        }
    qret, qid = [], []
    for i in range(1, 6):
        qs = [net_return(v, slip_levels[0]) for v in _gross_values(quintiles.get(f"Q{i}", []))]
        if qs:
            qret.append(statistics.mean(qs))
            qid.append(float(i))
    rho = spearman_rho(qid, qret)
    verdict = {
        "spearman": rho,
        "monotone_ok": rho is not None and rho >= min_spearman,
        "per_slip": per_slip,
        "overall": False,
    }
    verdict["overall"] = bool(
        verdict["monotone_ok"] and verdict["per_slip"][slip_levels[0]]["edge"]
    )
    return verdict


def random_baseline(records: list[dict], horizon: int, seed: int = 42) -> list[dict]:
    """Satu draw acak per (as_of, stratum) dengan seed tetap (baseline acak)."""
    pool: dict[tuple, list[float]] = {}
    for r in records:
        value = r.get(f"ret_{horizon}")
        if value is not None:
            pool.setdefault((r.get("as_of"), r.get("stratum")), []).append(value)
    rnd = random.Random(seed)
    draws = []
    for key in sorted(pool, key=lambda k: (str(k[0]), str(k[1]))):
        draws.append({"as_of": key[0], "stratum": key[1], "ret": rnd.choice(pool[key])})
    return draws


def verdict_for_broker_window(records: list[dict], window: dict,
                              horizon: int = 5,
                              slip_levels=SLIP_SENSITIVITY,
                              min_effective: int = 30,
                              min_spearman: float = 0.7) -> dict:
    """Putusan khusus tier broker dalam window broker-accumulation (daya rendah)."""
    start, end = window.get("start"), window.get("end")
    in_window = [r for r in records
                 if r.get("rated")
                 and r.get(f"ret_{horizon}") is not None
                 and r.get("depth") == "broker"
                 and (start is None or r.get("as_of", "") >= start)
                 and (end is None or r.get("as_of", "") <= end)]
    baseline = [r[f"ret_{horizon}"] for r in records
                if r.get(f"ret_{horizon}") is not None
                and (start is None or r.get("as_of", "") >= start)
                and (end is None or r.get("as_of", "") <= end)]
    cuts = score_cuts([r["score"] for r in in_window if r.get("score") is not None]) if in_window else None
    qb = {k: [{**r, "ret": r[f"ret_{horizon}"]} for r in v]
          for k, v in score_quintiles(in_window, cuts=cuts).items()}
    n_eff = effective_n(in_window, horizon)
    verdict = edge_verdict(qb, baseline, n_eff,
                           slip_levels=slip_levels, min_effective=min_effective,
                           min_spearman=min_spearman)
    n_dates = len({r["as_of"] for r in in_window})
    return {
        "window": window,
        "n_records": len(in_window),
        "n_signal_dates": n_dates,
        "n_effective": n_eff,
        "verdict": verdict,
        "power_notes": [f"daya rendah/indikatif: window broker-accumulation pendek "
                        f"({start}..{end}), n_signal_dates={n_dates}, n_records={len(in_window)}"],
        "caveats": ["tier broker hanya dari window broker-accumulation"],
    }


def verdict_for_horizon(records: list[dict], horizon: int,
                        slip_levels=SLIP_SENSITIVITY,
                        min_effective: int = 30,
                        min_spearman: float = 0.7,
                        embargo_days: int = 20) -> dict:
    rated = [r for r in records
             if r.get("rated") and r.get(f"ret_{horizon}") is not None]
    recs = [{**r, "ret": r[f"ret_{horizon}"]} for r in rated]
    dates = sorted({r["as_of"] for r in recs})
    split = split_calib_test(dates, embargo_days=embargo_days)
    calib = [r for r in recs if split["cut_date"] is not None and r["as_of"] < split["cut_date"]]
    test = [r for r in recs
            if split["embargo_start"] is not None and r["as_of"] >= split["embargo_start"]]
    cuts = score_cuts([r["score"] for r in calib]) if calib else None
    qb = {k: [{**r, "ret": r["ret"]} for r in v]
          for k, v in score_quintiles(test, cuts=cuts).items()}
    baseline = [r["ret"] for r in recs
                if split["embargo_start"] is not None and r["as_of"] >= split["embargo_start"]]
    verdict = edge_verdict(qb, baseline, effective_n(test, horizon),
                           slip_levels=slip_levels, min_effective=min_effective,
                           min_spearman=min_spearman)
    return {
        "horizon": horizon, "n_rated": len(recs),
        "n_calib": len(calib), "n_test": len(test),
        "n_effective": effective_n(test, horizon),
        "split": split, "verdict": verdict,
    }


def effective_n(records: list[dict], horizon: int) -> int:
    """Perkiraan n efektif: sinyal dgn window tumpang-tindih dihitung sekali."""
    by_ticker: dict[str, list[str]] = {}
    for r in records:
        if r.get(f"ret_{horizon}") is None:
            continue
        by_ticker.setdefault(r["ticker"], []).append(r["as_of"])
    count = 0
    for _t, dates in by_ticker.items():
        dates.sort()
        last = None
        for d in dates:
            if last is None or (date.fromisoformat(d) - date.fromisoformat(last)).days >= horizon:
                count += 1
                last = d
    return count


def build_report(records: list[dict], horizons=HORIZONS) -> dict:
    report: dict[str, Any] = {}
    for h in horizons:
        key = f"ret_{h}"
        rated = [r for r in records if r.get("rated") and r.get(key) is not None]
        allv = [r[key] for r in records if r.get(key) is not None]
        per_h: dict[str, Any] = {
            "baseline_all": _metrics(allv),
            "signal_all": _metrics([r[key] for r in rated]),
            "by_depth": {},
            "by_quintile": {},
            "effective_n_signal": effective_n(rated, h),
            "net_sensitivity": {},
        }
        for slip in SLIP_SENSITIVITY:
            gross = [r[key] for r in rated]
            netv = [net_return(v, slip) for v in gross]
            per_h["net_sensitivity"][f"slip_{slip}"] = _metrics(netv)
        for depth in ("broker", "foreign", "hv"):
            vals = [r[key] for r in rated if r.get("depth") == depth]
            per_h["by_depth"][depth] = _metrics(vals)
        for q, recs in score_quintiles(rated).items():
            vals = [r[key] for r in recs if r.get(key) is not None]
            per_h["by_quintile"][q] = _metrics(vals)
        report[f"h{h}"] = per_h
    return report


# ------------------------------------------------------------------ fetching

def _cache_path(cache_dir: str, kind: str, ticker: str) -> str:
    return os.path.join(cache_dir, kind, f"{ticker}.json")


async def cached_fetch(cache_dir: str, kind: str, ticker: str, coro_fn: Callable) -> Optional[Any]:
    path = _cache_path(cache_dir, kind, ticker)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    data = await coro_fn()
    if data is None:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


async def run_backtest(
    provider,
    universe: list[dict],
    n_samples: int = DEFAULT_SAMPLES,
    seed: int = 42,
    cache_dir: str = DEFAULT_CACHE,
    step: int = DEFAULT_STEP,
    horizons=HORIZONS,
    hist_limit: int = 250,
) -> dict:
    sample = stratified_sample(universe, n_samples, seed=seed)
    records: list[dict] = []
    failures: list[str] = []
    reserve = settings.accumulation_quota_reserve

    for code in sample:
        if provider.quota_remaining() is not None and provider.quota_remaining() <= reserve:
            failures.append(f"stop:kuota<=reserve@{code}")
            break
        try:
            hist = await cached_fetch(
                cache_dir, "history", code,
                lambda c=code: provider.fetch_history(c, limit=hist_limit),
            )
            if not hist:
                failures.append(code)
                continue
            brok = await cached_fetch(
                cache_dir, "broker", code,
                lambda c=code: provider.fetch_broker_accumulation(c),
            )
            records.extend(reconstruct_records(hist, brok, code, step=step, horizons=horizons))
        except Exception as e:  # noqa: BLE001 — satu ticker gagal tidak menghentikan
            failures.append(f"{code}:{type(e).__name__}")

    dates = sorted({r["as_of"] for r in records})
    cut = dates[int(len(dates) * 0.6)] if dates else None
    calib = [r for r in records if cut is None or r["as_of"] < cut]
    test = [r for r in records if cut is not None and r["as_of"] >= cut]

    min_eff = settings.accumulation_backtest_min_effective_n
    verdicts = {
        h: verdict_for_horizon(records, h, min_effective=min_eff)
        for h in horizons
    }

    return {
        "n_sample": len(sample),
        "n_records": len(records),
        "failures": failures,
        "cut_date": cut,
        "calibration": build_report(calib, horizons),
        "test": build_report(test, horizons),
        "verdicts": verdicts,
        "limitations": [
            "Satu rezim pasar (periode pendek).",
            "Universe/survivorship dari data hari ini (market-cap sekarang).",
            "Tanpa IHSG; baseline = rata-rata semua sampel di tanggal yang sama.",
            "ARA/ARB & ketidakmungkinan beli tidak dimodelkan.",
            "Sinyal berurutan berkorelasi -> pakai n efektif, jangan klaim signifikansi.",
            "Tier broker hanya dari window broker-accumulation (pendek) -> daya rendah/indikatif.",
            "Bobot tidak dikalibrasi otomatis; rekomendasi saja.",
        ],
    }


async def check_broker_range(provider, code: str = "BBCA", requested_start: str = "2026-01-01") -> dict:
    """1 request: cek apakah rentang broker-accumulation bisa diperpanjang."""
    data = await provider.fetch_broker_accumulation(code, start_date=requested_start)
    if not data:
        return {"extended": False, "note": "tidak ada data"}
    actual = data.get("start_date")
    return {
        "requested_start": requested_start,
        "actual_start": actual,
        "extended": bool(actual and str(actual) <= requested_start),
        "n_series": len(data.get("series") or []),
    }


# ---------------------------------------------------------------------- CLI

async def _cli() -> int:
    from app.providers.idx_edge_provider import IdxEdgeProvider

    ap = argparse.ArgumentParser(description="Backtest sinyal akumulasi (kuota segar wajib)")
    ap.add_argument("--samples", type=int, default=0,
                    help="0 = seluruh universe lolos filter produksi")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--step", type=int, default=DEFAULT_STEP)
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--max-requests", type=int, default=2500)
    ap.add_argument("--dry-run", action="store_true", help="hanya cetak rencana kuota")
    args = ap.parse_args()

    provider = IdxEdgeProvider()
    await provider.fetch_market_cap(page=1, per_page=1)  # probe pertama
    remaining = provider.quota_remaining()
    limit = provider.ratelimit_limit
    reserve = settings.accumulation_quota_reserve

    universe = [
        r for r in await provider.fetch_market_cap_all()
        if (r.get("market_cap") or 0) >= settings.accumulation_market_cap_min
    ]
    n = len(universe) if args.samples <= 0 else min(args.samples, len(universe))
    ok, need = quota_ok_for_universe(remaining, n, reserve)
    rate = settings.rate_limit_per_minute or 60
    est_min = round(need / rate, 1)

    print(json.dumps({
        "ratelimit_limit": limit,
        "remaining": remaining,
        "universe": len(universe),
        "samples": n,
        "reserve": reserve,
        "need": need,
        "rate_per_minute": rate,
        "est_minutes": est_min,
        "max_requests": args.max_requests,
        "gate_ok": ok and need <= args.max_requests,
    }, indent=1))

    if need > args.max_requests:
        print(f"ABORT: need {need} > max_requests {args.max_requests}")
        return 3
    if not ok:
        print(f"ABORT: remaining {remaining} < need {need}")
        return 2
    if args.dry_run:
        return 0

    print("cek rentang broker:", json.dumps(await check_broker_range(provider)))

    report = await run_backtest(
        provider, universe, n_samples=n, seed=args.seed,
        cache_dir=args.cache, step=args.step,
    )
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_cli()))
