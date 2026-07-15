"use client";

import type { StockReport } from "@/lib/api";
import { Card, VerdictBadge, Bar } from "@/components/ui";

function CompareCard({ report }: { report: StockReport }) {
  const priceColor =
    report.change_percent !== undefined
      ? report.change_percent >= 0 ? "text-green-400" : "text-red-400"
      : "text-zinc-100";

  const indicators = [
    report.indicators.rsi != null && { label: "RSI", value: `${report.indicators.rsi}` },
    report.indicators.volume_ratio != null && { label: "Vol", value: `${report.indicators.volume_ratio}x` },
    report.indicators.gap_percent != null && { label: "Gap", value: `${report.indicators.gap_percent}%` },
    report.indicators.atr != null && { label: "ATR", value: `${report.indicators.atr}` },
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  return (
    <Card padding="md" className="flex-1 min-w-0">
      <div className="flex items-center justify-between mb-3">
        <div className="min-w-0">
          <div className="text-lg font-bold text-zinc-100 truncate">{report.company_name || report.ticker}</div>
          <div className="text-zinc-500 text-xs font-mono">{report.ticker}</div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <VerdictBadge verdict={report.verdict} />
          {report.is_simulated && <span className="text-amber-400 text-[10px]">Simulasi</span>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-zinc-800 rounded-lg p-2 text-center">
          <div className="text-[10px] text-zinc-500 mb-0.5">Harga</div>
          <div className={`text-sm font-bold ${priceColor}`}>{report.price?.toLocaleString() || "-"}</div>
          {report.change_percent !== undefined && (
            <div className={`text-[10px] ${priceColor}`}>{report.change_percent >= 0 ? "+" : ""}{report.change_percent}%</div>
          )}
        </div>
        <div className="bg-zinc-800 rounded-lg p-2 text-center">
          <div className="text-[10px] text-zinc-500 mb-0.5">Skor</div>
          <div className="text-sm font-bold text-zinc-100">{report.score}</div>
        </div>
        <div className="bg-zinc-800 rounded-lg p-2 text-center">
          <div className="text-[10px] text-zinc-500 mb-0.5">Keyakinan</div>
          <div className="text-sm font-bold text-zinc-100">{report.confidence}%</div>
        </div>
      </div>

      <Bar variant="score" value={report.score} height="sm" className="mb-3" />

      {indicators.length > 0 && (
        <div className="grid grid-cols-2 gap-1 mb-3">
          {indicators.map((it, i) => (
            <div key={i} className="bg-zinc-800 rounded px-2 py-1 flex justify-between text-xs">
              <span className="text-zinc-400">{it.label}</span>
              <span className="text-zinc-200 font-mono">{it.value}</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-zinc-500 text-xs leading-relaxed line-clamp-3">{report.summary}</p>
    </Card>
  );
}

export function ComparisonView({ reports }: { reports: StockReport[] }) {
  return (
    <div className="w-full max-w-4xl mx-auto mt-6 space-y-4">
      <h2 className="text-xl font-bold text-zinc-100">Perbandingan Saham</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {reports.map((r) => (
          <CompareCard key={r.ticker} report={r} />
        ))}
      </div>
      {reports.length > 0 && (
        <p className="text-xs text-zinc-600 italic text-center">{reports[0].disclaimer}</p>
      )}
    </div>
  );
}
