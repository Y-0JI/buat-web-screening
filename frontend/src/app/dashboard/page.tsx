"use client";

import { useEffect, useState } from "react";
import {
  fetchWatchlist,
  removeWatchlist,
  fetchHistory,
  type WatchlistItem,
  type HistoryItem,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { AuthGuard } from "@/components/auth-guard";

function WatchlistTab() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadWatchlist();
  }, []);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const res = await fetchWatchlist();
      if (res.success && res.data) setItems(res.data);
    } catch {
      setError("Gagal memuat watchlist");
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (ticker: string) => {
    try {
      await removeWatchlist(ticker);
      setItems((prev) => prev.filter((w) => w.ticker !== ticker));
    } catch {
      setError("Gagal menghapus");
    }
  };

  if (loading) return <div className="text-zinc-500 text-sm">Memuat...</div>;
  if (error) return <div className="text-red-400 text-sm">{error}</div>;

  return (
    <div>
      {items.length === 0 ? (
        <p className="text-zinc-500 text-sm">Belum ada saham di watchlist.</p>
      ) : (
        <div className="space-y-2">
          {items.map((w) => (
            <div
              key={w.id}
              className="flex items-center justify-between px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl"
            >
              <div>
                <span className="text-zinc-100 font-semibold">{w.ticker}</span>
                {w.note && (
                  <span className="text-zinc-500 text-sm ml-2">{w.note}</span>
                )}
              </div>
              <button
                onClick={() => handleRemove(w.ticker)}
                className="text-zinc-500 hover:text-red-400 text-sm transition-colors"
              >
                Hapus
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function HistoryTab() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const verdictColors: Record<string, string> = {
    BUY: "text-emerald-400",
    HOLD: "text-amber-400",
    SELL: "text-red-400",
    AVOID: "text-zinc-400",
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const res = await fetchHistory(30);
      if (res.success && res.data) setItems(res.data);
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-zinc-500 text-sm">Memuat...</div>;

  return (
    <div>
      {items.length === 0 ? (
        <p className="text-zinc-500 text-sm">Belum ada riwayat riset.</p>
      ) : (
        <div className="space-y-2">
          {items.map((h) => (
            <div
              key={h.id}
              className="flex items-center justify-between px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl"
            >
              <div>
                <span className="text-zinc-100 font-semibold">{h.ticker}</span>
                <span className="text-zinc-500 text-sm ml-2">
                  {h.created_at ? new Date(h.created_at).toLocaleString("id-ID") : ""}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {h.score !== null && h.score !== undefined && (
                  <span className="text-zinc-400 text-sm">{h.score}</span>
                )}
                {h.verdict && (
                  <span
                    className={`text-sm font-bold ${
                      verdictColors[h.verdict] || "text-zinc-400"
                    }`}
                  >
                    {h.verdict}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"watchlist" | "history">("watchlist");

  return (
    <AuthGuard>
      <main className="max-w-2xl mx-auto px-4 py-12">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-zinc-100">
            Halo, {user?.username} 👋
          </h1>
          <p className="text-zinc-500 text-sm mt-1">Dashboard pribadi kamu</p>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setTab("watchlist")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === "watchlist"
                ? "bg-emerald-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            Watchlist
          </button>
          <button
            onClick={() => setTab("history")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === "history"
                ? "bg-emerald-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            Riwayat
          </button>
        </div>

        {tab === "watchlist" ? <WatchlistTab /> : <HistoryTab />}
      </main>
    </AuthGuard>
  );
}
