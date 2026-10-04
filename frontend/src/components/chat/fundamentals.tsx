"use client";

import { useState } from "react";
import type { FundamentalData } from "@/lib/chat";

function big(v: number | null | undefined): string | null {
  if (v == null) return null;
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(2) + " T";
  if (a >= 1e9) return (v / 1e9).toFixed(2) + " B";
  if (a >= 1e6) return (v / 1e6).toFixed(1) + " M";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + " K";
  return v.toFixed(0);
}

function rp(v: number | null | undefined): string | null {
  return v == null ? null : Math.round(v).toLocaleString("id-ID");
}

function num(v: number | null | undefined, d = 2): string | null {
  return v == null ? null : v.toFixed(d);
}

function pct(v: number | null | undefined): string | null {
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

type QMetric = "net" | "eps" | "revenue";

function QuarterlyTable({ data }: { data: FundamentalData }) {
  const [metric, setMetric] = useState<QMetric>("net");
  const rows = data.quarterly || [];
  if (!rows.length) return null;

  const years = [...new Set(rows.map((r) => r.year).filter(Boolean))].sort().reverse().slice(0, 3);
  if (!years.length) return null;

  const cell = (year: string, quarter: string): number | null => {
    const it = rows.find((r) => r.year === year && r.quarter === quarter);
    return it ? it[metric] : null;
  };
  const fmt = (v: number | null): string =>
    v == null ? "-" : metric === "eps" ? Math.round(v).toLocaleString("id-ID") : (big(v) ?? "-");

  const latest = rows[rows.length - 1];
  const ann = latest ? (latest[metric] != null ? (latest[metric] as number) * 4 : null) : null;
  const ttm =
    metric === "net"
      ? data.income.net_income
      : metric === "revenue"
        ? data.income.revenue
        : data.per_share.eps;
  const meta = data.quarterly_meta;

  const metricBtn = (id: QMetric, label: string) => (
    <button
      key={id}
      type="button"
      onClick={() => setMetric(id)}
      className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
        metric === id ? "bg-emerald-500/15 text-emerald-500" : "text-text-secondary"
      }`}
    >
      {label}
    </button>
  );

  const qRow = (label: string, vals: (number | null)[], key: string) => (
    <tr key={key} className="border-t border-border/60 first:border-t-0">
      <td className="py-1 pr-2 text-text-muted">{label}</td>
      {vals.map((v, i) => (
        <td key={i} className="py-1 px-2 text-right text-text-primary tabular-nums">
          {fmt(v)}
        </td>
      ))}
    </tr>
  );

  const metaRow = (label: string, value: string | null, key: string) =>
    value == null ? null : (
      <tr key={key} className="border-t border-border/60">
        <td className="py-1 pr-2 text-text-muted">{label}</td>
        {years.map((y) => (
          <td key={y} className="py-1 px-2 text-right text-text-primary tabular-nums">
            {value}
          </td>
        ))}
      </tr>
    );

  return (
    <div className="rounded-lg border border-border bg-surface-0/40 px-3 py-2 sm:col-span-2 lg:col-span-3">
      <div className="flex items-center gap-1.5 mb-1.5">
        <div className="text-[11px] font-semibold text-text-secondary mr-auto">Quarterly</div>
        {metricBtn("net", "Net Income")}
        {metricBtn("eps", "EPS")}
        {metricBtn("revenue", "Revenue")}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-text-muted">
              <td className="py-1 pr-2">Period</td>
              {years.map((y) => (
                <td key={y} className="py-1 px-2 text-right font-semibold">
                  {y}
                </td>
              ))}
            </tr>
          </thead>
          <tbody>
            {["1", "2", "3", "4"].map((qt) =>
              qRow(
                `Q${qt}`,
                years.map((y) => cell(y, qt)),
                `q${qt}`
              )
            )}
            {qRow(
              "Annualised",
              years.map((y, i) => (i === 0 ? ann : null)),
              "ann"
            )}
            {qRow(
              "TTM",
              years.map((y, i) => (i === 0 ? ttm : null)),
              "ttm"
            )}
            {meta && (
              <>
                {metaRow("Market Cap", big(meta.market_cap), "mcap")}
                {metaRow("Enterprise Value", big(meta.ev), "ev")}
                {metaRow(
                  "Current Share Outstanding",
                  meta.shares != null ? big(meta.shares) : null,
                  "shares"
                )}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function FundamentalsCard({ data }: { data: FundamentalData }) {
  const v = data.valuation;
  const inc = data.income;
  const q = data.income_q;
  const bal = data.balance;
  const cf = data.cashflow;
  const ps = data.per_share;
  const pr = data.profitability;
  const sol = data.solvency;
  const g = data.growth;
  const ef = data.effectiveness;

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
          title="Current Valuation"
          rows={[
            { label: "Current PE Ratio (Annualised)", value: num(v.pe_ann) },
            { label: "Current PE Ratio (TTM)", value: num(v.pe) },
            { label: "Earnings Yield (TTM)", value: pct(v.earnings_yield) },
            { label: "Current Price to Sales (TTM)", value: num(v.psr) },
            { label: "Current Price to Book Value", value: num(v.pbv) },
            { label: "Current Price To Cashflow (TTM)", value: num(v.p_cf) },
            { label: "Current Price To Free Cashflow (TTM)", value: num(v.p_fcf) },
            { label: "EV to EBIT (TTM)", value: num(v.ev_ebit) },
            { label: "PEG Ratio", value: num(v.peg) },
            { label: "PEG Ratio (3yr)", value: num(v.peg_3yr) },
          ]}
        />
        <Panel
          title="Income Statement"
          rows={[
            { label: "Revenue (TTM)", value: big(inc.revenue) },
            { label: "Gross Profit (TTM)", value: big(inc.gross_profit) },
            { label: "Net Income (TTM)", value: big(inc.net_income) },
          ]}
        />
        <Panel
          title="Balance Sheet"
          rows={[
            { label: "Cash (Quarter)", value: big(bal.cash) },
            { label: "Total Assets (Quarter)", value: big(bal.total_assets) },
            { label: "Total Liabilities (Quarter)", value: big(bal.total_liabilities) },
            { label: "Working Capital (Quarter)", value: big(bal.working_capital) },
            { label: "Common Equity", value: big(bal.common_equity) },
            { label: "Long-term Debt (Quarter)", value: big(bal.long_term_debt) },
            { label: "Short-term Debt (Quarter)", value: big(bal.short_term_debt) },
            { label: "Total Debt (Quarter)", value: big(bal.total_debt) },
            { label: "Net Debt (Quarter)", value: big(bal.net_debt) },
            { label: "Total Equity", value: big(bal.total_equity) },
          ]}
        />
        <Panel
          title="Cash Flow Statement"
          rows={[
            { label: "Cash From Operations (TTM)", value: big(cf.operating) },
            { label: "Cash From Investing (TTM)", value: big(cf.investing) },
            { label: "Cash From Financing (TTM)", value: big(cf.financing) },
            { label: "Capital expenditure (TTM)", value: big(cf.free_cash_flow != null && cf.operating != null ? cf.operating - cf.free_cash_flow : null) },
            { label: "Free cash flow (TTM)", value: big(cf.free_cash_flow) },
          ]}
        />
        <Panel
          title="Per Share"
          rows={[
            { label: "Current EPS (TTM)", value: rp(ps.eps) },
            { label: "Current EPS (Annualised)", value: rp(ps.eps_ann) },
            { label: "Revenue Per Share (TTM)", value: rp(ps.revenue) },
            { label: "Cash Per Share (Quarter)", value: rp(ps.cash) },
            { label: "Current Book Value Per Share", value: rp(ps.book_value) },
            { label: "Free Cashflow Per Share (TTM)", value: rp(ps.fcf) },
          ]}
        />
        <Panel
          title="Profitability"
          rows={[
            { label: "Gross Profit Margin (Quarter)", value: pct(pr.gross_margin) },
            { label: "Operating Profit Margin (Quarter)", value: pct(pr.operating_margin) },
            { label: "Net Profit Margin (Quarter)", value: pct(pr.net_margin) },
          ]}
        />
        <Panel
          title="Growth"
          rows={[
            { label: "Revenue (Quarter YoY Growth)", value: pct(g.revenue_yoy) },
            { label: "Gross Profit (Quarter YoY Growth)", value: pct(g.gross_yoy) },
            { label: "Net Income (Quarter YoY Growth)", value: pct(g.net_income_yoy) },
          ]}
        />
        <Panel
          title="Solvency"
          rows={[
            { label: "Current Ratio (Quarter)", value: num(sol.current_ratio) },
            { label: "Quick Ratio (Quarter)", value: num(sol.quick_ratio) },
            { label: "Debt to Equity Ratio (Quarter)", value: num(sol.debt_to_equity) },
            { label: "LT Debt/Equity (Quarter)", value: num(sol.lt_debt_equity) },
            { label: "Total Liabilities/Equity (Quarter)", value: num(sol.liabilities_to_equity) },
            { label: "Total Debt/Total Assets (Quarter)", value: num(sol.total_debt_assets) },
            { label: "Financial Leverage (Quarter)", value: num(sol.financial_leverage) },
            { label: "Interest Coverage (TTM)", value: num(sol.interest_coverage, 1) },
            { label: "Free cash flow (Quarter)", value: big(sol.fcf_q) },
            { label: "Altman Z-Score (Modified)", value: num(sol.altman_z) },
          ]}
        />
        {ef && (
          <Panel
            title="Management Effectiveness"
            rows={[
              { label: "Return on Assets (TTM)", value: pct(ef.roa) },
              { label: "Return on Equity (TTM)", value: pct(ef.roe) },
              { label: "Return on Capital Employed (TTM)", value: pct(ef.roce) },
              { label: "Return On Invested Capital (TTM)", value: pct(ef.roic) },
              { label: "Days Sales Outstanding (Quarter)", value: num(ef.dso) },
              { label: "Days Inventory (Quarter)", value: num(ef.dio) },
              { label: "Days Payables Outstanding (Quarter)", value: num(ef.dpo) },
              { label: "Cash Conversion Cycle (Quarter)", value: num(ef.ccc) },
              { label: "Receivables Turnover (Quarter)", value: num(ef.receivables_turnover) },
              { label: "Asset Turnover (TTM)", value: num(ef.asset_turnover) },
              { label: "Inventory Turnover (TTM)", value: num(ef.inventory_turnover) },
            ]}
          />
        )}
        <QuarterlyTable data={data} />
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
        {q && (
          <Panel
            title="Latest Quarter"
            rows={[
              { label: "Revenue", value: big(q.revenue) },
              { label: "Gross Profit", value: big(q.gross_profit) },
              { label: "Operating Profit", value: big(q.operating_profit) },
              { label: "Net Income", value: big(q.net_income) },
              { label: "EPS", value: rp(q.eps) },
            ]}
          />
        )}
      </div>
    </div>
  );
}
