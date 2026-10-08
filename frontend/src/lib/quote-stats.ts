import type { QuoteData } from "./chat";
import { fmtCompact, fmtRp } from "./format";

export type StatTone = "up" | "down" | "neutral";

export interface QuoteStat {
  key: string;
  label: string;
  value: string;
  tone: StatTone;
}

function toneVs(value: number | null | undefined, ref: number | null | undefined): StatTone {
  if (value == null || ref == null) return "neutral";
  if (value > ref) return "up";
  if (value < ref) return "down";
  return "neutral";
}

export function buildQuoteStats(quote: QuoteData | null): QuoteStat[] {
  if (!quote) return [];
  const prev = quote.prev_close ?? null;
  return [
    { key: "open", label: "Open", value: fmtRp(quote.day_open), tone: toneVs(quote.day_open, prev) },
    { key: "high", label: "High", value: fmtRp(quote.day_high), tone: toneVs(quote.day_high, prev) },
    { key: "low", label: "Low", value: fmtRp(quote.day_low), tone: toneVs(quote.day_low, prev) },
    { key: "prev", label: "Prev", value: fmtRp(prev), tone: "neutral" },
    { key: "lot", label: "Lot", value: fmtCompact(quote.lot), tone: "neutral" },
    { key: "value", label: "Val", value: fmtCompact(quote.value), tone: "neutral" },
    { key: "avg", label: "Avg", value: fmtRp(quote.avg), tone: toneVs(quote.avg, prev) },
    {
      key: "freq",
      label: "Freq",
      value: quote.freq != null ? Math.round(quote.freq).toLocaleString("id-ID") : "-",
      tone: "neutral",
    },
    { key: "fbuy", label: "F Buy", value: fmtCompact(quote.f_buy_value), tone: quote.f_buy_value ? "up" : "neutral" },
    { key: "fsell", label: "F Sell", value: fmtCompact(quote.f_sell_value), tone: quote.f_sell_value ? "down" : "neutral" },
    { key: "ara", label: "ARA", value: "-", tone: "neutral" },
    { key: "arb", label: "ARB", value: "-", tone: "neutral" },
  ];
}
