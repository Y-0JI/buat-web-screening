"use client";

import type { QuoteData } from "@/lib/chat";
import { buildIndexStats, type IndexTone } from "@/lib/index-stats";

const TONE_TEXT: Record<IndexTone, string> = {
  up: "text-emerald-500",
  down: "text-red-500",
  neutral: "text-text-primary",
};

interface Props {
  ticker: string;
  quote: QuoteData | null;
}

export function IndexQuoteStrip({ ticker, quote }: Props) {
  const stats = buildIndexStats(ticker, quote);
  if (!stats) return null;
  const { title, cells } = stats;

  return (
    <section className="px-4 pt-2">
      <div className={`text-sm font-bold ${TONE_TEXT[title.tone]}`}>
        {title.ticker} <span className="tabular-nums">{title.price}</span>{" "}
        <span className="tabular-nums">{title.changeText}</span>
      </div>
      <dl className="mt-1 grid grid-cols-3 gap-x-4 gap-y-0.5 text-xs">
        {cells.map((c) => (
          <div key={c.key} className="flex items-baseline gap-2">
            <dt className="shrink-0 text-text-muted">{c.label}</dt>
            <dd className={`ml-auto tabular-nums ${TONE_TEXT[c.tone]}`}>{c.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
