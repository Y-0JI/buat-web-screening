"use client";

import { useState, useEffect } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { useAuth } from "@/lib/auth-context";
import { AuthGuard } from "@/components/auth-guard";
import { Card, Skeleton } from "@/components/ui";
import { fetchWatchlist, addWatchlist, removeWatchlist, type WatchlistItem } from "@/lib/api";

export function WatchlistView() {
  const { isAuthenticated } = useAuth();
  const { openResearch } = useWorkspace();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [note, setNote] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (isAuthenticated) loadData();
  }, [isAuthenticated]);

  async function loadData() {
    setLoading(true);
    try {
      const res = await fetchWatchlist();
      if (res.success && res.data) setItems(res.data);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    const t = input.trim().toUpperCase();
    if (!t || adding) return;
    setAdding(true);
    try {
      const res = await addWatchlist(t, note.trim() || undefined);
      if (res.success && res.data) {
        setItems(res.data);
        setInput("");
        setNote("");
      }
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(ticker: string) {
    try {
      await removeWatchlist(ticker);
      setItems((p) => p.filter((w) => w.ticker !== ticker));
    } catch {}
  }

  if (!isAuthenticated) {
    return (
      <AuthGuard>
        <div />
      </AuthGuard>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <Card padding="md">
        <h2 className="text-xl font-bold text-zinc-100 mb-4">Watchlist</h2>

        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Kode saham..."
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          />
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Catatan (opsional)"
            className="w-48 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          />
          <button
            onClick={handleAdd}
            disabled={!input.trim() || adding}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {adding ? "Menambahkan..." : "Tambah"}
          </button>
        </div>
      </Card>

      {loading ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} variant="row" height="h-14" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card padding="lg" className="text-center">
          <svg className="w-16 h-16 text-zinc-700 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          <h3 className="text-zinc-300 font-medium mb-2">Watchlist Kosong</h3>
          <p className="text-zinc-500">Tambahkan saham ke watchlist untuk memantau pergerakannya.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <WatchlistRow key={item.id} item={item} onRemove={handleRemove} onResearch={openResearch} />
          ))}
        </div>
      )}
    </div>
  );
}

function WatchlistRow({ item, onRemove, onResearch }: { item: WatchlistItem; onRemove: (t: string) => void; onResearch: (t: string) => void }) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800/60 transition-colors cursor-pointer"
      onClick={() => onResearch(item.ticker)}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-100 text-sm">{item.ticker}</span>
          {item.note && <span className="text-zinc-500 text-xs truncate">{item.note}</span>}
        </div>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onRemove(item.ticker); }}
        className="text-zinc-500 hover:text-red-400 text-xs transition-colors shrink-0"
      >
        Hapus
      </button>
    </div>
  );
}