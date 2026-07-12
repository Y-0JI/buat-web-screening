"use client";

import { useAuth } from "@/lib/auth-context";
import { addWatchlist, fetchStockHistory, type OHLCVPoint } from "@/lib/api";
import type { StockReport } from "@/lib/api";
import { useState, useEffect } from "react";
import { PriceChart } from "@/components/chart/PriceChart";

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    BUY: "bg-emerald-600 text-emerald-100",
    HOLD: "bg-amber-600 text-amber-100",
    SELL: "bg-red-600 text-red-100",
    AVOID: "bg-zinc-600 text-zinc-100",
  };
  return (
    <span
      className={`px-3 py-1 rounded-full text-sm font-bold ${
        colors[verdict] || "bg-zinc-600"
      }`}
    >
      {verdict}
    </span>
  );
}

export function StockReportCard({ data }: { data: StockReport }) {
  const { user } = useAuth();
  const [wlMsg, setWlMsg] = useState<string | null>(null);
  const [chartData, setChartData] = useState<OHLCVPoint[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartOpen, setChartOpen] = useState(true);
  const [period, setPeriod] = useState("6mo");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setChartLoading(true);
      try {
        const res = await fetchStockHistory(data.ticker, period);
        if (!cancelled && res.success && res.data) {
          setChartData(res.data);
        }
      } catch {
        // silent
      } finally {
        if (!cancelled) setChartLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [data.ticker, period]);

  const priceColor =
    data.change_percent !== undefined
      ? data.change_percent >= 0
        ? "text-emerald-400"
        : "text-red-400"
      : "text-zinc-100";

  return (
    <div className="w-full max-w-2xl mx-auto mt-6 p-6 bg-zinc-900 border border-zinc-800 rounded-2xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">
            {data.company_name || data.ticker}
          </h2>
          <span className="text-zinc-500 text-sm">{data.ticker}</span>
        </div>
        <div className="flex items-center gap-2">
          {data.mode && (
            <span className="text-xs px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-zinc-400">
              {data.mode}
            </span>
          )}
          <VerdictBadge verdict={data.verdict} />
        </div>
      </div>

      {data.is_simulated && (
        <div className="mb-4 p-3 bg-amber-950/30 border border-amber-800/50 rounded-xl text-sm">
          <span className="text-amber-400 font-medium">Data simulasi</span>
          <span className="text-amber-300/70 ml-2">Sumber data tidak tersedia, menampilkan data simulasi.</span>
        </div>
      )}

      <div className="mb-4">
        <button
          onClick={() => setChartOpen(!chartOpen)}
          className="flex items-center justify-between w-full text-sm font-semibold text-zinc-400 hover:text-zinc-300 mb-2"
        >
          <span>Chart Harga</span>
          <span className="text-xs">{chartOpen ? "▲" : "▼"}</span>
        </button>
        {chartOpen && (
          <div>
            <div className="flex gap-1 mb-2">
              {["1mo", "3mo", "6mo", "1y"].map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${
                    period === p
                      ? "bg-blue-600 border-blue-500 text-white"
                      : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-300"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            {chartLoading ? (
              <div className="h-[330px] flex items-center justify-center bg-zinc-900 rounded-xl">
                <span className="text-zinc-500 text-sm animate-pulse">Memuat chart...</span>
              </div>
            ) : (
              <PriceChart data={chartData} isSimulated={data.is_simulated} />
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-zinc-800 rounded-xl p-3 text-center">
          <div className="text-xs text-zinc-500 mb-1">Harga</div>
          <div className={`text-lg font-bold ${priceColor}`}>
            {data.price?.toLocaleString() || "-"}
          </div>
          {data.change_percent !== undefined && (
            <div className={`text-xs ${priceColor}`}>
              {data.change_percent >= 0 ? "+" : ""}
              {data.change_percent}%
            </div>
          )}
        </div>
        <div className="bg-zinc-800 rounded-xl p-3 text-center">
          <div className="text-xs text-zinc-500 mb-1">Skor</div>
          <div className="text-lg font-bold text-zinc-100">{data.score}</div>
        </div>
        <div className="bg-zinc-800 rounded-xl p-3 text-center">
          <div className="text-xs text-zinc-500 mb-1">Keyakinan</div>
          <div className="text-lg font-bold text-zinc-100">
            {data.confidence}%
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="w-full bg-zinc-800 rounded-full h-3">
          <div
            className="h-3 rounded-full transition-all bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500"
            style={{ width: `${data.score}%` }}
          />
        </div>
      </div>

      {data.stop_loss && (
        <div className="mb-4 p-3 bg-red-950/30 border border-red-900/50 rounded-xl text-sm">
          <span className="text-red-400 font-medium">Stop-loss: </span>
          <span className="text-red-300">{data.stop_loss.toLocaleString()}</span>
        </div>
      )}

      <div className="space-y-2 mb-4">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
          Indikator
        </h3>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {data.indicators.rsi != null && (
            <div className="bg-zinc-800 rounded-lg px-3 py-2 flex justify-between">
              <span className="text-zinc-400">RSI</span>
              <span className="text-zinc-200 font-mono">{data.indicators.rsi}</span>
            </div>
          )}
          {data.indicators.volume_ratio != null && (
            <div className="bg-zinc-800 rounded-lg px-3 py-2 flex justify-between">
              <span className="text-zinc-400">Vol Ratio</span>
              <span className="text-zinc-200 font-mono">{data.indicators.volume_ratio}x</span>
            </div>
          )}
          {data.indicators.gap_percent != null && (
            <div className="bg-zinc-800 rounded-lg px-3 py-2 flex justify-between">
              <span className="text-zinc-400">Gap</span>
              <span className="text-zinc-200 font-mono">{data.indicators.gap_percent}%</span>
            </div>
          )}
          {data.indicators.atr != null && (
            <div className="bg-zinc-800 rounded-lg px-3 py-2 flex justify-between">
              <span className="text-zinc-400">ATR</span>
              <span className="text-zinc-200 font-mono">{data.indicators.atr}</span>
            </div>
          )}
        </div>
      </div>

      <div className="p-4 bg-zinc-800 rounded-xl mb-4">
        <p className="text-zinc-300 text-sm leading-relaxed">{data.summary}</p>
      </div>

      {data.score_breakdown.length > 0 && (
        <details className="mb-4">
          <summary className="text-sm text-zinc-500 cursor-pointer hover:text-zinc-300">
            Detail skor
          </summary>
          <div className="mt-2 space-y-1">
            {data.score_breakdown.map((b, i) => (
              <div key={i} className="flex justify-between text-xs text-zinc-400 px-2 py-1">
                <span>{b.funnel_layer}</span>
                <span>
                  {b.score} (x{b.weight})
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

      {user && (
        <div className="mb-4">
          <button
            onClick={async () => {
              setWlMsg(null);
              try {
                const res = await addWatchlist(data.ticker);
                if (res.success) {
                  setWlMsg("Ditambahkan ke watchlist");
                } else {
                  setWlMsg(res.error || "Gagal");
                }
              } catch {
                setWlMsg("Gagal menghubungi server");
              }
            }}
            className="w-full py-2 px-4 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-xl text-sm text-zinc-300 transition-colors"
          >
            + Tambah ke Watchlist
          </button>
          {wlMsg && (
            <div className="text-xs text-zinc-400 mt-1 text-center">{wlMsg}</div>
          )}
        </div>
      )}

      <p className="text-xs text-zinc-600 italic">{data.disclaimer}</p>
    </div>
  );
}
