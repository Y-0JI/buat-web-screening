"use client";

import { Card } from "@/components/ui";
import type { Fundamentals } from "@/lib/api";

function fmtCurrency(value?: number | null): string | null {
  if (value == null || typeof value !== "number") return null;
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}Rp ${(abs / 1e12).toFixed(2)} T`;
  if (abs >= 1e9) return `${sign}Rp ${(abs / 1e9).toFixed(2)} M`;
  if (abs >= 1e6) return `${sign}Rp ${(abs / 1e6).toFixed(2)} Jt`;
  return `${sign}Rp ${abs.toLocaleString("id-ID")}`;
}

function fmtRatio(value?: number | null): string | null {
  if (value == null || typeof value !== "number") return null;
  return `${value.toFixed(2)}x`;
}

function fmtPercent(value?: number | null): string | null {
  if (value == null || typeof value !== "number") return null;
  const pct = Math.abs(value) <= 1 ? value * 100 : value;
  return `${pct.toFixed(2)}%`;
}

function fmtNumber(value?: number | null): string | null {
  if (value == null || typeof value !== "number") return null;
  return value.toLocaleString("id-ID");
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-800 rounded-lg px-3 py-2">
      <div className="text-zinc-500 text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-zinc-200 text-sm mt-0.5 break-words">{value}</div>
    </div>
  );
}

export function FundamentalCard({ data }: { data: Fundamentals }) {
  if (!data || data.error) return null;

  const rows: Array<[string, string | null]> = [
    ["Market Cap", fmtCurrency(data.market_cap)],
    ["Enterprise Value", fmtCurrency(data.enterprise_value)],
    ["P/E", fmtRatio(data.pe)],
    ["Forward P/E", fmtRatio(data.forward_pe)],
    ["P/BV", fmtRatio(data.pbv ?? data.pb)],
    ["PEG", fmtRatio(data.peg)],
    ["EPS", fmtCurrency(data.eps)],
    ["ROE", fmtPercent(data.roe)],
    ["ROA", fmtPercent(data.roa)],
    ["Revenue", fmtCurrency(data.revenue)],
    ["Revenue Growth", fmtPercent(data.revenue_growth)],
    ["Net Income", fmtCurrency(data.net_income)],
    ["Gross Margin", fmtPercent(data.gross_margin)],
    ["Operating Margin", fmtPercent(data.operating_margin)],
    ["Debt to Equity", fmtRatio(data.debt_to_equity)],
    ["Current Ratio", fmtRatio(data.current_ratio)],
    ["Free Cash Flow", fmtCurrency(data.free_cash_flow)],
    ["Dividend Yield", fmtPercent(data.dividend_yield)],
    ["Dividend Payout", fmtPercent(data.dividend_payout_ratio)],
    ["Shares Outstanding", fmtNumber(data.shares_outstanding)],
  ];

  const shown = rows.filter(([, v]) => v != null) as Array<[string, string]>;
  if (shown.length === 0) return null;

  return (
    <Card padding="md">
      <div className="flex items-center gap-2 mb-3">
        <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <h3 className="text-sm font-semibold text-zinc-300">Fundamental</h3>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {shown.map(([label, value]) => (
          <Field key={label} label={label} value={value} />
        ))}
      </div>
    </Card>
  );
}
