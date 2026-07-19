"use client";

import { Card } from "@/components/ui";
import type { Fundamentals } from "@/lib/api";

function fmtCurrency(value?: number | null): string {
  if (value == null || typeof value !== "number") return "—";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `Rp ${(abs / 1e12).toFixed(2)} T`;
  if (abs >= 1e9) return `Rp ${(abs / 1e9).toFixed(2)} M`;
  if (abs >= 1e6) return `Rp ${(abs / 1e6).toFixed(2)} Jt`;
  return `Rp ${abs.toLocaleString("id-ID")}`;
}

function fmtPrice(value?: number | null): string {
  if (value == null || typeof value !== "number") return "—";
  return `Rp ${value.toLocaleString("id-ID")}`;
}

function fmtVolume(value?: number | null): string {
  if (value == null || typeof value !== "number") return "—";
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)} M`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)} Jt`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)} Rb`;
  return value.toLocaleString("id-ID");
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-800 rounded-lg px-3 py-2.5 text-center">
      <div className="text-zinc-500 text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-zinc-100 text-sm font-semibold mt-1">{value}</div>
    </div>
  );
}

export function QuickStats({ data }: { data: Fundamentals }) {
  if (!data || data.error) return null;

  const hasAny =
    data.week_52_high != null ||
    data.week_52_low != null ||
    data.average_volume != null ||
    data.market_cap != null;
  if (!hasAny) return null;

  return (
    <Card padding="md">
      <div className="flex items-center gap-2 mb-3">
        <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        <h3 className="text-sm font-semibold text-zinc-300">Quick Stats</h3>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <StatBox label="52W High" value={fmtPrice(data.week_52_high)} />
        <StatBox label="52W Low" value={fmtPrice(data.week_52_low)} />
        <StatBox label="Avg Volume" value={fmtVolume(data.average_volume)} />
        <StatBox label="Market Cap" value={fmtCurrency(data.market_cap)} />
      </div>
    </Card>
  );
}
