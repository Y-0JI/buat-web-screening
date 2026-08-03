"use client";

import { useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchMarketInsight, type MarketInsightData } from "@/lib/api";

interface MarketInsightProps {
  className?: string;
}

const sentimentColors: Record<string, string> = {
  bullish: "text-green-400 bg-green-500/15",
  bearish: "text-red-400 bg-red-500/15",
  neutral: "text-zinc-400 bg-zinc-500/15",
};

const sentimentLabels: Record<string, string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Netral",
};

export function MarketInsight({ className = "" }: MarketInsightProps) {
  const [data, setData] = useState<MarketInsightData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await fetchMarketInsight();
        if (cancelled) return;
        if (res.success && res.data) {
          setData(res.data);
        } else {
          setError(res.error || "Gagal memuat insight");
        }
      } catch {
        if (!cancelled) setError("Gagal memuat insight pasar");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [attempt]);

  const retry = useCallback(() => setAttempt(a => a + 1), []);

  if (loading) {
    return (
      <Card className={className}>
        <Skeleton variant="heading" width="w-32" className="mb-2" />
        <Skeleton variant="text" className="mb-1" />
        <Skeleton variant="text" width="w-3/4" />
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-between gap-3">
          <div className="text-zinc-500 text-sm">{error || "Tidak ada data"}</div>
          {error && (
            <button
              type="button"
              onClick={retry}
              disabled={loading}
              className="shrink-0 px-2 py-1 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-300 text-xs rounded-md transition-colors"
            >
              Coba lagi
            </button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
          Insight Pasar
        </h3>
        <div className="flex items-center gap-2">
          {data.mode && (
            <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/15 text-blue-400 rounded-full font-medium">
              {data.mode}
            </span>
          )}
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
              sentimentColors[data.sentiment] || sentimentColors.neutral
            }`}
          >
            {sentimentLabels[data.sentiment] || data.sentiment}
          </span>
        </div>
      </div>
      <p className="text-sm text-zinc-300 leading-relaxed">
        {data.summary}
      </p>
    </Card>
  );
}
