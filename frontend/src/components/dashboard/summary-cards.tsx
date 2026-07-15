import type { RankingItem } from "@/lib/api";
import { Stat } from "@/components/ui/stat";
import { Bar } from "@/components/ui/bar";

interface SummaryCardsProps {
  items: RankingItem[];
  generatedAt?: string;
}

export function SummaryCards({ items, generatedAt }: SummaryCardsProps) {
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

  const sentimentScore = total > 0
    ? Math.round(((verdictCounts.BUY - verdictCounts.SELL) / total) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat
          label="Sentimen"
          value={sentimentScore >= 0 ? `+${sentimentScore}` : `${sentimentScore}`}
          icon={
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          }
        />
        <Stat
          label="Skor Rata-rata"
          value={avgScore}
          icon={
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
        <Stat
          label="Total Saham"
          value={total}
          icon={
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          }
        />
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
              Status Data
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                dataStatus === "Live"
                  ? "bg-green-500/15 text-green-400"
                  : dataStatus === "Mix"
                    ? "bg-amber-500/15 text-amber-400"
                    : "bg-zinc-500/15 text-zinc-400"
              }`}
            >
              {dataStatus}
            </span>
          </div>
          <div className="text-xs text-zinc-500 mt-2">
            {generatedAt ? `Diperbarui ${timeAgo(generatedAt)}` : "-"}
          </div>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
            Distribusi Verdict
          </span>
        </div>
        <Bar
          variant="sentiment"
          height="sm"
          showLabel
          segments={[
            { value: verdictCounts.BUY, color: "bg-green-500", label: `BUY ${verdictCounts.BUY}` },
            { value: verdictCounts.HOLD, color: "bg-amber-500", label: `HOLD ${verdictCounts.HOLD}` },
            { value: verdictCounts.SELL, color: "bg-red-500", label: `SELL ${verdictCounts.SELL}` },
            { value: verdictCounts.AVOID, color: "bg-zinc-600", label: `AVOID ${verdictCounts.AVOID}` },
          ]}
        />
      </div>
    </div>
  );
}

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
