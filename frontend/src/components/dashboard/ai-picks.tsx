"use client";

import type { RankingItem } from "@/lib/api";

const verdictColors: Record<string, string> = {
  BUY: "bg-emerald-600 text-emerald-100",
  HOLD: "bg-amber-600 text-amber-100",
  SELL: "bg-red-600 text-red-100",
  AVOID: "bg-zinc-600 text-zinc-100",
};

function PickCard({ item }: { item: RankingItem }) {
  const priceColor =
    item.change_percent !== undefined
      ? item.change_percent >= 0
        ? "text-emerald-400"
        : "text-red-400"
      : "text-zinc-100";

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-3 hover:bg-zinc-800/60 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="w-5 text-center text-zinc-500 font-mono text-xs font-bold">
            {item.rank}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-zinc-100 text-sm">
                {item.ticker}
              </span>
              {item.is_simulated && (
                <span className="text-amber-400 text-[10px] font-medium bg-amber-950/30 px-1.5 py-0.5 rounded">
                  Simulasi
                </span>
              )}
              {item.company_name && (
                <span className="text-zinc-500 text-xs truncate hidden sm:inline">
                  {item.company_name}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {item.price !== undefined && (
            <div className="text-right hidden sm:block">
              <div className={`text-sm font-bold ${priceColor}`}>
                {item.price?.toLocaleString()}
              </div>
              {item.change_percent !== undefined && (
                <div className={`text-xs ${priceColor}`}>
                  {item.change_percent >= 0 ? "+" : ""}
                  {item.change_percent}%
                </div>
              )}
            </div>
          )}

          <div className="w-16">
            <div className="w-full bg-zinc-800 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500"
                style={{ width: `${item.score}%` }}
              />
            </div>
            <div className="text-[10px] text-zinc-500 text-center mt-0.5">
              {item.score}
            </div>
          </div>

          <span
            className={`px-2 py-0.5 rounded-full text-xs font-bold ${verdictColors[item.verdict]}`}
          >
            {item.verdict}
          </span>
        </div>
      </div>

      {item.summary && (
        <p className="text-xs text-zinc-500 mt-2 ml-8 leading-relaxed line-clamp-2">
          {item.summary}
        </p>
      )}
    </div>
  );
}

interface AIPicksProps {
  items: RankingItem[];
  maxItems?: number;
}

export function AIPicks({ items, maxItems = 5 }: AIPicksProps) {
  const picks = items.slice(0, maxItems);

  if (picks.length === 0) {
    return (
      <section>
        <h2 className="text-lg font-bold text-zinc-100 mb-3">
          Top Rekomendasi AI
        </h2>
        <p className="text-zinc-500 text-sm">Belum ada data screening.</p>
      </section>
    );
  }

  return (
    <section>
      <h2 className="text-lg font-bold text-zinc-100 mb-3">
        Top Rekomendasi AI
      </h2>
      <div className="space-y-2">
        {picks.map((item) => (
          <PickCard key={item.ticker} item={item} />
        ))}
      </div>
    </section>
  );
}
