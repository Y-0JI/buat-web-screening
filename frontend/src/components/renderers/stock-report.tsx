"use client";

import { useAuth } from "@/lib/auth-context";
import {
  addWatchlist,
  fetchStockHistory,
  fetchStockNews,
  type NewsItem,
  type OHLCVPoint,
  type StockReport,
} from "@/lib/api";
import { useState, useEffect } from "react";
import { PriceChart } from "@/components/chart/PriceChart";
import { Card, Badge, VerdictBadge, Button, Section, Bar, Skeleton } from "@/components/ui";

function IndicatorGrid({ data }: { data: StockReport["indicators"] }) {
  const items: Array<{ label: string; value: string; tone?: string }> = [];
  if (data.rsi != null) items.push({ label: "RSI", value: `${data.rsi}` });
  if (data.volume_ratio != null) items.push({ label: "Volume Ratio", value: `${data.volume_ratio}x` });
  if (data.gap_percent != null) items.push({ label: "Gap", value: `${data.gap_percent}%` });
  if (data.atr != null) items.push({ label: "ATR", value: `${data.atr}` });
  if (data.vwap != null) items.push({ label: "VWAP", value: `${data.vwap}` });
  if (data.support_resistance) {
    items.push({ label: "Support", value: `${data.support_resistance.support}` });
    items.push({ label: "Resistance", value: `${data.support_resistance.resistance}` });
  }
  const emaEntries = Object.entries(data.ema || {});
  for (const [k, v] of emaEntries) items.push({ label: k, value: `${v}` });

  if (items.length === 0) {
    return <p className="text-zinc-500 text-sm">Tidak ada indikator tersedia.</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {items.map((it, i) => (
        <div key={i} className="bg-zinc-800 rounded-lg px-3 py-2 flex justify-between items-center">
          <span className="text-zinc-400 text-xs">{it.label}</span>
          <span className="text-zinc-200 font-mono text-sm">{it.value}</span>
        </div>
      ))}
    </div>
  );
}

function NewsSection({ ticker }: { ticker: string }) {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetchStockNews(ticker, 5);
        if (!cancelled && res.success && res.data) {
          setNews(res.data);
        }
      } catch {
        // silent
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [ticker]);

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => <Skeleton key={i} variant="text" />)}
      </div>
    );
  }

  if (news.length === 0) {
    return <p className="text-zinc-500 text-sm">Belum ada berita terbaru.</p>;
  }

  return (
    <div className="space-y-2">
      {news.map((n, i) => (
        <a
          key={i}
          href={n.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block p-3 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors"
        >
          <div className="text-sm text-zinc-200 font-medium leading-snug">{n.headline}</div>
          <div className="text-xs text-zinc-500 mt-1">{n.publisher} · {n.source} · {n.published_date}</div>
        </a>
      ))}
    </div>
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
      ? data.change_percent >= 0 ? "text-green-400" : "text-red-400"
      : "text-zinc-100";

  return (
    <div className="w-full max-w-3xl mx-auto mt-6 space-y-4">
      {/* Hero */}
      <Card padding="lg">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-2xl font-bold text-zinc-100 truncate">{data.company_name || data.ticker}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-zinc-500 text-sm font-mono">{data.ticker}</span>
              {data.mode && <Badge variant="mode" size="sm">{data.mode}</Badge>}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <VerdictBadge verdict={data.verdict} />
            {data.is_simulated && <Badge variant="status-sim" size="sm">Simulasi</Badge>}
          </div>
        </div>

        <div className="flex items-end gap-4 mt-4">
          <div>
            <div className={`text-3xl font-bold ${priceColor}`}>
              {data.price != null ? data.price.toLocaleString() : "-"}
            </div>
            {data.change_percent !== undefined && (
              <div className={`text-sm ${priceColor}`}>
                {data.change_percent >= 0 ? "+" : ""}{data.change_percent}%
              </div>
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-zinc-500">Skor {data.score}</span>
              <span className="text-xs text-zinc-500">Keyakinan {data.confidence}%</span>
            </div>
            <Bar variant="score" value={data.score} height="md" />
          </div>
        </div>

        {data.stop_loss && (
          <div className="mt-4 p-3 bg-red-950/30 border border-red-900/50 rounded-xl text-sm">
            <span className="text-red-400 font-medium">Rekomendasi stop-loss: </span>
            <span className="text-red-300">{data.stop_loss.toLocaleString()}</span>
          </div>
        )}
      </Card>

      {/* Chart */}
      <Card padding="md">
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
      </Card>

      {/* AI Narrative */}
      <Card padding="md">
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h3 className="text-sm font-semibold text-zinc-300">Insight AI</h3>
          {data.ai_available === false && (
            <span className="text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/30 px-1.5 py-0.5 rounded">
              AI sedang tidak tersedia — coba lagi nanti
            </span>
          )}
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed">{data.summary}</p>
      </Card>

      {/* Collapsible sections */}
      <Section title="Teknikal" defaultOpen>
        <IndicatorGrid data={data.indicators} />
      </Section>

      <Section title="Skor Breakdown" defaultOpen={false}>
        <div className="space-y-1">
          {data.score_breakdown.map((b, i) => (
            <div key={i} className="flex justify-between text-sm px-2 py-1.5 bg-zinc-800 rounded-lg">
              <span className="text-zinc-400">{b.funnel_layer}</span>
              <span className="text-zinc-200">{b.score} <span className="text-zinc-500">×{b.weight}</span></span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Berita Terkait" defaultOpen={false}>
        <NewsSection ticker={data.ticker} />
      </Section>

      {user && (
        <div>
          <Button
            variant="secondary"
            className="w-full"
            onClick={async () => {
              setWlMsg(null);
              try {
                const res = await addWatchlist(data.ticker);
                setWlMsg(res.success ? "Ditambahkan ke watchlist" : res.error || "Gagal");
              } catch {
                setWlMsg("Gagal menghubungi server");
              }
            }}
          >
            + Tambah ke Watchlist
          </Button>
          {wlMsg && <div className="text-xs text-zinc-400 mt-1 text-center">{wlMsg}</div>}
        </div>
      )}

      <p className="text-xs text-zinc-600 italic text-center">{data.disclaimer}</p>
    </div>
  );
}
