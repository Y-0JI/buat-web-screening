"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { Card, Skeleton, Badge, VerdictBadge } from "@/components/ui";
import { screenStocks, type RankingItem } from "@/lib/api";

export function ScreeningView() {
  const { state, openResearch } = useWorkspace();
  const [mode, setMode] = useState<"BSJP" | "BPJS">(state.activeMode);
  const [items, setItems] = useState<RankingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatedAt, setGeneratedAt] = useState<string | undefined>();

  useEffect(() => {
    loadData();
  }, [mode]);

  async function loadData() {
    setLoading(true);
    try {
      const res = await screenStocks(mode);
      if (res.success && res.data) {
        setItems(res.data);
        setGeneratedAt(res.generated_at);
      }
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  function handleModeChange(m: "BSJP" | "BPJS") {
    setMode(m);
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <Card padding="md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-zinc-100">Screening Saham</h2>
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
        </div>
        <p className="text-zinc-500 text-sm">
          {generatedAt ? `Terakhir diperbarui: ${new Date(generatedAt).toLocaleString("id-ID")}` : "Data screening berdasarkan analisis AI"}
        </p>
      </Card>

      {loading ? (
        <div className="space-y-2">
          {[...Array(10)].map((_, i) => (
            <Skeleton key={i} variant="row" height="h-16" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card padding="md">
          <p className="text-zinc-500 text-center">
            {generatedAt
              ? "Tidak ada data screening tersedia."
              : "Screening sedang diproses, muat ulang dalam beberapa menit."}
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map(item => (
            <ScreeningRow key={item.ticker} item={item} onResearch={openResearch} />
          ))}
        </div>
      )}

      <p className="text-xs text-zinc-600 text-center">
        Hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi.
      </p>
    </div>
  );
}

function ScreeningRow({ item, onResearch }: { item: RankingItem; onResearch: (t: string) => void }) {
  const vc: Record<string, string> = { BUY: "text-green-400", HOLD: "text-amber-400", SELL: "text-red-400", AVOID: "text-zinc-400" };

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800/60 transition-colors cursor-pointer"
      onClick={() => onResearch(item.ticker)}
    >
      <div className="w-6 text-center text-zinc-500 font-mono text-sm font-bold shrink-0">{item.rank}</div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-100 text-sm">{item.ticker}</span>
          {item.is_simulated && <Badge variant="status-sim" size="sm">Simulasi</Badge>}
          {item.company_name && <span className="text-zinc-500 text-xs truncate hidden sm:inline">{item.company_name}</span>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="text-right hidden sm:block">
          <div className={`text-sm font-bold ${item.change_percent !== undefined ? (item.change_percent >= 0 ? "text-green-400" : "text-red-400") : "text-zinc-100"}`}>
            {item.price?.toLocaleString() || "-"}
          </div>
          {item.change_percent !== undefined && (
            <div className={`text-xs ${item.change_percent >= 0 ? "text-green-400" : "text-red-400"}`}>
              {item.change_percent >= 0 ? "+" : ""}{item.change_percent}%
            </div>
          )}
        </div>

        <div className="w-24">
          <div className="w-full bg-zinc-800 rounded-full h-2">
            <div className="h-2 rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500" style={{ width: `${item.score}%` }} />
          </div>
          <div className="text-xs text-zinc-400 text-center mt-0.5">{item.score}</div>
        </div>

        <VerdictBadge verdict={item.verdict} />

        <div className="text-xs text-zinc-500 w-10 text-right">{item.confidence}%</div>
      </div>
    </div>
  );
}