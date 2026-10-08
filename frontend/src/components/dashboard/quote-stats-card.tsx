"use client";

import { useMemo } from "react";
import type { HistoryPoint, QuoteData } from "@/lib/chat";
import { fmtPct, fmtRp } from "@/lib/format";
import { buildIndexStats } from "@/lib/index-stats";
import { buildQuoteStats, type StatTone } from "@/lib/quote-stats";

const TONE_TEXT: Record<StatTone, string> = {
  up: "text-emerald-500",
  down: "text-red-500",
  neutral: "text-text-primary",
};

const TONE_BG: Record<StatTone, string> = {
  up: "bg-emerald-500/10",
  down: "bg-red-500/10",
  neutral: "bg-surface-2/50",
};

function Sparkline({ points, up }: { points: HistoryPoint[]; up: boolean }) {
  const d = useMemo(() => {
    if (points.length < 2) return "";
    const closes = points.map((p) => p.close);
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const span = max - min || 1;
    return points
      .map((p, i) => {
        const x = (i / (points.length - 1)) * 100;
        const y = 36 - ((p.close - min) / span) * 36;
        return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
  }, [points]);

  if (!d) return null;
  const color = up ? "#22c55e" : "#ef4444";
  return (
    <svg viewBox="0 0 100 36" preserveAspectRatio="none" className="w-full h-10" aria-hidden>
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

interface Props {
  ticker: string;
  quote: QuoteData | null;
  series: HistoryPoint[];
  index?: boolean;
}

export function QuoteStatsCard({ ticker, quote, series, index }: Props) {
  const stats = index
    ? (buildIndexStats(ticker, quote)?.cells ?? [])
    : buildQuoteStats(quote);
  if (!quote || !stats.length) return null;

  const up = (quote.change ?? 0) >= 0;
  return (
    <section className="mx-4 mt-2 rounded-2xl border border-border bg-surface-1/60 backdrop-blur p-3">
      <div className="grid grid-cols-1 sm:grid-cols-[minmax(150px,200px)_1fr] gap-3 items-stretch">
        <div className="rounded-xl bg-surface-2/60 p-3 flex flex-col">
          <div className="text-lg font-bold text-text-primary">{ticker}</div>
          <Sparkline points={series} up={up} />
          <div className="mt-1 text-3xl font-bold text-text-primary leading-tight tabular-nums">
            {quote.last_price != null ? fmtRp(quote.last_price) : "-"}
          </div>
          {quote.change != null && (
            <div className={`text-sm font-bold ${up ? "text-emerald-500" : "text-red-500"}`}>
              {quote.change >= 0 ? "+" : ""}
              {fmtRp(quote.change)} ({fmtPct(quote.change_pct)})
            </div>
          )}
        </div>

        <div className={`grid gap-2 ${index ? "grid-cols-3" : "grid-cols-2 md:grid-cols-4"}`}>
          {stats.map((s) => (
            <div key={s.key} className={`rounded-lg px-2.5 py-2 ${TONE_BG[s.tone]}`}>
              <div className="text-[10px] uppercase tracking-wide text-text-muted">{s.label}</div>
              <div className={`text-sm font-bold tabular-nums ${TONE_TEXT[s.tone]}`}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
