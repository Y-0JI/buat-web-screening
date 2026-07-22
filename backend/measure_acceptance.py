"""Pengukuran empiris Acceptance Criteria 16.4.x (bukan bagian test CI).

Jalan via `python3 measure_acceptance.py`. Menembak provider NYATA (Yahoo/IDX)
untuk mengukur:
  #1 % ticker sukses (df ada & bukan simulasi)
  #3 latency cache MISS (panggilan pertama)  <10s
  #2 latency cache HIT  (panggilan kedua)    <2s
  #4 error rate                               <2%
Sampel ticker likuid IDX. Hasil diringkas + verdict per kriteria.
"""

import asyncio
import time

from app.services import stock_service
from app.repositories.technical_cache import calculate_score_cached
from app.cache.service import cache_service

SAMPLE = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ICBP",
    "INDF", "GGRM", "HMSP", "KLBF", "ADRO", "ANTM", "PTBA", "PGAS",
    "SMGR", "INTP", "CPIN", "JPFA", "AKRA", "EXCL", "TOWR", "TBIG",
    "BRIS", "ARTO", "MDKA", "INCO", "ITMG", "UNTR", "AMRT", "MAPI",
    "ACES", "ERAA", "BUKA", "GOTO", "EMTK", "TINS", "WIKA", "PTPP",
]


async def _measure_one(ticker: str):
    """Return dict: ok, simulated, err, t_miss, t_hit."""
    rec = {"ticker": ticker, "ok": False, "simulated": None,
           "err": None, "t_miss": None, "t_hit": None}
    try:
        await cache_service.clear("price")
        t0 = time.perf_counter()
        df, sim = await stock_service.get_price(ticker)
        rec["t_miss"] = time.perf_counter() - t0

        t1 = time.perf_counter()
        df2, sim2 = await stock_service.get_price(ticker)
        rec["t_hit"] = time.perf_counter() - t1

        rec["simulated"] = bool(sim)
        rec["ok"] = df is not None and not df.empty and not sim
    except Exception as e:  # noqa: BLE001
        rec["err"] = f"{type(e).__name__}: {e}"
    return rec


async def main():
    print(f"Mengukur {len(SAMPLE)} ticker (provider nyata)...\n")
    results = []
    for t in SAMPLE:
        r = await _measure_one(t)
        results.append(r)
        flag = "OK " if r["ok"] else ("SIM" if r["simulated"] else "ERR")
        miss = f"{r['t_miss']:.2f}s" if r["t_miss"] is not None else "-"
        hit = f"{r['t_hit']:.3f}s" if r["t_hit"] is not None else "-"
        print(f"  [{flag}] {t:5s} miss={miss:>7} hit={hit:>7} "
              f"{r['err'] or ''}")

    n = len(results)
    ok = sum(1 for r in results if r["ok"])
    errs = sum(1 for r in results if r["err"])
    sims = sum(1 for r in results if r["simulated"] and not r["err"])
    miss_times = [r["t_miss"] for r in results if r["t_miss"] is not None]
    hit_times = [r["t_hit"] for r in results if r["t_hit"] is not None]

    pct_ok = 100 * ok / n
    pct_err = 100 * errs / n
    max_miss = max(miss_times) if miss_times else 0
    max_hit = max(hit_times) if hit_times else 0
    avg_miss = sum(miss_times) / len(miss_times) if miss_times else 0
    avg_hit = sum(hit_times) / len(hit_times) if hit_times else 0

    def verdict(cond):
        return "LULUS" if cond else "GAGAL"

    print("\n" + "=" * 56)
    print("RINGKASAN ACCEPTANCE CRITERIA 16.4.x")
    print("=" * 56)
    print(f"#1 Ticker sukses  : {ok}/{n} = {pct_ok:.1f}%  "
          f"(simulasi={sims}, error={errs})   "
          f"[{verdict(pct_ok >= 95)}] target >=95%")
    print(f"#2 Cache HIT      : max={max_hit:.3f}s avg={avg_hit:.3f}s  "
          f"[{verdict(max_hit < 2)}] target <2s")
    print(f"#3 Cache MISS     : max={max_miss:.2f}s avg={avg_miss:.2f}s  "
          f"[{verdict(max_miss < 10)}] target <10s")
    print(f"#4 Error rate     : {pct_err:.1f}%  "
          f"[{verdict(pct_err < 2)}] target <2%")
    print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
