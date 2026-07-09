"use client";

import type { VisionReport } from "@/lib/api";

export function VisionAnalysisView({ data }: { data: VisionReport }) {
  const trendColors: Record<string, string> = {
    uptrend: "text-emerald-400",
    downtrend: "text-red-400",
    sideways: "text-amber-400",
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-6 p-6 bg-zinc-900 border border-zinc-800 rounded-2xl">
      <div className="mb-4">
        <h2 className="text-xl font-bold text-zinc-100">
          Analisis Visual
        </h2>
        <p className="text-zinc-500 text-sm mt-1">{data.file_name}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {data.trend && (
          <div className="bg-zinc-800 rounded-xl p-3">
            <div className="text-xs text-zinc-500 mb-1">Trend</div>
            <div className={`text-lg font-bold capitalize ${trendColors[data.trend] || "text-zinc-100"}`}>
              {data.trend}
            </div>
          </div>
        )}
        {data.support_level !== null && data.support_level !== undefined && (
          <div className="bg-zinc-800 rounded-xl p-3">
            <div className="text-xs text-zinc-500 mb-1">Support</div>
            <div className="text-lg font-bold text-zinc-100">
              {data.support_level.toLocaleString()}
            </div>
          </div>
        )}
        {data.resistance_level !== null && data.resistance_level !== undefined && (
          <div className="bg-zinc-800 rounded-xl p-3">
            <div className="text-xs text-zinc-500 mb-1">Resistance</div>
            <div className="text-lg font-bold text-zinc-100">
              {data.resistance_level.toLocaleString()}
            </div>
          </div>
        )}
      </div>

      {data.patterns_detected.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-2">
            Pattern Terdeteksi
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.patterns_detected.map((p, i) => (
              <span
                key={i}
                className="px-3 py-1 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-200"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="p-4 bg-zinc-800 rounded-xl mb-4">
        <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-line">
          {data.analysis_text}
        </p>
      </div>

      <p className="text-xs text-zinc-600 italic">{data.disclaimer}</p>
    </div>
  );
}
