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
from datetime import date
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
    """Banyak tanggal as_of untuk satu saham. Return tidak memakai data > as_of."""
    prep = A.prepare(history_rows)
    if not prep["ok"] or len(prep["bars"]) < min_bars:
        return []
    bars = prep["bars"]
    maxh = max(horizons)
    recs: list[dict] = []
    i = min_bars - 1
    while i + 1 + maxh < len(bars):
        as_of = bars[i]["date"]
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
            rec[f"ret_{h}"] = forward_return(bars, i, h)
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


def score_quintiles(records: list[dict]) -> dict[str, list[dict]]:
    rated = [r for r in records if r.get("rated") and r.get("score") is not None]
    if not rated:
        return {}
    scores = sorted(r["score"] for r in rated)
    cuts = [scores[int(len(scores) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
    buckets: dict[str, list[dict]] = {f"Q{i+1}": [] for i in range(5)}
    for r in rated:
        s = r["score"]
        idx = 0
        while idx < 4 and s >= cuts[idx]:
            idx += 1
        buckets[f"Q{idx+1}"].append(r)
    return buckets


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

    return {
        "n_sample": len(sample),
        "n_records": len(records),
        "failures": failures,
        "cut_date": cut,
        "calibration": build_report(calib, horizons),
        "test": build_report(test, horizons),
        "limitations": [
            "Satu rezim pasar (periode pendek).",
            "Universe/survivorship dari data hari ini (market-cap sekarang).",
            "Tanpa IHSG; baseline = rata-rata sampel di tanggal sama.",
            "ARA/ARB & ketidakmungkinan beli tidak dimodelkan.",
            "Sinyal berurutan berkorelasi -> pakai n efektif, jangan klaim signifikansi.",
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
    ap.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--step", type=int, default=DEFAULT_STEP)
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    args = ap.parse_args()

    provider = IdxEdgeProvider()
    await provider.fetch_market_cap(page=1, per_page=1)  # probe pertama
    remaining = provider.quota_remaining()
    if remaining is None or remaining < MIN_FRESH_QUOTA:
        print(f"ABORT: sisa kuota {remaining} < {MIN_FRESH_QUOTA}. Jalankan setelah kuota reset.")
        return 2

    universe = [
        r for r in await provider.fetch_market_cap_all()
        if (r.get("market_cap") or 0) >= settings.accumulation_market_cap_min
    ]
    print("cek rentang broker:", json.dumps(await check_broker_range(provider)))

    report = await run_backtest(
        provider, universe, n_samples=args.samples, seed=args.seed,
        cache_dir=args.cache, step=args.step,
    )
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_cli()))
