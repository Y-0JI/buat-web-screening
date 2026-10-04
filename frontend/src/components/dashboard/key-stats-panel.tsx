"use client";

import { useEffect, useState } from "react";
import { getFundamentals, type FundamentalData } from "@/lib/chat";
import { FundamentalsCard } from "../chat/fundamentals";

const cache = new Map<string, FundamentalData | null>();

export function KeyStatsPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<FundamentalData | null | undefined>(() =>
    cache.has(ticker) ? cache.get(ticker) ?? null : undefined
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cache.has(ticker)) {
      setData(cache.get(ticker) ?? null);
      setError(null);
      return;
    }
    let cancelled = false;
    setData(undefined);
    setError(null);
    void (async () => {
      try {
        const res = await getFundamentals(ticker);
        cache.set(ticker, res);
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) setError("Gagal memuat data fundamental.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (error) {
    return (
      <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-500 text-xs px-3 py-6 text-center">
        {error}
      </div>
    );
  }

  if (data === undefined) {
    return (
      <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
        Memuat data fundamental…
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
        Data fundamental {ticker} tidak tersedia.
      </div>
    );
  }

  return (
    <div className="mt-2">
      <FundamentalsCard data={data} />
    </div>
  );
}
