"use client";

import { useState } from "react";
import type { WatchlistItem } from "@/lib/api";

interface WatchlistSectionProps {
  items: WatchlistItem[];
  onRemove: (ticker: string) => void;
  onAdd: (ticker: string, note?: string) => void;
}

export function WatchlistSection({
  items,
  onRemove,
  onAdd,
}: WatchlistSectionProps) {
  const [input, setInput] = useState("");
  const [noteInput, setNoteInput] = useState("");
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    const ticker = input.trim().toUpperCase();
    if (!ticker || adding) return;
    setAdding(true);
    try {
      await onAdd(ticker, noteInput.trim() || undefined);
      setInput("");
      setNoteInput("");
    } finally {
      setAdding(false);
    }
  };

  return (
    <section>
      <h2 className="text-lg font-bold text-zinc-100 mb-3">Watchlist</h2>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tambah saham..."
          className="flex-1 min-w-0 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-600 transition-colors"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAdd();
          }}
          disabled={adding}
        />
        <input
          type="text"
          value={noteInput}
          onChange={(e) => setNoteInput(e.target.value)}
          placeholder="Catatan (opsional)"
          className="hidden sm:block w-32 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-600 transition-colors"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAdd();
          }}
          disabled={adding}
        />
        <button
          onClick={handleAdd}
          disabled={!input.trim() || adding}
          className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white text-sm font-medium rounded-xl transition-colors"
        >
          Tambah
        </button>
      </div>

      {items.length === 0 ? (
        <p className="text-zinc-500 text-sm">Belum ada saham di watchlist.</p>
      ) : (
        <div className="space-y-2">
          {items.map((w) => (
            <div
              key={w.id}
              className="flex items-center justify-between px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl"
            >
              <div className="min-w-0">
                <span className="text-zinc-100 font-semibold text-sm">
                  {w.ticker}
                </span>
                {w.note && (
                  <span className="text-zinc-500 text-xs ml-2 truncate">
                    {w.note}
                  </span>
                )}
              </div>
              <button
                onClick={() => onRemove(w.ticker)}
                className="text-zinc-500 hover:text-red-400 text-xs transition-colors ml-2 shrink-0"
              >
                Hapus
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
