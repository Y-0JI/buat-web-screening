"""Sinyal & skor akumulasi pemain besar (murni, tanpa I/O).

Output `evaluate()`: komponen mentah (`raw_signals`) + skor + depth + reasons.
"""

import math
from typing import Any, Optional

MIN_BARS = 30
LOOKBACK = 20
SCORE_CAP_NO_BROKER = 60.0

DEFAULT_WEIGHTS = {
    "obv": 0.15,
    "ad": 0.10,
    "cmf": 0.10,
    "absorption": 0.15,
    "basing": 0.10,
    "vwap": 0.10,
    "foreign": 0.15,
    "broker": 0.15,
}


# --------------------------------------------------------------------- helpers

def _f(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _ramp(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return _clamp01((x - lo) / (hi - lo))


def _delta_ratio(series: list[float], lookback: int, denom: float) -> float:
    """Perubahan series pada jendela dinormalisasi terhadap skala bermakna (volume).

    Mencegah amplifikasi noise: deret yang praktis datar menghasilkan ~0, bukan
    rasio besar karena dibagi magnitudonya sendiri.
    """
    if len(series) < 2 or denom <= 0:
        return 0.0
    seg = series[-lookback:] if len(series) >= lookback else series
    x = (seg[-1] - seg[0]) / denom
    return max(-1.0, min(1.0, x))


def foreign_flow(bar: dict) -> float:
    """Konvensi: n_foreign = f_buy - f_sell; fallback ke kolom n_foreign."""
    fb, fs = _f(bar.get("f_buy")), _f(bar.get("f_sell"))
    if fb is not None and fs is not None:
        return fb - fs
    nf = _f(bar.get("n_foreign"))
    return nf if nf is not None else 0.0


# ------------------------------------------------------------------ cleaning

def prepare(rows: list[dict], as_of: Optional[str] = None, min_bars: int = MIN_BARS) -> dict:
    """Bersihkan & urutkan deret. Return {ok, reason, bars, issues}.

    - filter `date <= as_of`
    - buang baris NaN / harga tak valid
    - dedupe per tanggal (ambil yang terakhir)
    - deteksi suspensi/volume nol dan data kurang
    """
    issues: list[str] = []
    valid = 0
    dirty = 0
    by_date: dict[str, dict] = {}
    seen_dates: dict[str, int] = {}

    for r in rows or []:
        d = r.get("date")
        if not d:
            continue
        d = str(d)
        if as_of and d > str(as_of):
            continue
        seen_dates[d] = seen_dates.get(d, 0) + 1
        o, h, l, c = _f(r.get("open")), _f(r.get("high")), _f(r.get("low")), _f(r.get("close"))
        v = _f(r.get("volume"))
        if o is None or h is None or l is None or c is None or v is None:
            dirty += 1
            continue
        if c <= 0 or h < l:
            dirty += 1
            continue
        valid += 1
        by_date[d] = {
            "date": d, "open": o, "high": h, "low": l, "close": c,
            "volume": max(0.0, v), "value": _f(r.get("value")) or 0.0,
            "freq": _f(r.get("freq")) or 0.0,
            "f_buy": _f(r.get("f_buy")), "f_sell": _f(r.get("f_sell")),
            "n_foreign": _f(r.get("n_foreign")), "avg": _f(r.get("avg")),
        }

    bars = [by_date[k] for k in sorted(by_date)]
    dups = sum(1 for n in seen_dates.values() if n > 1)
    if dirty:
        issues.append(f"{dirty} baris kotor diabaikan")
    if dups:
        issues.append(f"{dups} tanggal duplikat (dipakai yang terakhir)")

    if not bars:
        return {"ok": False, "reason": "tidak ada data", "bars": [], "issues": issues}
    if len(bars) < min_bars:
        return {
            "ok": False,
            "reason": f"data kurang ({len(bars)} < {min_bars} bar)",
            "bars": bars,
            "issues": issues,
        }

    zero_vol = sum(1 for b in bars if b["volume"] <= 0)
    if zero_vol / len(bars) >= 0.3:
        return {
            "ok": False,
            "reason": "suspensi/volume nol",
            "bars": bars,
            "issues": issues,
        }
    if all(b["high"] == b["low"] for b in bars):
        return {"ok": False, "reason": "range harga nol", "bars": bars, "issues": issues}

    return {"ok": True, "reason": None, "bars": bars, "issues": issues}


def adjust_splits(bars: list[dict]) -> tuple[list[dict], bool]:
    """Sesuaikan lompatan harga karena aksi korporasi (split) agar tidak jadi sinyal palsu.

    Deteksi: rasio close melompat (<0.7 atau >1.4) DISERTAI lonjakan volume (>1.5x)
    pada hari yang sama. Bar sebelum hari itu diskalakan dengan rasio tersebut.
    """
    if len(bars) < 2:
        return [dict(b) for b in bars], False
    adj = [dict(b) for b in bars]
    adjusted = False
    for i in range(1, len(bars)):
        p0, p1 = bars[i - 1]["close"], bars[i]["close"]
        if p0 <= 0 or p1 <= 0:
            continue
        r = p1 / p0
        v0, v1 = bars[i - 1]["volume"], bars[i]["volume"]
        vr = (v1 / v0) if v0 > 0 else 0.0
        if (r < 0.7 or r > 1.4) and vr > 1.5:
            for j in range(i):
                for k in ("open", "high", "low", "close"):
                    adj[j][k] *= r
                if r > 0:
                    adj[j]["volume"] /= r
            adjusted = True
    return adj, adjusted


# ---------------------------------------------------------------- indicators

def obv_series(bars: list[dict]) -> list[float]:
    out = [0.0]
    for i in range(1, len(bars)):
        d = bars[i]["close"] - bars[i - 1]["close"]
        step = bars[i]["volume"] if d > 0 else (-bars[i]["volume"] if d < 0 else 0.0)
        out.append(out[-1] + step)
    return out


def ad_series(bars: list[dict]) -> list[float]:
    out: list[float] = []
    run = 0.0
    for b in bars:
        rng = b["high"] - b["low"]
        mfm = 0.0 if rng <= 0 else ((b["close"] - b["low"]) - (b["high"] - b["close"])) / rng
        run += mfm * b["volume"]
        out.append(run)
    return out


def cmf(bars: list[dict], period: int = LOOKBACK) -> float:
    seg = bars[-period:]
    vol = sum(b["volume"] for b in seg)
    if vol <= 0:
        return 0.0
    mfv = 0.0
    for b in seg:
        rng = b["high"] - b["low"]
        mfm = 0.0 if rng <= 0 else ((b["close"] - b["low"]) - (b["high"] - b["close"])) / rng
        mfv += mfm * b["volume"]
    return mfv / vol


def vwap(bars: list[dict], period: int = LOOKBACK) -> Optional[float]:
    seg = bars[-period:]
    vol = sum(b["volume"] for b in seg)
    if vol <= 0:
        return None
    return sum(((b["high"] + b["low"] + b["close"]) / 3) * b["volume"] for b in seg) / vol


def runup(bars: list[dict], n: int = LOOKBACK) -> float:
    if len(bars) < 2:
        return 0.0
    n = min(n, len(bars) - 1)
    prev = bars[-1 - n]["close"]
    return (bars[-1]["close"] / prev - 1) if prev > 0 else 0.0


def absorption_ratio(bars: list[dict], period: int = LOOKBACK,
                     vol_mult: float = 1.5, range_mult: float = 0.6) -> float:
    seg = bars[-period:]
    if len(seg) < 5:
        return 0.0
    avg_v = sum(b["volume"] for b in seg) / len(seg) or 1.0
    avg_r = sum(b["high"] - b["low"] for b in seg) / len(seg) or 1.0
    hits = sum(
        1 for b in seg
        if b["volume"] > vol_mult * avg_v and (b["high"] - b["low"]) < range_mult * avg_r
    )
    return hits / len(seg)


def basing_score(bars: list[dict], period: int = 2 * LOOKBACK) -> float:
    if len(bars) < 10:
        return 0.0
    seg = bars[-period:] if len(bars) >= period else bars
    third = max(1, len(seg) // 3)
    first, last = seg[:third], seg[-third:]
    r1 = max(b["high"] for b in first) - min(b["low"] for b in first)
    r2 = max(b["high"] for b in last) - min(b["low"] for b in last)
    comp = _clamp01(1 - (r2 / r1)) if r1 > 0 else 0.0
    lo1 = min(b["low"] for b in first)
    lo2 = min(b["low"] for b in last)
    higher_low = 1.0 if lo2 >= lo1 else 0.0
    return 0.5 * comp + 0.5 * higher_low


def foreign_consistency(bars: list[dict], n: int = LOOKBACK) -> dict:
    seg = bars[-n:] if len(bars) >= n else bars
    flows = [foreign_flow(b) for b in seg]
    pos = sum(1 for x in flows if x > 0)
    return {
        "ratio": pos / len(flows) if flows else 0.0,
        "net": sum(flows),
        "days": len(flows),
        "pos_days": pos,
    }


# --------------------------------------------------------------------- broker

def broker_signals(payload: Optional[dict], current_close: Optional[float],
                   total_value: float, as_of: Optional[str] = None,
                   lookback: int = LOOKBACK) -> Optional[dict]:
    """Sinyal broker dari payload `/api/broker-accumulation`.

    Dinormalisasi terhadap nilai transaksi (rasio), bukan rupiah mentah.
    Persistensi = jumlah hari net positif dalam N hari.
    """
    if not payload:
        return None
    series = payload.get("series") or []
    rows = []
    for b in series:
        pts = [
            p for p in (b.get("points") or [])
            if not as_of or str(p.get("date")) <= str(as_of)
        ][-lookback:]
        if not pts:
            continue
        pos = sum(1 for p in pts if (_f(p.get("nval")) or 0.0) > 0)
        net = sum((_f(p.get("nval")) or 0.0) for p in pts)
        bavgs = [
            _f(p.get("bavg")) for p in pts
            if (_f(p.get("nval")) or 0.0) > 0 and _f(p.get("bavg"))
        ]
        rows.append({
            "broker_code": b.get("broker_code"),
            "name": b.get("broker_name"),
            "pos_days": pos,
            "days": len(pts),
            "net": net,
            "bavg": bavgs[-1] if bavgs else None,
        })

    buyers = sorted([r for r in rows if r["net"] > 0], key=lambda x: x["net"], reverse=True)[:3]
    if not buyers:
        return None
    base = abs(total_value) if total_value else 0.0
    concentration = _clamp01(sum(r["net"] for r in buyers) / base) if base > 0 else 0.0
    persistence = _clamp01(
        sum(r["pos_days"] for r in buyers) / (len(buyers) * lookback)
    )
    price_vs_buyer_avg = None
    if current_close:
        wsum = sum(r["net"] for r in buyers) or 1.0
        wavg = sum((r["bavg"] or current_close) * r["net"] for r in buyers) / wsum
        if wavg > 0:
            price_vs_buyer_avg = current_close / wavg - 1
    return {
        "top_buyers": buyers,
        "concentration": concentration,
        "persistence": persistence,
        "price_vs_buyer_avg": price_vs_buyer_avg,
    }


# ---------------------------------------------------------------------- score

def _reasons(comp: dict, raw: dict, depth: str, capped: bool) -> list[str]:
    r: list[str] = []
    if comp.get("obv", 0) > 0.6:
        r.append("OBV naik (tekanan beli)")
    if comp.get("ad", 0) > 0.6:
        r.append("garis A/D menguat")
    if comp.get("cmf", 0) > 0.6:
        r.append("Chaikin Money Flow positif")
    if comp.get("absorption", 0) > 0.3:
        r.append("ada penyerapan volume (volume naik, range sempit)")
    if comp.get("basing", 0) > 0.6:
        r.append("harga membentuk basis/mengompresi range")
    if comp.get("vwap", 0) >= 0.99:
        r.append("harga di atas VWAP periodik")
    f = raw.get("foreign") or {}
    if f.get("net", 0) > 0 and f.get("ratio", 0) >= 0.5:
        r.append(f"arus asing beli bersih {f.get('pos_days')}/{f.get('days')} hari")
    b = raw.get("broker")
    if b:
        r.append("broker besar net beli konsisten beberapa hari")
        pv = b.get("price_vs_buyer_avg")
        if pv is not None and abs(pv) <= 0.15:
            r.append("harga masih dekat rata-rata harga pembeli")
    if capped and depth != "broker":
        r.append("skor dibatasi karena belum ada konfirmasi broker besar")
    if not r:
        r.append("sinyal lemah / tidak jelas")
    return r


def evaluate(
    history_rows: list[dict],
    broker_payload: Optional[dict] = None,
    as_of: Optional[str] = None,
    weights: Optional[dict] = None,
    cap_no_broker: float = SCORE_CAP_NO_BROKER,
    min_bars: int = MIN_BARS,
    lookback: int = LOOKBACK,
    max_runup: float = 0.15,
) -> dict:
    """Nilai satu saham. Return dict: rated/score/depth/components/raw_signals/reasons."""
    prep = prepare(history_rows, as_of=as_of, min_bars=min_bars)
    issues = list(prep["issues"])
    if not prep["ok"]:
        return {
            "rated": False, "depth": "none", "score": None,
            "components": {}, "raw_signals": {},
            "reasons": [prep["reason"]] + issues,
        }

    bars, adjusted = adjust_splits(prep["bars"])
    if adjusted:
        issues.append("disesuaikan untuk aksi korporasi (split)")

    ru = runup(bars, lookback)
    if ru > max_runup:
        return {
            "rated": False, "depth": "none", "score": None,
            "components": {}, "raw_signals": {"runup": ru},
            "reasons": [f"sudah naik {ru * 100:.1f}% dalam {lookback} hari (bukan akumulasi awal)"]
            + issues,
        }

    close = bars[-1]["close"]
    seg = bars[-lookback:]
    tot_vol = sum(b["volume"] for b in seg) or 1.0
    obv_s = _delta_ratio(obv_series(bars), lookback, tot_vol)
    ad_s = _delta_ratio(ad_series(bars), lookback, tot_vol)
    cmf_v = cmf(bars, lookback)
    absorp = absorption_ratio(bars, lookback)
    base_s = basing_score(bars, lookback * 2)
    vw = vwap(bars, lookback)
    vwap_pos = None if vw is None else (1.0 if close > vw * (1 + 1e-6) else 0.5)
    fconf = foreign_consistency(bars, lookback)
    total_value = sum(b["value"] for b in bars[-lookback:])
    bsignals = broker_signals(broker_payload, close, total_value, as_of=as_of, lookback=lookback)

    has_foreign = any(
        b.get("f_buy") is not None or b.get("f_sell") is not None or b.get("n_foreign") is not None
        for b in bars[-lookback:]
    )
    depth = "broker" if bsignals else ("foreign" if has_foreign else "hv")

    comp = {
        "obv": 0.5 + 0.5 * math.tanh(obv_s * 3),
        "ad": 0.5 + 0.5 * math.tanh(ad_s * 3),
        "cmf": (cmf_v + 1) / 2,
        "absorption": _clamp01(absorp * 2),
        "basing": base_s,
        "vwap": vwap_pos if vwap_pos is not None else 0.5,
        "foreign": fconf["ratio"] * (1.0 if fconf["net"] > 0 else 0.0),
    }
    if bsignals:
        pv = bsignals["price_vs_buyer_avg"]
        prox = 0.5 if pv is None else _clamp01(1 - abs(pv) / 0.15)
        comp["broker"] = _clamp01(
            0.4 * _ramp(bsignals["concentration"], 0.05, 0.4)
            + 0.4 * bsignals["persistence"]
            + 0.2 * prox
        )

    w = weights or DEFAULT_WEIGHTS
    used = {k: w.get(k, 0.0) for k in comp if w.get(k, 0.0) > 0}
    total_w = sum(used.values())
    raw_score = 50.0 if total_w <= 0 else sum(comp[k] * used[k] for k in used) / total_w * 100.0
    capped = raw_score if depth == "broker" else min(raw_score, cap_no_broker)

    raw_signals = {
        "obv_slope": obv_s, "ad_slope": ad_s, "cmf": cmf_v,
        "absorption_ratio": absorp, "basing": base_s,
        "vwap": vw, "vwap_pos": vwap_pos, "foreign": fconf,
        "broker": bsignals, "total_value": total_value,
        "close": close, "runup": ru, "split_adjusted": adjusted,
    }
    return {
        "rated": True,
        "depth": depth,
        "score": round(capped, 1),
        "raw_score": round(raw_score, 1),
        "capped": raw_score > capped + 1e-9,
        "components": {k: round(v, 4) for k, v in comp.items()},
        "raw_signals": raw_signals,
        "reasons": _reasons(comp, raw_signals, depth, raw_score > capped + 1e-9) + issues,
    }
