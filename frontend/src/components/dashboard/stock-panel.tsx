"use client";

import type { HistoryPoint, QuoteData } from "@/lib/chat";
import { fmtCompact, fmtPct, fmtRp } from "@/lib/format";

export const PERIODS = ["1M", "3M", "YTD", "1Y", "3Y", "5Y"] as const;
export type Period = (typeof PERIODS)[number];
export const ACTIVE_PERIODS: Period[] = ["1M", "3M", "YTD", "1Y"];

const PERIOD_LABEL: Record<Period, string> = {
  "1M": "Past 1 Month",
  "3M": "Past 3 Months",
  YTD: "Year to Date",
  "1Y": "Past 1 Year",
  "3Y": "Past 3 Years",
  "5Y": "Past 5 Years",
};

interface Props {
  ticker: string;
  quote: QuoteData | null;
  series: HistoryPoint[];
  period: Period;
  loading: boolean;
  error: string | null;
}

export function StockPanel({ ticker, quote, series, period, loading, error }: Props) {
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

  return (
    <div className="px-4 pt-3">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white shrink-0">
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C9 7 6 9 6 13a6 6 0 0012 0c0-4-3-6-6-11zm-3 14a3 3 0 016 0H9z" />
          </svg>
        </div>
        <div className="min-w-0">
          <div className="text-sm text-zinc-100 truncate">
            <span className="font-bold">{ticker}</span>{" "}
            <span className="text-zinc-400">
              {quote?.name || (loading ? "Memuat…" : "")}
            </span>
          </div>
          {quote?.market_label && (
            <div className="text-[11px] text-zinc-500">{quote.market_label}</div>
          )}
        </div>
      </div>

      <div className="mt-1 flex items-baseline gap-2 flex-wrap">
        <span className="text-[28px] leading-9 font-bold text-zinc-100">
          {price != null ? fmtRp(price) : "-"}
        </span>
        {change != null && (
          <span className={`text-sm font-bold ${chgColor}`}>
            {down ? "▼" : "▲"} {fmtRp(Math.abs(change))} ({fmtPct(changePct)})
          </span>
        )}
      </div>

      <div className="mt-0.5 flex items-center gap-2.5 flex-wrap text-xs text-zinc-400">
        <span>{PERIOD_LABEL[period]}</span>
        <span className="text-zinc-700">|</span>
        <span>
          Lot <span className="text-zinc-100 font-bold">{fmtCompact(lot)}</span>
        </span>
        <span>
          Val <span className="text-zinc-100 font-bold">{fmtCompact(val)}</span>
        </span>
      </div>

      {last && (
        <div className="mt-1.5 flex gap-3.5 flex-wrap text-xs">
          {(
            [
              ["O", last.open],
              ["H", last.high],
              ["L", last.low],
              ["C", last.close],
            ] as const
          ).map(([label, v]) => (
            <span key={label}>
              <span className="text-emerald-500">{label} </span>
              <span className="text-zinc-100">{fmtRp(v)}</span>
            </span>
          ))}
          <span>
            <span className="text-emerald-500">Vol </span>
            <span className="text-zinc-100">{fmtCompact(last.volume)}</span>
          </span>
        </div>
      )}

      {error && (
        <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs px-3 py-2">
          {error}
        </div>
      )}
    </div>
  );
}
