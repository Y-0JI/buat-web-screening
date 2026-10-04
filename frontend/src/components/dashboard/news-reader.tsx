"use client";

import { useEffect, useState } from "react";
import { getArticle, type NewsItem } from "@/lib/chat";

interface Props {
  item: NewsItem;
  onClose: () => void;
  onKeepReading: () => void;
}

export function NewsReader({ item, onClose, onKeepReading }: Props) {
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setText(null);
    void (async () => {
      try {
        const art = await getArticle(item.url);
        if (!cancelled) setText(art?.text ?? null);
      } catch {
        /* abaikan, fallback ke snippet */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [item.url]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl border border-border bg-surface-0 shadow-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-text-secondary truncate">
            News <span className="mx-1">/</span> {item.source || "Sumber"}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-2 shrink-0"
            aria-label="Tutup"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <h3 className="mt-2 text-xl font-bold text-text-primary leading-snug">
          {item.title}
        </h3>
        {(item.published || item.source) && (
          <p className="mt-1.5 text-xs text-text-muted">
            {[item.published, item.source].filter(Boolean).join(" · ")}
          </p>
        )}

        <div className="mt-4 space-y-3 text-sm leading-relaxed text-text-secondary">
          {loading ? (
            <p className="text-text-muted">Memuat artikel…</p>
          ) : text ? (
            text.split(/\n{2,}/).map((p, i) => <p key={i}>{p}</p>)
          ) : (
            <p>{item.snippet || "Artikel tidak bisa dibaca penuh."}</p>
          )}
        </div>

        <div className="mt-5 flex items-center justify-center gap-2 flex-wrap">
          {!text && !loading && (
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 rounded-lg border border-border text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-2 transition-colors"
            >
              Buka artikel
            </a>
          )}
          <button
            type="button"
            onClick={onKeepReading}
            className="px-4 py-2 rounded-lg bg-surface-2 hover:bg-surface-3 text-sm font-semibold text-text-primary transition-colors"
          >
            Keep reading
          </button>
        </div>
      </div>
    </div>
  );
}
