"use client";

import { useEffect, useState } from "react";
import { getSeasonality, type SeasonalityData } from "@/lib/chat";

const cache = new Map<string, SeasonalityData | null>();

function cellColor(v: number | null | undefined): string {
  if (v == null) return "text-text-muted";
  return v >= 0 ? "text-emerald-500" : "text-red-500";
}

export function SeasonalityPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<SeasonalityData | null | undefined>(() =>
    cache.has(ticker) ? cache.get(ticker) ?? null : undefined
  );
  const [error, setError] = useState<string | null>(null);
  const stats = data?.monthly_stats ?? [];

  useEffect(() => {
    if (cache.has(ticker)) {
      setData(cache.get(ticker) ?? null);
      setError(null);
      return;
    }
    let cancelled = false;
    setData(undefined);
    setError(null);
    void (async () => {
      try {
        const res = await getSeasonality(ticker);
        cache.set(ticker, res);
        if (cancelled) return;
        setData(res);
        if (!res) setError(`Data seasonality ${ticker} tidak tersedia.`);
      } catch {
        if (!cancelled) setError("Gagal memuat seasonality. Periksa koneksi backend.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return (
    <div className="mt-2">
      {data === undefined && !error ? (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          Memuat seasonality…
        </div>
      ) : error || !data ? (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          {error || `Data seasonality tidak tersedia.`}
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-2.5">
          {data.summary && (
            <p className="mb-2 text-xs text-text-secondary leading-relaxed">{data.summary}</p>
          )}
          {stats.length > 0 && (
            <div className="mb-3">
              <div className="text-[11px] font-semibold text-text-secondary mb-1">
                Statistik per bulan
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="text-text-muted">
                      <td className="py-1 pr-2 font-semibold">Bulan</td>
                      <td className="py-1 px-2 text-right font-semibold">Rata-rata</td>
                      <td className="py-1 px-2 text-right font-semibold">Naik</td>
                      <td className="py-1 px-2 text-right font-semibold">Turun</td>
                      <td className="py-1 px-2 text-right font-semibold">Total</td>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {stats.map((s) => (
                      <tr key={s.month}>
                        <td className="py-1 pr-2 text-text-muted">{s.month}</td>
                        <td className={`py-1 px-2 text-right tabular-nums ${cellColor(s.avg)}`}>
                          {s.avg == null ? "-" : `${s.avg.toFixed(2)}%`}
                        </td>
                        <td className="py-1 px-2 text-right tabular-nums text-emerald-500">{s.up ?? "-"}</td>
                        <td className="py-1 px-2 text-right tabular-nums text-red-500">{s.down ?? "-"}</td>
                        <td className="py-1 px-2 text-right tabular-nums text-text-primary">{s.total ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-text-muted">
                  <td className="py-1.5 pr-2 font-semibold">Bulan</td>
                  {data.years.map((y) => (
                    <td key={y} className="py-1.5 px-2 text-right font-semibold">
                      {y}
                    </td>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {data.months.map((m) => (
                  <tr key={m}>
                    <td className="py-1.5 pr-2 text-text-muted">{m}</td>
                    {data.years.map((y) => {
                      const v = data.monthly_returns?.[m]?.[y] ?? null;
                      return (
                        <td
                          key={y}
                          className={`py-1.5 px-2 text-right tabular-nums ${cellColor(v)}`}
                        >
                          {v == null ? "-" : `${v.toFixed(2)}%`}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.yearly_avg != null && (
            <p className="mt-2 text-[11px] text-text-secondary">
              Rata-rata tahunan:{" "}
              <span className={`font-semibold tabular-nums ${cellColor(data.yearly_avg)}`}>
                {data.yearly_avg.toFixed(2)}%
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
