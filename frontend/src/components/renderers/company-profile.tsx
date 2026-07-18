"use client";

import { Card } from "@/components/ui";
import type { CompanyProfile } from "@/lib/api";

function formatMarketCap(value?: number): string {
  if (value == null) return "—";
  if (value >= 1e12) return `Rp ${(value / 1e12).toFixed(2)} T`;
  if (value >= 1e9) return `Rp ${(value / 1e9).toFixed(2)} M`;
  if (value >= 1e6) return `Rp ${(value / 1e6).toFixed(2)} Jt`;
  return `Rp ${value.toLocaleString("id-ID")}`;
}

function formatShares(value?: number): string {
  if (value == null) return "—";
  return value.toLocaleString("id-ID");
}

function formatDate(value?: string): string {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleDateString("id-ID", { year: "numeric", month: "long", day: "numeric" });
}

function normalizeUrl(url?: string): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : `https://${url}`;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-zinc-800 rounded-lg px-3 py-2">
      <div className="text-zinc-500 text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-zinc-200 text-sm mt-0.5 break-words">{value}</div>
    </div>
  );
}

export function CompanyProfileCard({ data }: { data: CompanyProfile }) {
  const initial = (data.symbol || data.name || "?").slice(0, 4).toUpperCase();
  const website = normalizeUrl(data.website);

  return (
    <Card padding="md">
      <div className="flex items-start gap-4 mb-4">
        {data.logo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={data.logo}
            alt={data.name || data.symbol || ""}
            className="w-14 h-14 rounded-lg object-contain bg-zinc-800 shrink-0"
          />
        ) : (
          <div className="w-14 h-14 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0">
            <span className="text-zinc-400 font-bold text-sm">{initial}</span>
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-zinc-100 truncate">
            {data.name || data.symbol}
          </h2>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            {data.symbol && (
              <span className="text-xs font-mono text-zinc-400">{data.symbol}</span>
            )}
            {data.exchange && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                {data.exchange}
              </span>
            )}
            {data.sector && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">
                {data.sector}
              </span>
            )}
            {data.market_segment && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                {data.market_segment}
              </span>
            )}
          </div>
        </div>
      </div>

      {data.business_summary && (
        <p className="text-sm text-zinc-400 leading-relaxed mb-4">
          {data.business_summary}
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <Field label="Industri" value={data.industry || "—"} />
        <Field label="Sub Sektor" value={data.sub_sector || "—"} />
        <Field label="Negara" value={data.country || "—"} />
        <Field label="Tanggal Listing" value={formatDate(data.listing_date)} />
        <Field label="Market Cap" value={formatMarketCap(data.market_cap)} />
        <Field label="Saham Beredar" value={formatShares(data.shares_outstanding)} />
        <Field
          label="Website"
          value={
            website ? (
              <a
                href={website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:underline break-all"
              >
                {data.website}
              </a>
            ) : (
              "—"
            )
          }
        />
        {data.employees != null && (
          <Field label="Karyawan" value={data.employees.toLocaleString("id-ID")} />
        )}
      </div>
    </Card>
  );
}
