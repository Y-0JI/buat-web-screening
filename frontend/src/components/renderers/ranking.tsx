"use client";

import { useState } from "react";
import type { RankingItem } from "@/lib/api";
import { Card, VerdictBadge, Bar, Badge } from "@/components/ui";

function RankingRow({ item, onExpand, expanded }: { item: RankingItem; onExpand: () => void; expanded: boolean }) {
  const priceColor =
    item.change_percent !== undefined
      ? item.change_percent >= 0 ? "text-green-400" : "text-red-400"
      : "text-zinc-100";

  return (
    <Card variant="interactive" padding="none" onClick={onExpand}>
      <div className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-6 text-center text-zinc-500 font-mono text-sm font-bold shrink-0">{item.rank}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-zinc-100 text-sm">{item.ticker}</span>
              {item.is_simulated && <Badge variant="status-sim" size="sm">Simulasi</Badge>}
              {item.company_name && (
                <span className="text-zinc-500 text-xs truncate hidden sm:inline">{item.company_name}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right hidden sm:block">
              <div className={`text-sm font-bold ${priceColor}`}>{item.price?.toLocaleString() || "-"}</div>
              {item.change_percent !== undefined && (
                <div className={`text-xs ${priceColor}`}>{item.change_percent >= 0 ? "+" : ""}{item.change_percent}%</div>
              )}
            </div>
            <div className="w-20">
              <Bar variant="score" value={item.score} height="sm" />
              <div className="text-[10px] text-zinc-500 text-center mt-0.5">{item.score}</div>
            </div>
            <VerdictBadge verdict={item.verdict} size="sm" />
            <div className="text-xs text-zinc-500 w-10 text-right">{item.confidence}%</div>
          </div>
        </div>
        {expanded && item.summary && (
          <div className="mt-3 ml-9 text-xs text-zinc-400 leading-relaxed border-t border-zinc-800 pt-3">
            {item.summary}
          </div>
        )}
      </div>
    </Card>
  );
}

export function RankingView({ items }: { items: RankingItem[] }) {
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  return (
    <div className="w-full max-w-3xl mx-auto mt-6 space-y-4">
      <div>
        <h2 className="text-xl font-bold text-zinc-100">Screening Harian</h2>
        <p className="text-zinc-500 text-sm mt-1">Saham terbaik berdasarkan skor komposit</p>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <RankingRow
            key={item.ticker}
            item={item}
            expanded={expandedTicker === item.ticker}
            onExpand={() => setExpandedTicker(expandedTicker === item.ticker ? null : item.ticker)}
          />
        ))}
      </div>
      <p className="text-xs text-zinc-600 italic text-center">
        Hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi.
      </p>
    </div>
  );
}
