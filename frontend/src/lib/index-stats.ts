import type { QuoteData } from "./chat";

export type IndexTone = "up" | "down" | "neutral";

export interface IndexCell {
  key: string;
  label: string;
  value: string;
  tone: IndexTone;
}

export interface IndexTitle {
  ticker: string;
  price: string;
  changeText: string;
  tone: IndexTone;
}

const INDEX_CODES = new Set(["IHSG", "COMPOSITE", "JKSE"]);

export function isIndexTicker(ticker: string): boolean {
  return INDEX_CODES.has((ticker || "").trim().toUpperCase());
}

function num(v: number | null | undefined, digits = 2): string {
  if (v == null || !Number.isFinite(v)) return "-";
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function compactUs(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "-";
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 }) + "B";
  if (a >= 1e6) return (v / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 }) + "M";
  if (a >= 1e3) return (v / 1e3).toLocaleString("en-US", { maximumFractionDigits: 1 }) + "K";
  return num(v, 0);
}

function toneOf(change: number | null | undefined): IndexTone {
  if (change == null) return "neutral";
  if (change > 0) return "up";
  if (change < 0) return "down";
  return "neutral";
}

function signed(v: number | null | undefined, digits = 2): string {
  if (v == null || !Number.isFinite(v)) return "-";
  const sign = v > 0 ? "+" : v < 0 ? "-" : "";
  return `${sign}${Math.abs(v).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export interface IndexStats {
  title: IndexTitle;
  cells: IndexCell[];
}

export function buildIndexStats(ticker: string, quote: QuoteData | null): IndexStats | null {
  if (!quote) return null;
  const tone = toneOf(quote.change);
  return {
    title: {
      ticker,
      price: num(quote.last_price),
      changeText: `${signed(quote.change)} (${signed(quote.change_pct)}%)`,
      tone,
    },
    cells: [
      { key: "prev", label: "Prev", value: num(quote.prev_close), tone: "neutral" },
      { key: "open", label: "Open", value: num(quote.day_open), tone: "neutral" },
      { key: "lot", label: "Lot", value: compactUs(quote.lot), tone: "neutral" },
      { key: "chg", label: "Chg", value: signed(quote.change), tone },
      { key: "high", label: "High", value: num(quote.day_high), tone: "neutral" },
      {
        key: "val",
        label: "Val",
        value: quote.value != null && Number.isFinite(quote.value) ? Math.round(quote.value).toLocaleString("en-US") : "-",
        tone: "neutral",
      },
      {
        key: "pct",
        label: "%",
        value: quote.change_pct != null && Number.isFinite(quote.change_pct) ? `${quote.change_pct.toLocaleString("en-US", { maximumFractionDigits: 2 })}%` : "-",
        tone,
      },
      { key: "low", label: "Low", value: num(quote.day_low), tone: "neutral" },
      { key: "avg", label: "Avg", value: "0", tone: "neutral" },
    ],
  };
}
