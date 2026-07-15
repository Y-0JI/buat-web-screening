"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface MarketInsightData {
  summary: string;
  sentiment: string;
  score_avg: number | null;
  total_stocks: number;
  mode?: string;
  generated_at: string;
}

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

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/insight/market`
        );
        const json = await res.json();
        if (json.success && json.data) {
          setData(json.data);
        } else {
          setError(json.error || "Gagal memuat insight");
        }
      } catch {
        setError("Gagal memuat insight pasar");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

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
        <div className="text-zinc-500 text-sm">{error || "Tidak ada data"}</div>
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
