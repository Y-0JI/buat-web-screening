"use client";

import { useState } from "react";
import type { HistoryItem } from "@/lib/api";

const verdictColors: Record<string, string> = {
  BUY: "text-emerald-400",
  HOLD: "text-amber-400",
  SELL: "text-red-400",
  AVOID: "text-zinc-400",
};

interface RecentHistoryProps {
  items: HistoryItem[];
  maxItems?: number;
}

export function RecentHistory({ items, maxItems = 3 }: RecentHistoryProps) {
  const [expanded, setExpanded] = useState(false);
  const visibleItems = expanded ? items : items.slice(0, maxItems);

  return (
    <section>
      <h2 className="text-lg font-bold text-zinc-100 mb-3">Riwayat</h2>

      {items.length === 0 ? (
        <p className="text-zinc-500 text-sm">Belum ada riwayat riset.</p>
      ) : (
        <>
          <div className="space-y-2">
            {visibleItems.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl"
              >
                <div className="min-w-0">
                  <span className="text-zinc-100 font-semibold text-sm">
                    {h.ticker}
                  </span>
                  <span className="text-zinc-500 text-xs ml-2">
                    {h.created_at
                      ? new Date(h.created_at).toLocaleDateString("id-ID", {
                          day: "numeric",
                          month: "short",
                        })
                      : ""}
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
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

          {items.length > maxItems && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-emerald-400 hover:text-emerald-300 mt-2 transition-colors"
            >
              {expanded
                ? "Tampilkan lebih sedikit"
                : `Lihat semua (${items.length})`}
            </button>
          )}
        </>
      )}
    </section>
  );
}
