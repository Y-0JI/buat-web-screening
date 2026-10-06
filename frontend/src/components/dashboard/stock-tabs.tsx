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
      ) : tab === "chartplus" ? (
        <div className="mt-2">
          <TradingViewChart symbol={toTradingViewSymbol(ticker)} />
        </div>
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
    </div>
  );
}
