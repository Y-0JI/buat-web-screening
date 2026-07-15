"use client";

import type { VisionReport } from "@/lib/api";
import { Card, Badge, Section } from "@/components/ui";

export function VisionAnalysisView({ data }: { data: VisionReport }) {
  const trendColors: Record<string, string> = {
    uptrend: "text-green-400",
    downtrend: "text-red-400",
    sideways: "text-amber-400",
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-6 space-y-4">
      <Card padding="lg">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-zinc-100">Analisis Visual</h2>
          <p className="text-zinc-500 text-sm mt-1">{data.file_name}</p>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-4">
          {data.trend && (
            <div className="bg-zinc-800 rounded-xl p-3 text-center">
              <div className="text-xs text-zinc-500 mb-1">Trend</div>
              <div className={`text-lg font-bold capitalize ${trendColors[data.trend] || "text-zinc-100"}`}>
                {data.trend}
              </div>
            </div>
          )}
          {data.support_level != null && (
            <div className="bg-zinc-800 rounded-xl p-3 text-center">
              <div className="text-xs text-zinc-500 mb-1">Support</div>
              <div className="text-lg font-bold text-zinc-100">{data.support_level.toLocaleString()}</div>
            </div>
          )}
          {data.resistance_level != null && (
            <div className="bg-zinc-800 rounded-xl p-3 text-center">
              <div className="text-xs text-zinc-500 mb-1">Resistance</div>
              <div className="text-lg font-bold text-zinc-100">{data.resistance_level.toLocaleString()}</div>
            </div>
          )}
        </div>

        <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">{data.analysis_text}</p>
      </Card>

      {data.patterns_detected.length > 0 && (
        <Section title="Pattern Terdeteksi" defaultOpen>
          <div className="flex flex-wrap gap-2">
            {data.patterns_detected.map((p, i) => (
              <Badge key={i} variant="mode" size="sm">{p}</Badge>
            ))}
          </div>
        </Section>
      )}

      <p className="text-xs text-zinc-600 italic text-center">{data.disclaimer}</p>
    </div>
  );
}
