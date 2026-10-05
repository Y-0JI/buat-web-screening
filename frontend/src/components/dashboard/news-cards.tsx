"use client";

import type { NewsItem } from "@/lib/chat";

function fmtDate(published: string | null): string {
  if (!published) return "";
  const d = new Date(published);
  if (Number.isNaN(d.getTime())) return published;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

interface Props {
  items: NewsItem[];
  onOpen: (item: NewsItem) => void;
  columns?: 2 | 3;
}

export function NewsCards({ items, onOpen, columns = 3 }: Props) {
  return (
    <div
      className={`grid gap-3 ${
        columns === 3 ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" : "grid-cols-1 sm:grid-cols-2"
      }`}
    >
      {items.map((it) => (
        <button
          key={it.url}
          type="button"
          onClick={() => onOpen(it)}
          className="text-left rounded-lg p-3 hover:bg-surface-2/60 transition-colors"
        >
          <div className="text-[11px] text-text-muted truncate">
            {fmtDate(it.published)}
            {it.source ? ` · ${it.source}` : ""}
          </div>
          <div className="mt-1 text-[13px] font-semibold leading-snug text-text-primary line-clamp-3">
            {it.title}
          </div>
        </button>
      ))}
    </div>
  );
}
