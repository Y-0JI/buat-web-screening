"use client";

import { useEffect, useState } from "react";
import type { NewsItem } from "@/lib/chat";
import type { LiveTrade } from "@/lib/live";
import { KeyStatsPanel } from "./key-stats-panel";
import { NewsPanel } from "./news-panel";
import { NewsReader } from "./news-reader";
import { OverviewPanel } from "./overview-panel";
import { SeasonalityPanel } from "./seasonality-panel";
import { TradingViewChart } from "./tradingview-chart";
import { toTradingViewSymbol } from "@/lib/chat";

interface TabDef {
  id: string;
  label: string;
  disabled?: boolean;
}

const TABS: TabDef[] = [
  { id: "overview", label: "Overview" },
  { id: "key-stats", label: "Key Stats" },
  { id: "analysis", label: "Analysis" },
  { id: "financials", label: "Financials" },
  { id: "fundachart", label: "Fundachart" },
  { id: "insider", label: "Insider" },
  { id: "corp-action", label: "Corp. Action", disabled: true },
  { id: "profile", label: "Profile" },
  { id: "news", label: "News" },
  { id: "chartplus", label: "Chart+" },
];

const INDEX_TABS: TabDef[] = [
  { id: "overview", label: "Overview" },
  { id: "seasonality", label: "Seasonality" },
  { id: "chartplus", label: "Chart+" },
];

export function StockTabs({ ticker, liveTrades, liveConnected, isIndex }: { ticker: string; liveTrades: LiveTrade[]; liveConnected: boolean; isIndex: boolean }) {
  const [tab, setTab] = useState<string | null>(null);
  const [article, setArticle] = useState<NewsItem | null>(null);

  useEffect(() => {
    setTab(null);
    setArticle(null);
  }, [ticker]);

  const click = (id: string) => setTab((prev) => (prev === id ? null : id));
  const list = isIndex ? INDEX_TABS : TABS;
  const active = list.find((t) => t.id === tab);
  const openNews = () => setTab("news");

  // Chart+ dibuka fullscreen: Esc = kembali ke dashboard.
  const chartFull = tab === "chartplus";
  useEffect(() => {
    if (!chartFull) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTab(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chartFull]);

  return (
    <div className="px-4 pb-3">
      <div className="flex overflow-x-auto rounded-lg border border-border divide-x divide-border bg-surface-1">
        {list.map((t) => {
          const on = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              disabled={t.disabled}
              onClick={() => click(t.id)}
              className={`flex-1 whitespace-nowrap px-3 py-2 text-xs font-medium transition-colors ${
                on
                  ? "text-emerald-500"
                  : t.disabled
                    ? "text-text-muted/50 cursor-not-allowed"
                    : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === "overview" ? (
        <OverviewPanel
          ticker={ticker}
          onOpenArticle={setArticle}
          onOpenNews={openNews}
          liveTrades={liveTrades}
          liveConnected={liveConnected}
          hideBrokers={isIndex}
        />
      ) : tab === "key-stats" ? (
        <KeyStatsPanel ticker={ticker} />
      ) : tab === "news" ? (
        <NewsPanel ticker={ticker} onOpenArticle={setArticle} />
      ) : tab === "seasonality" ? (
        <SeasonalityPanel ticker={ticker} />
      ) : active ? (
        <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          Konten {active.label} — segera
        </div>
      ) : null}

      {article && (
        <NewsReader
          item={article}
          onClose={() => setArticle(null)}
          onKeepReading={() => {
            setArticle(null);
            openNews();
          }}
        />
      )}

      {chartFull && (
        <div className="fixed inset-0 z-50 bg-surface-0 flex flex-col min-h-0">
          <header className="h-12 shrink-0 flex items-center gap-2 px-3 border-b border-border">
            <button
              type="button"
              onClick={() => setTab(null)}
              className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-2 transition-colors"
              aria-label="Kembali ke dashboard"
              title="Kembali ke dashboard"
            >
              <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-xs font-medium">Kembali</span>
            </button>
            <div className="flex-1 min-w-0 px-1">
              <h2 className="text-xs font-semibold leading-tight truncate">
                {ticker} · Chart+
              </h2>
              <p className="text-[10px] text-text-muted leading-tight truncate">
                TradingView Advanced Chart
              </p>
            </div>
          </header>
          <div className="flex-1 min-h-0">
            <TradingViewChart symbol={toTradingViewSymbol(ticker)} height="100%" />
          </div>
        </div>
      )}
    </div>
  );
}
