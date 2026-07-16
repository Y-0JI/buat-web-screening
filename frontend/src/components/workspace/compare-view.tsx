"use client";

import { useState } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { Card, Section, Skeleton, Badge, VerdictBadge, Bar } from "@/components/ui";
import { compareStocks, type StockReport } from "@/lib/api";

export function CompareView() {
  const { state, openCompare } = useWorkspace();
  const [mode, setMode] = useState<"BSJP" | "BPJS">(state.activeMode);
  const [tickersInput, setTickersInput] = useState(state.compareTickers.join(", "));
  const [reports, setReports] = useState<StockReport[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleCompare() {
    const tickers = tickersInput
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    if (tickers.length < 2) return;

    setLoading(true);
    try {
      const res = await compareStocks(tickers, mode);
      if (res.success && res.data) {
        setReports(res.data);
        openCompare(tickers, mode);
      }
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  }

  function handleModeChange(m: "BSJP" | "BPJS") {
    setMode(m);
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <Card padding="md">
        <h2 className="text-xl font-bold text-zinc-100 mb-4">Perbandingan Saham</h2>

        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="flex-1">
            <input
              type="text"
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              placeholder="Masukkan kode saham, pisahkan koma (contoh: BBCA, BBRI, BMRI)"
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === "Enter" && handleCompare()}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Mode:</span>
            <button
              onClick={() => handleModeChange("BSJP")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "BSJP" ? "bg-blue-600 text-white" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              BSJP
            </button>
            <button
              onClick={() => handleModeChange("BPJS")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "BPJS" ? "bg-blue-600 text-white" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              BPJS
            </button>
          </div>
          <button
            onClick={handleCompare}
            disabled={loading || tickersInput.split(",").filter(t => t.trim()).length < 2}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "Memuat..." : "Bandingkan"}
          </button>
        </div>

        <p className="text-xs text-zinc-500">Masukkan minimal 2 kode saham yang dipisahkan dengan koma.</p>
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} variant="card" height="h-64" />
          ))}
        </div>
      ) : reports.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((r) => (
            <CompareCard key={r.ticker} report={r} />
          ))}
        </div>
      ) : (
        <Card padding="lg" className="text-center">
          <svg className="w-16 h-16 text-zinc-700 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-zinc-300 font-medium mb-2">Mulai Perbandingan</h3>
          <p className="text-zinc-500">Masukkan minimal 2 kode saham untuk membandingkan analisis.</p>
        </Card>
      )}
    </div>
  );
}

function CompareCard({ report }: { report: StockReport }) {
  const priceColor = report.change_percent !== undefined ? (report.change_percent >= 0 ? "text-green-400" : "text-red-400") : "text-zinc-100";

  return (
    <Card padding="md">
      <div className="flex items-center justify-between mb-3">
        <div className="min-w-0">
          <div className="text-lg font-bold text-zinc-100 truncate">{report.company_name || report.ticker}</div>
          <div className="text-zinc-500 text-xs font-mono">{report.ticker}</div>
        </div>
        <VerdictBadge verdict={report.verdict} />
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

      <div className="grid grid-cols-2 gap-1 mb-3 text-xs">
        {report.indicators.rsi != null && (
          <div className="bg-zinc-800 rounded px-2 py-1 flex justify-between">
            <span className="text-zinc-400">RSI</span>
            <span className="text-zinc-200 font-mono">{report.indicators.rsi}</span>
          </div>
        )}
        {report.indicators.volume_ratio != null && (
          <div className="bg-zinc-800 rounded px-2 py-1 flex justify-between">
            <span className="text-zinc-400">Vol</span>
            <span className="text-zinc-200 font-mono">{report.indicators.volume_ratio}x</span>
          </div>
        )}
        {report.indicators.gap_percent != null && (
          <div className="bg-zinc-800 rounded px-2 py-1 flex justify-between">
            <span className="text-zinc-400">Gap</span>
            <span className="text-zinc-200 font-mono">{report.indicators.gap_percent}%</span>
          </div>
        )}
        {report.indicators.atr != null && (
          <div className="bg-zinc-800 rounded px-2 py-1 flex justify-between">
            <span className="text-zinc-400">ATR</span>
            <span className="text-zinc-200 font-mono">{report.indicators.atr}</span>
          </div>
        )}
      </div>

      <p className="text-zinc-500 text-xs leading-relaxed line-clamp-3">{report.summary}</p>
    </Card>
  );
}