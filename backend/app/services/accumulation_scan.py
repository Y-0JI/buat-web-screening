"""Orkestrator scan akumulasi — funnel bertingkat hemat kuota.

Single-flight: hanya satu scan berjalan; panggilan berikutnya ditolak (bukan
mengantre). Kuota memakai `x-ratelimit-remaining` terkecil sebagai acuan; bila
belum diketahui, probe ringan dulu, dan berhenti aman bila ragu.
"""

import asyncio
import logging
import re
from datetime import date
from typing import Optional

from app.analysis import accumulation as A
from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider
from app.repositories import accumulation_repository as repo

logger = logging.getLogger(__name__)

_in_progress = False
_DEPTH_RANK = {"broker": 0, "foreign": 1, "hv": 2, "none": 3}


def _provider() -> IdxEdgeProvider:
    return IdxEdgeProvider()


def scan_running() -> bool:
    return _in_progress


def _iso_date(value) -> Optional[str]:
    """Ambil tanggal ISO dari field yang bisa berupa teks tampilan."""
    if not value:
        return None
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
    if not m:
        return None
    try:
        date.fromisoformat(m.group(0))
        return m.group(0)
    except ValueError:
        return None


def _partial(reason: str, **extra) -> dict:
    base = {
        "status": "partial", "signals": [], "checked": [],
        "universe_count": 0, "stage_b_count": 0, "stage_c_count": 0,
        "requests_used": 0, "quota_remaining": None, "note": [reason],
    }
    base.update(extra)
    return base


