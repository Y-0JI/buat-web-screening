"use client";

import { useEffect, useState } from "react";
import { getNews, type NewsItem } from "@/lib/chat";
import { NewsTable } from "./news-table";

const cache = new Map<string, NewsItem[]>();

interface Props {
  ticker: string;
  onOpenArticle: (item: NewsItem) => void;
}

export function NewsPanel({ ticker, onOpenArticle }: Props) {
  const [items, setItems] = useState<NewsItem[] | undefined>(() =>
    cache.has(ticker) ? cache.get(ticker) : undefined
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cache.has(ticker)) {
      setItems(cache.get(ticker));
      setError(null);
      return;
    }
    let cancelled = false;
    setItems(undefined);
    setError(null);
    void (async () => {
      try {
        const res = await getNews(ticker, 50);
        cache.set(ticker, res.items);
        if (cancelled) return;
        setItems(res.items);
        if (!res.items.length) setError(res.error || `Belum ada berita ${ticker} di feed yang dipantau.`);
      } catch {
        if (!cancelled) setError("Gagal memuat berita. Periksa koneksi backend.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return (
    <div className="mt-2">
      <h4 className="text-base font-bold text-text-primary mb-2">Latest headlines</h4>
      {items === undefined && !error ? (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          Memuat berita…
        </div>
      ) : error ? (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          {error}
        </div>
      ) : (
        <NewsTable ticker={ticker} items={items || []} onOpen={onOpenArticle} />
      )}
    </div>
  );
}
