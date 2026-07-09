"use client";

import type { StockReport } from "@/lib/api";

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    BUY: "bg-emerald-600 text-emerald-100",
    HOLD: "bg-amber-600 text-amber-100",
    SELL: "bg-red-600 text-red-100",
    AVOID: "bg-zinc-600 text-zinc-100",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${colors[verdict] || "bg-zinc-600"}`}>
      {verdict}
    </span>
  );
}

function MiniCard({ report }: { report: StockReport }) {
  const priceColor =
    report.change_percent !== undefined
      ? report.change_percent >= 0
        ? "text-emerald-400"
        : "text-red-400"
      : "text-zinc-100";

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 flex-1 min-w-0">
      <div className="flex items-center justify-between mb-3">
        <div className="truncate">
          <div className="text-lg font-bold text-zinc-100 truncate">
            {report.company_name || report.ticker}
          </div>
          <div className="text-zinc-500 text-xs">{report.ticker}</div>
        </div>
        <VerdictBadge verdict={report.verdict} />
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-zinc-800 rounded-xl p-2 text-center">
          <div className="text-xs text-zinc-500">Harga</div>
          <div className={`text-base font-bold ${priceColor}`}>
            {report.price?.toLocaleString() || "-"}
          </div>
        </div>
        <div className="bg-zinc-800 rounded-xl p-2 text-center">
          <div className="text-xs text-zinc-500">Skor</div>
          <div className="text-base font-bold text-zinc-100">{report.score}</div>
        </div>
        <div className="bg-zinc-800 rounded-xl p-2 text-center">
          <div className="text-xs text-zinc-500">Keyakinan</div>
          <div className="text-base font-bold text-zinc-100">{report.confidence}%</div>
        </div>
      </div>

      <div className="w-full bg-zinc-800 rounded-full h-2 mb-3">
        <div
          className="h-2 rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500"
          style={{ width: `${report.score}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-1 text-xs mb-2">
        {report.indicators.rsi !== undefined && (
          <div className="bg-zinc-800 rounded-lg px-2 py-1 flex justify-between">
            <span className="text-zinc-400">RSI</span>
            <span className="text-zinc-200">{report.indicators.rsi}</span>
          </div>
        )}
        {report.indicators.volume_ratio !== undefined && (
          <div className="bg-zinc-800 rounded-lg px-2 py-1 flex justify-between">
            <span className="text-zinc-400">Vol</span>
            <span className="text-zinc-200">{report.indicators.volume_ratio}x</span>
          </div>
        )}
        {report.indicators.gap_percent !== undefined && (
          <div className="bg-zinc-800 rounded-lg px-2 py-1 flex justify-between">
            <span className="text-zinc-400">Gap</span>
            <span className="text-zinc-200">{report.indicators.gap_percent}%</span>
          </div>
        )}
        {report.indicators.atr !== undefined && (
          <div className="bg-zinc-800 rounded-lg px-2 py-1 flex justify-between">
            <span className="text-zinc-400">ATR</span>
            <span className="text-zinc-200">{report.indicators.atr}</span>
          </div>
        )}
      </div>

      <p className="text-zinc-400 text-xs leading-relaxed line-clamp-3">
        {report.summary}
      </p>
    </div>
  );
}

export function ComparisonView({ reports }: { reports: StockReport[] }) {
  return (
    <div className="w-full max-w-4xl mx-auto mt-6">
      <h2 className="text-xl font-bold text-zinc-100 mb-4">
        Perbandingan Saham
      </h2>
      <div className="flex gap-4 flex-col sm:flex-row">
        {reports.map((r) => (
          <MiniCard key={r.ticker} report={r} />
        ))}
      </div>
      {reports.length > 0 && (
        <p className="text-xs text-zinc-600 italic mt-4 text-center">
          {reports[0].disclaimer}
        </p>
      )}
    </div>
  );
}
