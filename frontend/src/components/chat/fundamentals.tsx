"use client";

import type { FundamentalData } from "@/lib/chat";

function big(v: number | null): string | null {
  if (v == null) return null;
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(2) + " T";
  if (a >= 1e9) return (v / 1e9).toFixed(2) + " B";
  if (a >= 1e6) return (v / 1e6).toFixed(1) + " M";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + " K";
  return v.toFixed(0);
}

function rp(v: number | null): string | null {
  return v == null ? null : Math.round(v).toLocaleString("id-ID");
}

function num(v: number | null, d = 2): string | null {
  return v == null ? null : v.toFixed(d);
}

function pct(v: number | null): string | null {
  return v == null ? null : `${v.toFixed(2)}%`;
}

interface RowItem {
  label: string;
  value: string | null;
}

function Panel({ title, rows }: { title: string; rows: RowItem[] }) {
  const visible = rows.filter((r) => r.value != null);
  if (!visible.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface-0/40 px-3 py-2">
      <div className="text-[11px] font-semibold text-text-secondary mb-1.5">{title}</div>
      <div className="space-y-1">
        {visible.map((r) => (
          <div key={r.label} className="flex justify-between gap-3 text-[11px]">
            <span className="text-text-muted">{r.label}</span>
            <span className="text-text-primary tabular-nums">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FundamentalsCard({ data }: { data: FundamentalData }) {
  const { valuation: v, income: inc, balance: bal, cashflow: cf, per_share: ps, profitability: pr, solvency: sol, growth: g } = data;

  return (
    <div className="my-2 rounded-xl border border-border bg-surface-1/40 p-3 text-text-primary">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-semibold">
          Fundamental <span className="text-text-secondary">{data.ticker}</span>
        </div>
        {data.as_of && <span className="text-[11px] text-text-muted">{data.as_of}</span>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <Panel
          title="Valuation"
          rows={[
            { label: "Market Cap", value: big(v.market_cap) },
            { label: "PE (TTM)", value: num(v.pe) },
            { label: "PBV", value: num(v.pbv) },
            { label: "PSR", value: num(v.psr) },
            { label: "Earnings Yield", value: pct(v.earnings_yield) },
          ]}
        />
        <Panel
          title="Income Statement (TTM)"
          rows={[
            { label: "Revenue", value: big(inc.revenue) },
            { label: "Gross Profit", value: big(inc.gross_profit) },
            { label: "Operating Profit", value: big(inc.operating_profit) },
            { label: "Net Income", value: big(inc.net_income) },
          ]}
        />
        <Panel
          title="Balance Sheet (Latest)"
          rows={[
            { label: "Total Assets", value: big(bal.total_assets) },
            { label: "Total Liabilities", value: big(bal.total_liabilities) },
            { label: "Total Equity", value: big(bal.total_equity) },
            { label: "Cash & Equivalents", value: big(bal.cash) },
          ]}
        />
        <Panel
          title="Cash Flow (TTM)"
          rows={[
            { label: "Operating", value: big(cf.operating) },
            { label: "Investing", value: big(cf.investing) },
            { label: "Financing", value: big(cf.financing) },
            { label: "Free Cash Flow", value: big(cf.free_cash_flow) },
          ]}
        />
        <Panel
          title="Per Share"
          rows={[
            { label: "EPS (TTM)", value: rp(ps.eps) },
            { label: "Book Value / Share", value: rp(ps.book_value) },
            { label: "Revenue / Share", value: rp(ps.revenue) },
          ]}
        />
        <Panel
          title="Profitability"
          rows={[
            { label: "Gross Margin", value: pct(pr.gross_margin) },
            { label: "Operating Margin", value: pct(pr.operating_margin) },
            { label: "Net Margin", value: pct(pr.net_margin) },
          ]}
        />
        <Panel
          title="Solvency"
          rows={[
            { label: "Current Ratio", value: num(sol.current_ratio) },
            { label: "Debt to Equity", value: num(sol.debt_to_equity) },
          ]}
        />
        <Panel
          title="Growth (YoY, Quarter)"
          rows={[
            { label: "Revenue", value: pct(g.revenue_yoy) },
            { label: "Net Income", value: pct(g.net_income_yoy) },
          ]}
        />
        {data.performance.length > 0 && (
          <div className="rounded-lg border border-border bg-surface-0/40 px-3 py-2">
            <div className="text-[11px] font-semibold text-text-secondary mb-1.5">Price Performance</div>
            <div className="space-y-1">
              {data.performance.map((p) => (
                <div key={p.period} className="flex items-center justify-between gap-2 text-[11px]">
                  <span className="text-text-muted w-8">{p.period}</span>
                  <span
                    className={`tabular-nums font-medium ${
                      (p.change_pct ?? 0) >= 0 ? "text-emerald-500" : "text-red-500"
                    }`}
                  >
                    {pct(p.change_pct)}
                  </span>
                  <span className="text-text-secondary tabular-nums">
                    {rp(p.low)} – {rp(p.high)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
