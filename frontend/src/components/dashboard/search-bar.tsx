"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { searchTickers, type TickerSuggestion } from "@/lib/chat";

export interface PinnedTicker {
  code: string;
  name?: string;
}

interface Props {
  value: string;
  onSelect: (ticker: string) => void;
  // Selalu tampil di atas hasil (mis. IHSG) — bisa dibuka tanpa mengetik.
  pinned?: PinnedTicker[];
}

export function SearchBar({ value, onSelect, pinned = [] }: Props) {
  const [text, setText] = useState("");
  const [results, setResults] = useState<TickerSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  useEffect(() => {
    const q = text.trim();
    if (q.length < 2) {
      abortRef.current?.abort();
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const timer = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const rows = await searchTickers(q, controller.signal);
        setResults(rows);
        setHighlight(0);
        setOpen(true);
      } catch {
        /* dibatalkan / gagal: diamkan */
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      abortRef.current?.abort();
    };
  }, [text]);

  const choose = (code: string) => {
    setOpen(false);
    setText("");
    setResults([]);
    if (code !== value) onSelect(code);
  };

  // pinned selalu di atas; hasil yang kodenya sama disembunyikan agar tidak dobel.
  const pinnedCodes = new Set(pinned.map((p) => p.code));
  const items = [
    ...pinned.map((p) => ({ code: p.code, name: p.name ?? "" })),
    ...results
      .filter((r) => !pinnedCodes.has(r.code))
      .map((r) => ({ code: r.code, name: r.name || "" })),
  ];

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && items.length) {
      e.preventDefault();
      setHighlight((h) => (h + 1) % items.length);
    } else if (e.key === "ArrowUp" && items.length) {
      e.preventDefault();
      setHighlight((h) => (h - 1 + items.length) % items.length);
    } else if (e.key === "Enter" && open && items.length) {
      e.preventDefault();
      choose(items[Math.min(highlight, items.length - 1)].code);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="relative w-full max-w-md" ref={ref}>
      <div className="flex items-center gap-2 rounded-lg bg-surface-1 px-3 py-2">
        <svg className="w-4 h-4 text-text-muted shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M10 18a8 8 0 110-16 8 8 0 010 16z" />
        </svg>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          onFocus={() => items.length && setOpen(true)}
          placeholder="Cari brand, simbol, atau nama…"
          aria-label="Cari emiten"
          className="w-full bg-transparent text-sm text-text-primary placeholder-text-muted focus:outline-none"
        />
        {loading && (
          <span className="w-3.5 h-3.5 shrink-0 rounded-full border border-border border-t-transparent animate-spin" />
        )}
      </div>

      {open && (items.length > 0 || text.trim().length >= 2) && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-40 max-h-72 overflow-y-auto rounded-xl border border-border bg-surface-1 shadow-xl py-1">
          {items.length === 0 && !loading ? (
            <div className="px-3 py-2.5 text-xs text-text-muted">Tidak ada hasil.</div>
          ) : (
            items.map((r, i) => (
              <button
                key={r.code}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => choose(r.code)}
                onMouseEnter={() => setHighlight(i)}
                className={`w-full flex items-baseline gap-2 px-3 py-2 text-left transition-colors ${
                  i === highlight ? "bg-surface-2" : ""
                }`}
              >
                <span className="text-sm font-bold text-text-primary shrink-0">{r.code}</span>
                <span className="text-xs text-text-secondary truncate">{r.name}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
