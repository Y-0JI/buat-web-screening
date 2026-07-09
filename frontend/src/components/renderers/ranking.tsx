"use client";

import type { RankingItem } from "@/lib/api";

const verdictColors: Record<string, string> = {
  BUY: "bg-emerald-600 text-emerald-100",
  HOLD: "bg-amber-600 text-amber-100",
  SELL: "bg-red-600 text-red-100",
  AVOID: "bg-zinc-600 text-zinc-100",
};

function RankingRow({ item }: { item: RankingItem }) {
  const priceColor =
    item.change_percent !== undefined
      ? item.change_percent >= 0
        ? "text-emerald-400"
        : "text-red-400"
      : "text-zinc-100";

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800 transition-colors">
      <div className="w-6 text-center text-zinc-500 font-mono text-sm font-bold">
        {item.rank}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-100 text-sm">
            {item.ticker}
          </span>
          {item.company_name && (
            <span className="text-zinc-500 text-xs truncate hidden sm:inline">
              {item.company_name}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="text-right hidden sm:block">
          <div className={`text-sm font-bold ${priceColor}`}>
            {item.price?.toLocaleString() || "-"}
          </div>
          {item.change_percent !== undefined && (
            <div className={`text-xs ${priceColor}`}>
              {item.change_percent >= 0 ? "+" : ""}
              {item.change_percent}%
            </div>
          )}
        </div>

        <div className="w-24">
          <div className="w-full bg-zinc-800 rounded-full h-2">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500"
              style={{ width: `${item.score}%` }}
            />
          </div>
          <div className="text-xs text-zinc-400 text-center mt-0.5">
            {item.score}
          </div>
        </div>

        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${verdictColors[item.verdict]}`}>
          {item.verdict}
        </span>

        <div className="text-xs text-zinc-500 w-10 text-right">
          {item.confidence}%
        </div>
      </div>
    </div>
  );
}

export function RankingView({ items }: { items: RankingItem[] }) {
  return (
    <div className="w-full max-w-3xl mx-auto mt-6">
      <h2 className="text-xl font-bold text-zinc-100 mb-2">
        Screening Harian
      </h2>
      <p className="text-zinc-500 text-sm mb-4">
        Saham terbaik berdasarkan skor komposit
      </p>

      <div className="space-y-2">
        {items.map((item) => (
          <RankingRow key={item.ticker} item={item} />
        ))}
      </div>

      <p className="text-xs text-zinc-600 italic mt-4 text-center">
        Hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi.
      </p>
    </div>
  );
}
