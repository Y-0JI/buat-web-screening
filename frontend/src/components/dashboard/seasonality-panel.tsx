"use client";

import { useEffect, useState } from "react";
import { getSeasonality, type SeasonalityData } from "@/lib/chat";
import {
  buildSeasonalityTable,
  type SeasonalityTable,
} from "./seasonality-table";

const cache = new Map<string, SeasonalityData | null>();

function returnTone(v: number | null): string {
  if (v == null) return "bg-surface-2/40 text-text-muted";
  if (v > 0) return "bg-emerald-500 text-white";
  if (v < 0) return "bg-red-500 text-white";
  return "bg-surface-2 text-text-muted";
}

function probTone(v: number | null): string {
  if (v == null || v <= 0) return "bg-surface-2/40 text-text-muted";
  return v >= 50 ? "bg-emerald-500 text-white" : "bg-red-500 text-white";
}

function pct(v: number | null): string {
  return v == null ? "-" : v.toFixed(2);
}

function count(v: number | null): string {
  return v == null ? "-" : String(Math.round(v));
}

function prob(v: number | null): string {
  return v == null ? "-" : `${Math.round(v)}%`;
}

const CELL = "border border-border/60 px-1 py-1 text-right tabular-nums";
const LABEL =
  "sticky left-0 z-10 bg-surface-1 px-2 py-1 text-left font-medium text-text-secondary whitespace-nowrap";

export function SeasonalityPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<SeasonalityData | null | undefined>(() =>
    cache.has(ticker) ? cache.get(ticker) ?? null : undefined
  );
  const [error, setError] = useState<string | null>(null);

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

  if (data === undefined && !error) {
    return (
      <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
        Memuat seasonality…
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
        {error || "Data seasonality tidak tersedia."}
      </div>
    );
  }

  return <Matrix data={data} />;
}

function Matrix({ data }: { data: SeasonalityData }) {
  const t: SeasonalityTable = buildSeasonalityTable(data);

  if (t.rows.length === 0) {
    return (
      <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
        Data seasonality tidak tersedia.
      </div>
    );
  }

  return (
    <div className="mt-2 rounded-lg border border-border bg-surface-1 p-2.5">
      {data.summary && (
        <p className="mb-2 text-xs leading-relaxed text-text-secondary">
          {data.summary}
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-text-muted">
              <th scope="col" className={LABEL}>
                Bulan
              </th>
              {t.months.map((m) => (
                <th key={m} scope="col" className="px-1 py-1 text-right font-medium">
                  {m}
                </th>
              ))}
              <th scope="col" className="px-2 py-1 text-right font-semibold">
                Year
              </th>
            </tr>
          </thead>
          <tbody>
            {t.hasStats && (
              <tr className="border-t border-border">
                <th scope="row" className={LABEL}>
                  Average
                </th>
                {t.average.map((v, i) => (
                  <td key={i} className={`${CELL} ${returnTone(v)}`}>
                    {pct(v)}
                  </td>
                ))}
                <td className={`${CELL} font-semibold ${returnTone(t.averageTotal)}`}>
                  {pct(t.averageTotal)}
                </td>
              </tr>
            )}

            {t.rows.map((r) => (
              <tr key={r.year} className="border-t border-border/60">
                <th scope="row" className={LABEL}>
                  {r.year}
                </th>
                {r.cells.map((v, i) => (
                  <td key={i} className={`${CELL} ${returnTone(v)}`}>
                    {pct(v)}
                  </td>
                ))}
                <td className={`${CELL} font-semibold ${returnTone(r.total)}`}>
                  {pct(r.total)}
                </td>
              </tr>
            ))}

            {t.hasStats && (
              <>
                <tr className="border-t border-border">
                  <th scope="row" className={LABEL}>
                    Up
                  </th>
                  {t.up.map((v, i) => (
                    <td key={i} className={`${CELL} text-emerald-500`}>
                      {count(v)}
                    </td>
                  ))}
                  <td className={`${CELL} font-semibold text-emerald-500`}>
                    {count(t.annualUp)}
                  </td>
                </tr>
                <tr>
                  <th scope="row" className={LABEL}>
                    Down
                  </th>
                  {t.down.map((v, i) => (
                    <td key={i} className={`${CELL} text-red-500`}>
                      {count(v)}
                    </td>
                  ))}
                  <td className={`${CELL} font-semibold text-red-500`}>
                    {count(t.annualDown)}
                  </td>
                </tr>
                <tr>
                  <th scope="row" className={LABEL}>
                    Total
                  </th>
                  {t.total.map((v, i) => (
                    <td key={i} className={`${CELL} text-text-primary`}>
                      {count(v)}
                    </td>
                  ))}
                  <td className={`${CELL} font-semibold text-text-primary`}>
                    {count(t.annualTotal)}
                  </td>
                </tr>
                <tr>
                  <th scope="row" className={LABEL}>
                    Up Probability
                  </th>
                  {t.upProb.map((v, i) => (
                    <td key={i} className={`${CELL} ${probTone(v)}`}>
                      {prob(v)}
                    </td>
                  ))}
                  <td className={`${CELL} font-semibold ${probTone(t.annualUpProb)}`}>
                    {prob(t.annualUpProb)}
                  </td>
                </tr>
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}