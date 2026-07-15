"use client";

import { useEffect, useState } from "react";
import {
  screenStocks,
  fetchWatchlist,
  addWatchlist,
  removeWatchlist,
  fetchHistory,
  type RankingItem,
  type WatchlistItem,
  type HistoryItem,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { AuthGuard } from "@/components/auth-guard";
import { MarketOverview } from "@/components/dashboard/market-overview";
import { AIPicks } from "@/components/dashboard/ai-picks";
import { WatchlistSection } from "@/components/dashboard/watchlist-section";
import { RecentHistory } from "@/components/dashboard/recent-history";

function SectionError({ message }: { message: string }) {
  return (
    <p className="text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-xl px-4 py-3">
      {message}
    </p>
  );
}

function SectionSkeleton() {
  return (
    <div className="animate-pulse space-y-2">
      <div className="h-4 bg-zinc-800 rounded w-32" />
      <div className="h-16 bg-zinc-900 rounded-2xl" />
      <div className="h-16 bg-zinc-900 rounded-2xl" />
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [screenItems, setScreenItems] = useState<RankingItem[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | undefined>();
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const [screenLoading, setScreenLoading] = useState(true);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [screenError, setScreenError] = useState("");
  const [watchlistError, setWatchlistError] = useState("");
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    loadScreen();
    loadWatchlist();
    loadHistory();
  }, []);

  const loadScreen = async () => {
    setScreenLoading(true);
    setScreenError("");
    try {
      const res = await screenStocks();
      if (res.success && res.data) {
        setScreenItems(res.data);
        setGeneratedAt(res.generated_at);
      } else {
        setScreenError(res.error || "Gagal memuat rekomendasi AI");
      }
    } catch {
      setScreenError("Gagal memuat rekomendasi AI");
    } finally {
      setScreenLoading(false);
    }
  };

  const loadWatchlist = async () => {
    setWatchlistLoading(true);
    setWatchlistError("");
    try {
      const res = await fetchWatchlist();
      if (res.success && res.data) setWatchlist(res.data);
      else setWatchlistError(res.error || "Gagal memuat watchlist");
    } catch {
      setWatchlistError("Gagal memuat watchlist");
    } finally {
      setWatchlistLoading(false);
    }
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const res = await fetchHistory(30);
      if (res.success && res.data) setHistory(res.data);
      else setHistoryError(res.error || "Gagal memuat riwayat");
    } catch {
      setHistoryError("Gagal memuat riwayat");
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleRemoveWatchlist = async (ticker: string) => {
    try {
      await removeWatchlist(ticker);
      setWatchlist((prev) => prev.filter((w) => w.ticker !== ticker));
    } catch {
      setWatchlistError("Gagal menghapus");
    }
  };

  const handleAddWatchlist = async (ticker: string, note?: string) => {
    const res = await addWatchlist(ticker, note);
    if (res.success && res.data) {
      setWatchlist(res.data);
      setWatchlistError("");
    } else {
      setWatchlistError(res.error || "Gagal menambah");
    }
  };

  return (
    <AuthGuard>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-100">
            Halo, {user?.username} 👋
          </h1>
          <p className="text-zinc-500 text-sm mt-1">
            Pantau pasar dan temukan peluang terbaik hari ini
          </p>
        </header>

        <div className="space-y-8">
          <section>
            {screenLoading ? (
              <SectionSkeleton />
            ) : screenError ? (
              <SectionError message={screenError} />
            ) : (
              <>
                <MarketOverview
                  items={screenItems}
                  generated_at={generatedAt}
                />
                <div className="mt-6">
                  <AIPicks items={screenItems} />
                </div>
              </>
            )}
          </section>

          <section>
            {watchlistLoading ? (
              <SectionSkeleton />
            ) : watchlistError ? (
              <SectionError message={watchlistError} />
            ) : (
              <WatchlistSection
                items={watchlist}
                onRemove={handleRemoveWatchlist}
                onAdd={handleAddWatchlist}
              />
            )}
          </section>

          <section>
            {historyLoading ? (
              <SectionSkeleton />
            ) : historyError ? (
              <SectionError message={historyError} />
            ) : (
              <RecentHistory items={history} />
            )}
          </section>
        </div>
      </main>
    </AuthGuard>
  );
}
