"use client";

import { Card, Section, VerdictBadge } from "@/components/ui";
import type {
  MarketIntelligenceData,
  MIRecommendationItem,
} from "@/lib/api";

function fmtCurrency(value?: number | null): string | null {
  if (value == null || typeof value !== "number") return null;
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}Rp ${(abs / 1e12).toFixed(2)} T`;
  if (abs >= 1e9) return `${sign}Rp ${(abs / 1e9).toFixed(2)} M`;
  if (abs >= 1e6) return `${sign}Rp ${(abs / 1e6).toFixed(2)} Jt`;
  return `${sign}Rp ${abs.toLocaleString("id-ID")}`;
}

function fmtNumber(value?: number | null, digits = 2): string | null {
  if (value == null || typeof value !== "number") return null;
  return value.toLocaleString("id-ID", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtDate(value?: string | null): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleDateString("id-ID", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="bg-zinc-800 rounded-lg px-3 py-2">
      <div className="text-zinc-500 text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-zinc-200 text-sm mt-0.5 break-words">
        {value ?? <span className="text-zinc-600">—</span>}
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p className="text-zinc-500 text-sm italic">{children}</p>;
}

function RecommendationBadge({ rec }: { rec: MIRecommendationItem }) {
  const map: Record<string, "BUY" | "HOLD" | "SELL" | "AVOID"> = {
    strong_buy: "BUY",
    buy: "BUY",
    hold: "HOLD",
    sell: "SELL",
    strong_sell: "SELL",
  };
  const verdict = map[rec.key ?? ""] ?? "AVOID";
  return (
    <div className="flex items-center gap-2">
      <VerdictBadge verdict={verdict} />
      {rec.number_of_analysts != null && (
        <span className="text-xs text-zinc-500">{rec.number_of_analysts} analis</span>
      )}
    </div>
  );
}

export function MarketIntelligenceCard({
  data,
}: {
  data: MarketIntelligenceData;
}) {
  const dividend = data.dividend;
  const corpActions = data.corporate_actions ?? [];
  const foreignFlow = data.foreign_flow;
  const brokers = data.broker_summary ?? [];
  const earnings = data.earnings;
  const priceTarget = data.price_target;
  const recommendation = data.recommendation;

  const topBrokers = [...brokers]
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 5);

  return (
    <Card padding="md">
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 13h2l2 5h10l2-5h2M5 13l1.5-6h11L19 13M9 18h.01M15 18h.01" />
        </svg>
        <h3 className="text-sm font-semibold text-zinc-300">Market Intelligence</h3>
      </div>

      <div className="space-y-4">
        {/* Dividend */}
        <div>
          <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Dividen</div>
          {dividend ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Field label="Per Lembar" value={fmtCurrency(dividend.cash_dividend_per_share)} />
              <Field label="Total" value={fmtCurrency(dividend.cash_dividend_total)} />
              <Field label="Currency" value={dividend.currency ?? undefined} />
              <Field label="Fiskal" value={dividend.fiscal_year ?? undefined} />
              <Field label="Ex Date" value={fmtDate(dividend.ex_date)} />
              <Field label="Payment" value={fmtDate(dividend.payment_date)} />
              {dividend.bonus_shares_total != null && (
                <Field label="Saham Bonus" value={fmtNumber(dividend.bonus_shares_total, 0)} />
              )}
            </div>
          ) : (
            <Muted>Tidak ada data dividen.</Muted>
          )}
        </div>

        {/* Corporate Actions */}
        <div>
          <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Aksi Korporasi</div>
          {corpActions.length > 0 ? (
            <div className="space-y-2">
              {corpActions.map((ca, i) => (
                <div key={i} className="bg-zinc-800 rounded-lg px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-zinc-200 font-medium">{ca.action_type}</span>
                    {ca.date && <span className="text-xs text-zinc-500">{fmtDate(ca.date)}</span>}
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-xs text-zinc-400">
                    {ca.ratio && <span>Ratio: {ca.ratio}</span>}
                    {ca.name && <span>{ca.name}</span>}
                    {ca.exercise_price != null && <span>Exercise: {fmtCurrency(ca.exercise_price)}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Muted>Tidak ada aksi korporasi.</Muted>
          )}
        </div>

        {/* Foreign Flow */}
        <div>
          <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Foreign Flow</div>
          {foreignFlow ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Field label="Net" value={fmtCurrency(foreignFlow.foreign_net)} />
              <Field label="Beli" value={fmtCurrency(foreignFlow.foreign_buy)} />
              <Field label="Jual" value={fmtCurrency(foreignFlow.foreign_sell)} />
              <Field label="Close" value={fmtNumber(foreignFlow.close)} />
              <Field label="Tanggal" value={fmtDate(foreignFlow.date)} />
            </div>
          ) : (
            <Muted>Data foreign flow belum tersedia.</Muted>
          )}
        </div>

        {/* Broker Summary */}
        <div>
          <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Broker Summary</div>
          {topBrokers.length > 0 ? (
            <div className="space-y-1">
              {topBrokers.map((b, i) => (
                <div key={i} className="flex justify-between items-center text-sm px-3 py-1.5 bg-zinc-800 rounded-lg">
                  <span className="text-zinc-200 truncate">
                    {b.broker_name || b.broker_code || "—"}
                  </span>
                  <span className="text-zinc-400 text-xs shrink-0 ml-2">
                    {fmtCurrency(b.value) ?? (b.frequency != null ? `${b.frequency}x` : "—")}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <Muted>Belum ada ringkasan broker.</Muted>
          )}
        </div>

        {/* Earnings */}
        <div>
          <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Earnings</div>
          {earnings ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Field label="Earnings Date" value={fmtDate(earnings.earnings_date)} />
              <Field label="EPS Avg" value={fmtNumber(earnings.eps_estimate_avg)} />
              <Field label="EPS High" value={fmtNumber(earnings.eps_estimate_high)} />
              <Field label="EPS Low" value={fmtNumber(earnings.eps_estimate_low)} />
              <Field label="Revenue Avg" value={fmtCurrency(earnings.revenue_estimate_avg)} />
              <Field label="Revenue High" value={fmtCurrency(earnings.revenue_estimate_high)} />
            </div>
          ) : (
            <Muted>Estimasi earnings belum tersedia.</Muted>
          )}
        </div>

        {/* Analyst — collapsible */}
        <Section title="Analis (Price Target & Rekomendasi)" defaultOpen={false}>
          <div className="space-y-3">
            <div>
              <div className="text-xs text-zinc-500 mb-1">Price Target</div>
              {priceTarget ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <Field label="Mean" value={fmtNumber(priceTarget.mean)} />
                  <Field label="High" value={fmtNumber(priceTarget.high)} />
                  <Field label="Low" value={fmtNumber(priceTarget.low)} />
                  <Field label="Currency" value={priceTarget.currency ?? undefined} />
                  <Field label="Jumlah Analis" value={fmtNumber(priceTarget.number_of_analysts, 0)} />
                </div>
              ) : (
                <Muted>Tidak ada target harga (wajar untuk sebagian besar saham).</Muted>
              )}
            </div>
            <div>
              <div className="text-xs text-zinc-500 mb-1">Rekomendasi</div>
              {recommendation ? (
                <RecommendationBadge rec={recommendation} />
              ) : (
                <Muted>Tidak ada rekomendasi analis (wajar untuk sebagian besar saham).</Muted>
              )}
            </div>
          </div>
        </Section>
      </div>
    </Card>
  );
}