def _stratify(liquid: list[dict], n: int) -> list[list[dict]]:
    n = max(1, n)
    ordered = sorted(liquid, key=lambda r: r.get("market_cap") or 0, reverse=True)
    if n == 1 or not ordered:
        return [ordered]
    size = max(1, len(ordered) // n)
    groups = [ordered[i * size:(i + 1) * size] for i in range(n)]
    if n * size < len(ordered):
        groups[-1].extend(ordered[n * size:])
    return groups


def _select_candidates(groups, rotation_map, cap, seeds) -> list[dict]:
    per = max(1, cap // max(1, len(groups)))
    out: list[dict] = []
    seen: set[str] = set()
    for s in seeds:
        s = str(s).upper()
        if s and s not in seen:
            seen.add(s)
            out.append({"ticker": s, "stratum": 0})
    for idx, g in enumerate(groups):
        ordered = sorted(
            g, key=lambda r: rotation_map.get(str(r["code"]).upper(), -1)
        )
        for r in ordered[:per]:
            t = str(r["code"]).upper()
            if t and t not in seen:
                seen.add(t)
                out.append({"ticker": t, "stratum": idx})
    return out[:cap]


def _signal(ticker: str, res: dict) -> dict:
    raw = res.get("raw_signals") or {}
    foreign = raw.get("foreign") or {}
    broker = raw.get("broker") or {}
    broker_net = (
        sum(x.get("net") or 0.0 for x in broker.get("top_buyers", []))
        if broker else None
    )
    return {
        "ticker": ticker,
        "score": res.get("score"),
        "depth": res.get("depth"),
        "components": {"raw": raw, "norm": res.get("components")},
        "reasons": "; ".join(res.get("reasons") or []),
        "close": raw.get("close"),
        "foreign_net": foreign.get("net"),
        "broker_net": broker_net,
        "broker_checked": bool(raw.get("broker_checked")),
        "broker_confirmed": bool(raw.get("broker_confirmed")),
    }


async def prepare_scan(force: bool = False) -> dict:
    """Probe ringan untuk tanggal data + cek idempotensi + buat baris 'running'.

    market-cap memuat `date` ISO (sumber tanggal andal); screener menyediakan seed.
    """
    provider = _provider()
    mc = await provider.fetch_market_cap(page=1, per_page=1)
    screener = await provider.fetch_screener()
    data_date = _iso_date((mc or {}).get("date")) or _iso_date((screener or {}).get("date"))
    if not data_date:
        return {"ok": False, "reason": "tanggal data tidak diketahui", "screener": screener}

    existing = await repo.get_scan_by_date(date.fromisoformat(data_date))
    if existing and existing["status"] == "complete" and not force:
        return {
            "ok": False, "skipped": True, "scan_id": existing["id"],
            "scan_date": data_date, "reason": "scan complete sudah ada",
        }

    created = await repo.save_scan(
        date.fromisoformat(data_date), "running", note="scan berjalan", force=True
    )
    return {
        "ok": True, "scan_id": created["id"], "scan_date": data_date,
        "screener": screener,
        # request yang dipakai tahap persiapan (probe market-cap + screener) agar
        # ikut dihitung di requests_used total.
        "prep_requests": provider.calls_today,
    }


async def begin_scan(force: bool = False) -> dict:
    """Coba mulai scan. Menahan lock (flag) bila berhasil; pemanggil wajib lanjut."""
    global _in_progress
    if _in_progress:
        return {"ok": False, "busy": True}
    _in_progress = True
    try:
        prep = await prepare_scan(force)
    except Exception as e:  # noqa: BLE001
        _in_progress = False
        logger.warning("prepare_scan gagal: %s", e)
        return {"ok": False, "error": str(e)}
    if not prep.get("ok"):
        _in_progress = False
    return prep


async def run_funnel(data_date: str, screener: Optional[dict]) -> dict:
    provider = _provider()
    start_calls = provider.calls_today
    reserve = settings.accumulation_quota_reserve
    weights = settings.accumulation_weights
    cap = settings.accumulation_score_cap_no_broker
    mb = A.MIN_BARS
    lb = A.LOOKBACK
    hist_bars = min(settings.accumulation_history_bars, settings.accumulation_max_history_limit)
    note: list[str] = []
    status = "complete"

    def quota_low() -> bool:
        q = provider.quota_remaining()
        return q is not None and q <= reserve

    # Kuota harus diketahui; bila belum, probe market-cap halaman 1 (health tidak
    # mengirim header kuota). Respons probe dipakai ulang sebagai halaman 1 Tahap A
    # sehingga tidak dihitung dua kali. Jangan menebak.
    probe_page = None
    if provider.quota_remaining() is None:
        probe_page = await provider.fetch_market_cap(page=1, per_page=50)
        if provider.quota_remaining() is None:
            return _partial("kuota tidak diketahui (probe gagal)")
    if quota_low():
        return _partial("sisa kuota di bawah reserve sebelum mulai")

    seeds = [
        str(r.get("stock_code")).upper()
        for r in (screener or {}).get("rows") or []
        if r.get("stock_code")
    ]

    # Tahap A — market-cap penuh + seed screener + rotasi per strata.
    mc = await provider.fetch_market_cap_all(max_pages=25, first_page=probe_page)
    liquid = [
        r for r in mc
        if (r.get("market_cap") or 0) >= settings.accumulation_market_cap_min
    ]
    groups = _stratify(liquid, settings.accumulation_rotation_strata)
    rotation = await repo.get_rotation_map([str(r["code"]).upper() for r in liquid])
    cap_candidates = min(settings.accumulation_history_limit, settings.accumulation_max_history_limit)
    candidates = _select_candidates(groups, rotation, cap_candidates, seeds)

    # Tahap B — history untuk kandidat (konkurensi terbatas).
    sem = asyncio.Semaphore(5)
    checked: list[dict] = []
    bconf = settings.accumulation_broker_confirm_min
    reasons_count = {"not_rated": 0, "runup": 0, "thin": 0, "failed": 0}

    async def hv(item: dict) -> Optional[dict]:
        async with sem:
            if quota_low():
                return None
            ticker = item["ticker"]
            rows = await provider.fetch_history(ticker, limit=hist_bars)
            checked.append(item)
            if not rows:
                reasons_count["failed"] += 1
                return {"ticker": ticker, "failed": True}
            prep = A.prepare(rows, as_of=data_date, min_bars=mb)
            if not prep["ok"]:
                reason = prep["reason"] or "tidak dinilai"
                if str(reason).startswith("sudah naik"):
                    reasons_count["runup"] += 1
                else:
                    reasons_count["not_rated"] += 1
                return {"ticker": ticker, "not_rated": reason}
            window = prep["bars"][-lb:]
            avg_value = sum(b["value"] for b in window) / max(1, len(window))
            if avg_value < settings.accumulation_min_daily_value:
                reasons_count["thin"] += 1
                return {"ticker": ticker, "thin": True}
            res = A.evaluate(
                rows, as_of=data_date, weights=weights, cap_no_broker=cap,
                min_bars=mb, lookback=lb, max_runup=settings.accumulation_max_runpct,
                broker_confirm_min=bconf,
            )
            if not res["rated"]:
                reason = (res["reasons"] or ["tidak dinilai"])[0]
                if str(reason).startswith("sudah naik"):
                    reasons_count["runup"] += 1
                else:
                    reasons_count["not_rated"] += 1
                return {"ticker": ticker, "not_rated": reason}
            return {"ticker": ticker, "stratum": item["stratum"], "res": res, "rows": rows}

    raw = await asyncio.gather(*(hv(c) for c in candidates))
    stage_b = [r for r in raw if r and r.get("res")]
    stage_b.sort(key=lambda x: x["res"]["score"], reverse=True)
    note.append(
        f"Tahap B: {len(stage_b)} lolos dari {len(candidates)} "
        f"(tidak dinilai {reasons_count['not_rated']}, sudah lari {reasons_count['runup']}, "
        f"likuiditas tipis {reasons_count['thin']}, gagal data {reasons_count['failed']})"
    )

    # Tahap C — broker untuk top kandidat.
    final: dict[str, dict] = {x["ticker"]: x for x in stage_b}
    stage_c = 0
    broker_confirmed = 0
    for x in stage_b[:settings.accumulation_broker_limit]:
        if quota_low():
            status = "partial"
            note.append("kuota menipis di Tahap C")
            break
        brok = await provider.fetch_broker_accumulation(x["ticker"])
        res2 = A.evaluate(
            x["rows"], broker_payload=brok, as_of=data_date, weights=weights,
            cap_no_broker=cap, min_bars=mb, lookback=lb,
            max_runup=settings.accumulation_max_runpct,
            broker_confirm_min=bconf,
        )
        if res2["rated"]:
            final[x["ticker"]] = {"ticker": x["ticker"], "stratum": x["stratum"], "res": res2}
            stage_c += 1
            if res2.get("broker_confirmed"):
                broker_confirmed += 1
    note.append(f"Tahap C: {stage_c} dicek broker, {broker_confirmed} mengonfirmasi")

    signals = [_signal(t, item["res"]) for t, item in final.items()]
    signals.sort(
        key=lambda s: (_DEPTH_RANK.get(s["depth"], 3), -(s["score"] or 0))
    )

    if quota_low() and status == "complete":
        status = "partial"
        note.append("kuota mendekati reserve saat berakhir")

    return {
        "status": status,
        "signals": signals,
        "checked": checked,
        "universe_count": len(candidates),
        "stage_b_count": len(stage_b),
        "stage_c_count": stage_c,
        "requests_used": provider.calls_today - start_calls,
        "quota_remaining": provider.quota_remaining(),
        "note": note,
    }


async def continue_scan(prep: dict, force: bool = False) -> None:
    """Jalankan funnel & simpan hasil. Selalu melepas single-flight."""
    global _in_progress
    try:
        data_date = prep["scan_date"]
        result = await run_funnel(data_date, prep.get("screener"))
        # Total request = persiapan + funnel (retry/probe apa pun yang lewat
        # provider sudah ikut terhitung di provider masing-masing).
        result["requests_used"] = result.get("requests_used", 0) + prep.get("prep_requests", 0)
        saved = await repo.save_scan(
            date.fromisoformat(data_date), result["status"],
            universe_count=result["universe_count"],
            stage_b_count=result["stage_b_count"],
            stage_c_count=result["stage_c_count"],
            requests_used=result["requests_used"],
            quota_remaining=result["quota_remaining"],
            note="; ".join(result["note"]) or None,
            signals=result["signals"],
            force=True,
        )
        if result.get("checked"):
            await repo.upsert_rotation(result["checked"], saved["id"])
    except Exception as e:  # noqa: BLE001
        logger.exception("scan akumulasi gagal")
        try:
            await repo.save_scan(
                date.fromisoformat(prep["scan_date"]), "partial",
                note=f"gagal: {e}", force=True,
            )
        except Exception:  # noqa: BLE001
            pass
    finally:
        _in_progress = False
