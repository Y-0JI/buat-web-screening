"use client";

import { useState } from "react";
import type { NewsItem } from "@/lib/chat";

const VISIBLE_DEFAULT = 15;

function fmtDate(published: string | null): string {
  if (!published) return "-";
  const d = new Date(published);
  if (Number.isNaN(d.getTime())) return published;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

interface Props {
  ticker: string;
  items: NewsItem[];
  onOpen: (item: NewsItem) => void;
}

export function NewsTable({ ticker, items, onOpen }: Props) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? items : items.slice(0, VISIBLE_DEFAULT);
  if (!items.length) {
    return (
      <div className="rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
        Belum ada berita {ticker} di feed yang dipantau.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-surface-1 px-3 py-2.5">
      <div className="flex items-center gap-2 flex-wrap mb-1.5">
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-surface-2 text-text-primary">
          All
        </span>
        {!expanded && items.length > VISIBLE_DEFAULT && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="px-3 py-1 text-xs text-text-secondary hover:text-text-primary transition-colors"
          >
            More in News Flow ›
          </button>
        )}
      </div>
      <div className="max-h-[480px] overflow-y-auto">
        <table className="w-full text-[13px]">
          <thead className="sticky top-0 bg-surface-1">
            <tr className="text-xs text-text-muted">
              <td className="py-1.5 pr-2 whitespace-nowrap">Time</td>
              <td className="py-1.5 pr-2">Instrument</td>
              <td className="py-1.5 pr-2">Headline</td>
              <td className="py-1.5 text-right">Provider</td>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {shown.map((it) => (
              <tr key={it.url}>
                <td className="py-2.5 pr-3 text-xs text-text-muted whitespace-nowrap">
                  {fmtDate(it.published)}
                </td>
                <td className="py-2.5 pr-3">
                  <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-surface-2 text-text-primary">
                    {ticker}
                  </span>
                </td>
                <td className="py-2.5 pr-3">
                  <button
                    type="button"
                    onClick={() => onOpen(it)}
                    className="text-left font-semibold text-text-primary hover:text-emerald-500 transition-colors"
                  >
                    {it.title}
                  </button>
                </td>
                <td className="py-2.5 text-right text-xs text-text-muted whitespace-nowrap">
                  {it.source || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
