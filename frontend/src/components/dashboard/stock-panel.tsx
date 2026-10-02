"use client";

import type { HistoryPoint, QuoteData } from "@/lib/chat";
import { fmtCompact, fmtPct, fmtRp, fmtSigned } from "@/lib/format";

export const PERIODS = ["1D", "1W", "1M", "3M", "YTD", "1Y", "3Y", "5Y"] as const;
export type Period = (typeof PERIODS)[number];
export const ACTIVE_PERIODS: Period[] = ["1D", "1W", "1M", "3M", "YTD", "1Y"];

interface Props {
  ticker: string;
  quote: QuoteData | null;
  series: HistoryPoint[];
  period: Period;
  onPeriod: (p: Period) => void;
  loading: boolean;
  error: string | null;
}

export function StockPanel({
  ticker,
  quote,
  series,
  period,
  onPeriod,
  loading,
  error,
}: Props) {
  const last = series.length ? series[series.length - 1] : null;
  const prev = series.length > 1 ? series[series.length - 2] : null;

  const price = quote?.last_price ?? last?.close ?? null;
  let change: number | null = null;
  let changePct: number | null = null;
  if (last && prev && prev.close) {
    change = last.close - prev.close;
    changePct = (change / prev.close) * 100;
  } else if (last?.change != null) {
    change = last.change;
    changePct = last.change_pct ?? null;
  }

  const down = (change ?? 0) < 0;
  const chgColor = down ? "text-red-400" : "text-emerald-400";

  const vol = last?.volume ?? null;
  const lot = quote?.lot ?? (vol != null ? vol / 100 : null);
  const val = quote?.value ?? last?.value ?? null;

  const periodLabel =
    period === "1D" ? "Today" : period === "YTD" ? "Year to Date" : `Past ${period}`;

  return (
    <div>
      <div className="flex items-baseline gap-2 flex-wrap">
        <span className="text-xl font-bold text-zinc-100">{ticker}</span>
        <span className="text-sm text-zinc-400 truncate max-w-[280px]">
          {quote?.name || (loading ? "Memuat…" : "")}
        </span>
      </div>

      <div className="mt-1 flex items-baseline gap-2 flex-wrap">
        <span className="text-2xl font-bold text-zinc-100">{price != null ? fmtRp(price) : "-"}</span>
        {change != null && (
          <span className={`text-sm font-semibold ${chgColor}`}>
            {down ? "▼" : "▲"} {fmtSigned(change)} ({fmtPct(changePct)})
          </span>
        )}
        <span className="text-xs text-zinc-500">{periodLabel}</span>
        <span className="text-xs text-zinc-500">
          Lot <span className="text-zinc-300 font-medium">{fmtCompact(lot)}</span>
        </span>
        <span className="text-xs text-zinc-500">
          Val <span className="text-zinc-300 font-medium">{fmtCompact(val)}</span>
        </span>
      </div>

      {last && (
        <div className="mt-1 text-xs text-zinc-400 flex gap-3 flex-wrap">
          <span>O <span className="text-zinc-200">{fmtRp(last.open)}</span></span>
          <span>H <span className="text-zinc-200">{fmtRp(last.high)}</span></span>
          <span>L <span className="text-zinc-200">{fmtRp(last.low)}</span></span>
          <span>C <span className="text-zinc-200">{fmtRp(last.close)}</span></span>
          <span>Vol <span className="text-zinc-200">{fmtCompact(last.volume)}</span></span>
        </div>
      )}

      {error && (
        <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs px-3 py-2">
          {error}
        </div>
      )}

      <div className="mt-2 flex items-center gap-1.5 flex-wrap">
        {PERIODS.map((p) => {
          const enabled = ACTIVE_PERIODS.includes(p);
          const on = period === p;
          return (
            <button
              key={p}
              type="button"
              disabled={!enabled}
              onClick={() => onPeriod(p)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                on
                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/50"
                  : enabled
                    ? "text-zinc-400 border border-zinc-700 hover:text-zinc-200 hover:border-zinc-600"
                    : "text-zinc-700 border border-zinc-800 cursor-not-allowed"
              }`}
            >
              {p}
            </button>
          );
        })}
      </div>
    </div>
  );
}
