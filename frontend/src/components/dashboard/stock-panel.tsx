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

  const price = quote?.last_price ?? last?.close ?? null;
  // Change relatif ke awal rentang periode (bukan selalu harian).
  const ref = series.length ? series[0].close : null;
  let change: number | null = null;
  let changePct: number | null = null;
  if (price != null && ref) {
    change = price - ref;
    changePct = (change / ref) * 100;
  } else if (quote?.change != null) {
    change = quote.change;
    changePct = quote.change_pct ?? null;
  } else if (last?.change != null) {
    change = last.change;
    changePct = last.change_pct ?? null;
  }

  const down = (change ?? 0) < 0;
  const chgColor = down ? "text-red-500" : "text-emerald-500";

  // Indeks: quote lot/value = 0 -> ambil dari bar terakhir (agregat pasar).
  const isIndexQuote = (quote?.lot ?? null) === 0 && (quote?.value ?? null) === 0;
  const rawLot = isIndexQuote
    ? last?.volume != null
      ? last.volume / 100
      : null
    : (quote?.lot ?? (last?.volume != null ? last.volume / 100 : null));
  const rawVal = isIndexQuote ? (last?.value ?? null) : (quote?.value ?? last?.value ?? null);
  // Jangan tampilkan "0" bila datanya tidak ada.
  const lot = rawLot === 0 ? null : rawLot;
  const val = rawVal === 0 ? null : rawVal;
  const vol = isIndexQuote ? (last?.volume ?? null) : (quote?.day_volume ?? last?.volume ?? null);
  const o =
    isIndexQuote || quote?.day_open == null ? last?.open : quote.day_open;
  const h =
    isIndexQuote || quote?.day_high == null ? last?.high : quote.day_high;
  const l = isIndexQuote || quote?.day_low == null ? last?.low : quote.day_low;
  const c = isIndexQuote ? last?.close : price;
  const ohlc = last
    ? ([
        ["O", o],
        ["H", h],
        ["L", l],
        ["C", c],
      ] as const)
    : null;

  return (
    <div className="px-4 pt-3">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white shrink-0">
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C9 7 6 9 6 13a6 6 0 0012 0c0-4-3-6-6-11zm-3 14a3 3 0 016 0H9z" />
          </svg>
        </div>
        <div className="min-w-0">
          <div className="text-sm text-text-primary truncate">
            <span className="font-bold">{ticker}</span>{" "}
            <span className="text-text-secondary">
              {quote?.name || (loading ? "Memuat…" : "")}
            </span>
          </div>
          {quote?.market_label && (
            <div className="text-[11px] text-text-muted">{quote.market_label}</div>
          )}
        </div>
      </div>

      <div className="mt-1 flex items-baseline gap-2 flex-wrap">
        <span className="text-[28px] leading-9 font-bold text-text-primary">
          {price != null ? fmtRp(price) : "-"}
        </span>
        {change != null && (
          <span className={`text-sm font-bold ${chgColor}`}>
            {down ? "▼" : "▲"} {fmtRp(Math.abs(change))} ({fmtPct(changePct)})
          </span>
        )}
      </div>

      <div className="mt-0.5 flex items-center gap-2.5 flex-wrap text-xs text-text-secondary">
        <span>{PERIOD_LABEL[period]}</span>
        <span className="text-text-muted">|</span>
        <span>
          Lot <span className="text-text-primary font-bold">{fmtCompact(lot)}</span>
        </span>
        <span>
          Val <span className="text-text-primary font-bold">{fmtCompact(val)}</span>
        </span>
      </div>

      {ohlc && (
        <div className="mt-1.5 flex gap-3.5 flex-wrap text-xs">
          {ohlc.map(([label, v]) => (
            <span key={label}>
              <span className="text-emerald-500">{label} </span>
              <span className="text-text-primary">{v != null ? fmtRp(v) : "-"}</span>
            </span>
          ))}
          <span>
            <span className="text-emerald-500">Vol </span>
            <span className="text-text-primary">{vol != null ? fmtCompact(vol) : "-"}</span>
          </span>
        </div>
      )}

      {error && (
        <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-500 text-xs px-3 py-2">
          {error}
        </div>
      )}
    </div>
  );
}
