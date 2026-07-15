"use client";

import type { RankingItem } from "@/lib/api";

function timeAgo(isoDate?: string | null): string {
  if (!isoDate) return "Tidak diketahui";
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Baru saja";
  if (diffMin < 60) return `${diffMin}m lalu`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}j lalu`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}h lalu`;
}

interface MarketOverviewProps {
  items: RankingItem[];
  generated_at?: string;
}

export function MarketOverview({ items, generated_at }: MarketOverviewProps) {
  const verdictCounts = { BUY: 0, HOLD: 0, SELL: 0, AVOID: 0 };
  let totalScore = 0;
  let simulatedCount = 0;

  for (const item of items) {
    verdictCounts[item.verdict] = (verdictCounts[item.verdict] || 0) + 1;
    totalScore += item.score;
    if (item.is_simulated) simulatedCount++;
  }

  const avgScore = items.length > 0 ? Math.round(totalScore / items.length) : 0;
  const total = items.length;
  const dataStatus =
    simulatedCount === total
      ? "Simulasi"
      : simulatedCount > 0
        ? "Mix"
        : "Live";

  const verdictConfig = [
    { key: "BUY", label: "BUY", color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { key: "HOLD", label: "HOLD", color: "text-amber-400", bg: "bg-amber-500/10" },
    { key: "SELL", label: "SELL", color: "text-red-400", bg: "bg-red-500/10" },
    { key: "AVOID", label: "AVOID", color: "text-zinc-400", bg: "bg-zinc-500/10" },
  ] as const;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold text-zinc-100">Kondisi Pasar</h2>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`px-2 py-0.5 rounded-full font-medium ${
              dataStatus === "Live"
                ? "bg-emerald-500/10 text-emerald-400"
                : dataStatus === "Mix"
                  ? "bg-amber-500/10 text-amber-400"
                  : "bg-zinc-500/10 text-zinc-400"
            }`}
          >
            Data {dataStatus}
          </span>
          <span className="text-zinc-500">{timeAgo(generated_at)}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {verdictConfig.map((v) => (
          <div
            key={v.key}
            className={`${v.bg} rounded-2xl px-4 py-3 text-center`}
          >
            <div className={`text-2xl font-bold ${v.color}`}>
              {verdictCounts[v.key]}
            </div>
            <div className={`text-xs font-medium ${v.color} mt-0.5`}>
              {v.label}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="flex-1 bg-zinc-900 rounded-full h-2 overflow-hidden">
          <div className="h-full flex">
            {total > 0 && (
              <>
                <div
                  className="bg-emerald-500"
                  style={{ width: `${(verdictCounts.BUY / total) * 100}%` }}
                />
                <div
                  className="bg-amber-500"
                  style={{ width: `${(verdictCounts.HOLD / total) * 100}%` }}
                />
                <div
                  className="bg-red-500"
                  style={{ width: `${(verdictCounts.SELL / total) * 100}%` }}
                />
                <div
                  className="bg-zinc-600"
                  style={{ width: `${(verdictCounts.AVOID / total) * 100}%` }}
                />
              </>
            )}
          </div>
        </div>
        <span className="text-xs text-zinc-400 whitespace-nowrap">
          Skor rata-rata:{" "}
          <span className="font-bold text-zinc-200">{avgScore}</span>
        </span>
      </div>
    </section>
  );
}
