"use client";

import { useEffect, useState } from "react";
import { getNews, type NewsItem } from "@/lib/chat";
import { NewsTable } from "./news-table";

interface Props {
  ticker: string;
  onOpenArticle: (item: NewsItem) => void;
}

export function NewsPanel({ ticker, onOpenArticle }: Props) {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setItems([]);
    setPage(1);
    setHasMore(false);
    setLoading(true);
    setReady(false);
    setError(null);
    void (async () => {
      try {
        const res = await getNews(ticker, { page: 1, perPage: 15 });
        if (cancelled) return;
        setItems(res.items);
        setHasMore(res.hasMore);
        if (!res.items.length) setError(res.error || `Belum ada berita ${ticker} di sumber yang dipantau.`);
      } catch {
        if (!cancelled) setError("Gagal memuat berita. Periksa koneksi backend.");
      } finally {
        if (!cancelled) {
          setLoading(false);
          setReady(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  const more = async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const res = await getNews(ticker, { page: page + 1, perPage: 15 });
      setItems((prev) => [...prev, ...res.items]);
      setPage((p) => p + 1);
      setHasMore(res.hasMore);
    } catch {
      /* diamkan, tombol tetap bisa diklik ulang */
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-2">
      <h4 className="text-base font-bold text-text-primary mb-2">Latest headlines</h4>
      {!ready ? (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          Memuat berita…
        </div>
      ) : error ? (
        <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          {error}
        </div>
      ) : (
        <NewsTable
          ticker={ticker}
          items={items}
          onOpen={onOpenArticle}
          hasMore={hasMore}
          loading={loading}
          onMore={more}
        />
      )}
    </div>
  );
}
