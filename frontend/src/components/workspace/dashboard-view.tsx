"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { AuthGuard } from "@/components/auth-guard";
import { Card, Section, Skeleton, Badge, VerdictBadge } from "@/components/ui";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { MarketInsight } from "@/components/dashboard/market-insight";
import { useWorkspace } from "@/lib/workspace-context";
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

function PickCard({ item, onResearch }: { item: RankingItem; onResearch: (t: string) => void }) {
  const priceColor = item.change_percent !== undefined ? (item.change_percent >= 0 ? "text-green-400" : "text-red-400") : "text-zinc-100";
  return (
    <Card variant="interactive" padding="sm" onClick={() => onResearch(item.ticker)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="w-5 text-center text-zinc-500 font-mono text-xs font-bold">{item.rank}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-zinc-100 text-sm">{item.ticker}</span>
              {item.is_simulated && <Badge variant="status-sim" size="sm">Simulasi</Badge>}
              {item.company_name && <span className="text-zinc-500 text-xs truncate hidden sm:inline">{item.company_name}</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {item.price !== undefined && (
            <div className="text-right hidden sm:block">
              <div className={`text-sm font-bold ${priceColor}`}>{item.price?.toLocaleString()}</div>
              {item.change_percent !== undefined && (
                <div className={`text-xs ${priceColor}`}>{item.change_percent >= 0 ? "+" : ""}{item.change_percent}%</div>
              )}
            </div>
          )}
          <div className="w-16">
            <div className="w-full bg-zinc-800 rounded-full h-1.5">
              <div className="h-1.5 rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500" style={{ width: `${item.score}%` }} />
            </div>
            <div className="text-[10px] text-zinc-500 text-center mt-0.5">{item.score}</div>
          </div>
          <VerdictBadge verdict={item.verdict} size="sm" />
        </div>
      </div>
    </Card>
  );
}

function WatchlistCard({ item, onRemove, onResearch }: { item: WatchlistItem; onRemove: (t: string) => void; onResearch: (t: string) => void }) {
  return (
    <div className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded-xl p-3 hover:bg-zinc-800/60 transition-colors">
      <button
        type="button"
        onClick={() => onResearch(item.ticker)}
        className="flex items-center min-w-0 text-left"
      >
        <span className="text-zinc-100 font-semibold text-sm">{item.ticker}</span>
        {item.note && <span className="text-zinc-500 text-xs ml-2 truncate">{item.note}</span>}
      </button>
      <button
        type="button"
        onClick={() => onRemove(item.ticker)}
        className="text-zinc-500 hover:text-red-400 text-xs transition-colors ml-2 shrink-0"
      >
        Hapus
      </button>
    </div>
  );
}

function HistoryRow({ item, onResearch }: { item: HistoryItem; onResearch: (t: string) => void }) {
  const vc: Record<string, string> = { BUY: "text-green-400", HOLD: "text-amber-400", SELL: "text-red-400", AVOID: "text-zinc-400" };
  return (
    <button onClick={() => onResearch(item.ticker)} className="w-full flex items-center justify-between px-3 py-2 hover:bg-zinc-800/60 rounded-lg transition-colors">
      <div className="min-w-0 flex items-center gap-2">
        <span className="text-zinc-100 font-semibold text-sm">{item.ticker}</span>
        <span className="text-zinc-500 text-xs">
          {item.created_at ? new Date(item.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "short" }) : ""}
        </span>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {item.score != null && <span className="text-zinc-400 text-sm">{item.score}</span>}
        {item.verdict && <span className={`text-sm font-bold ${vc[item.verdict] || "text-zinc-400"}`}>{item.verdict}</span>}
      </div>
    </button>
  );
}

export function DashboardView() {
  const { isAuthenticated, user } = useAuth();
  const { openResearch } = useWorkspace();
  const [screenItems, setScreenItems] = useState<RankingItem[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | undefined>();
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [wlInput, setWlInput] = useState("");
  const [wlAdding, setWlAdding] = useState(false);
  const [loading, setLoading] = useState({ screen: true, wl: true, hist: true });

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading({ screen: true, wl: true, hist: true });
    await Promise.allSettled([
      screenStocks().then(r => { if (r.success && r.data) { setScreenItems(r.data); setGeneratedAt(r.generated_at); } }),
      isAuthenticated && fetchWatchlist().then(r => { if (r.success && r.data) setWatchlist(r.data); }),
      isAuthenticated && fetchHistory(20).then(r => { if (r.success && r.data) setHistory(r.data); }),
    ]);
    setLoading({ screen: false, wl: false, hist: false });
  }

  async function handleAddWl() {
    const t = wlInput.trim().toUpperCase();
    if (!t || wlAdding) return;
    setWlAdding(true);
    try {
      const res = await addWatchlist(t);
      if (res.success && res.data) { setWatchlist(res.data); setWlInput(""); }
    } finally { setWlAdding(false); }
  }

  async function handleRemoveWl(ticker: string) {
    try { await removeWatchlist(ticker); setWatchlist(p => p.filter(w => w.ticker !== ticker)); } catch {}
  }

  const topPicks = screenItems.slice(0, 5);
  const visibleHistory = history.slice(0, 5);

  const content = (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-zinc-100">
          {isAuthenticated ? `Halo, ${user?.username}` : "Beranda"}
        </h1>
        <p className="text-zinc-500 text-sm mt-1">Pantau pasar dan temukan peluang terbaik hari ini</p>
      </header>

      {loading.screen ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} variant="card" height="h-24" />)}
        </div>
      ) : (
        <SummaryCards items={screenItems} generatedAt={generatedAt} />
      )}

      <MarketInsight />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Section title="Top Rekomendasi AI" defaultOpen>
            {loading.screen ? (
              <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} variant="row" />)}</div>
            ) : topPicks.length === 0 ? (
              <p className="text-zinc-500 text-sm">Belum ada data screening.</p>
            ) : (
              <div className="space-y-2">{topPicks.map(item => <PickCard key={item.ticker} item={item} onResearch={openResearch} />)}</div>
            )}
          </Section>

          {isAuthenticated && (
            <Section title="Watchlist" defaultOpen={false}
              action={
                <div className="flex gap-1.5">
                  <input type="text" value={wlInput} onChange={e => setWlInput(e.target.value)}
                    placeholder="Tambah..."
                    className="w-20 bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                    onKeyDown={e => e.key === "Enter" && handleAddWl()} />
                  <button onClick={handleAddWl} disabled={!wlInput.trim() || wlAdding}
                    className="px-2 py-1 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-xs rounded-md transition-colors">+</button>
                </div>
              }
            >
              {loading.wl ? (
                <div className="space-y-2">{[...Array(2)].map((_, i) => <Skeleton key={i} variant="row" />)}</div>
              ) : watchlist.length === 0 ? (
                <p className="text-zinc-500 text-sm">Belum ada saham di watchlist.</p>
              ) : (
                <div className="space-y-1.5">{watchlist.map(w => <WatchlistCard key={w.id} item={w} onRemove={handleRemoveWl} onResearch={openResearch} />)}</div>
              )}
            </Section>
          )}
        </div>

        <div>
          {isAuthenticated && (
            <Section title="Riwayat Terakhir" defaultOpen>
              {loading.hist ? (
                <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} variant="row" />)}</div>
              ) : visibleHistory.length === 0 ? (
                <p className="text-zinc-500 text-sm">Belum ada riwayat riset.</p>
              ) : (
                <div className="divide-y divide-zinc-800">{visibleHistory.map(h => <HistoryRow key={h.id} item={h} onResearch={openResearch} />)}</div>
              )}
            </Section>
          )}
        </div>
      </div>
    </div>
  );

  if (!isAuthenticated) return content;
  return <AuthGuard requireAuth={false}>{content}</AuthGuard>;
}
