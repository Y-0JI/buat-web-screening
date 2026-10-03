"use client";

import { useState, type KeyboardEvent } from "react";

interface Props {
  value: string;
  loading?: boolean;
  onSubmit: (ticker: string) => void;
}

export function TickerSearch({ value, loading, onSubmit }: Props) {
  const [text, setText] = useState("");

  const go = () => {
    const t = text.trim().toUpperCase();
    if (t && t !== value) onSubmit(t);
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") go();
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 focus-within:border-blue-500 transition-colors">
        <svg className="w-3.5 h-3.5 text-zinc-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M10 18a8 8 0 110-16 8 8 0 010 16z" />
        </svg>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Cari ticker…"
          className="w-28 bg-transparent text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none uppercase"
        />
        {loading && <span className="w-3 h-3 rounded-full border border-zinc-500 border-t-transparent animate-spin" />}
      </div>
      <button
        type="button"
        onClick={go}
        className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
      >
        Buka
      </button>
    </div>
  );
}
