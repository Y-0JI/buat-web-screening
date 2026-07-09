"use client";

import { useState, FormEvent } from "react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading: boolean;
  mode: string;
  onModeChange: (mode: string) => void;
}

const examples = [
  "Research RGAS",
  "Cari saham terbaik besok",
  "Bandingkan BBCA dan BRIS",
];

export function SearchBar({ onSearch, loading, mode, onModeChange }: SearchBarProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading) onSearch(query.trim());
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="absolute left-2 top-1/2 -translate-y-1/2 z-10">
          <select
            value={mode}
            onChange={(e) => onModeChange(e.target.value)}
            disabled={loading}
            className="bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-300 text-xs py-1.5 px-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="BSJP">BSJP</option>
            <option value="BPJS">BPJS</option>
          </select>
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tanya tentang saham..."
          className="w-full pl-20 pr-24 py-4 bg-zinc-800 border border-zinc-700 rounded-2xl text-zinc-100 placeholder-zinc-500 text-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl text-sm font-medium transition-colors"
        >
          {loading ? "Memproses..." : "Cari"}
        </button>
      </form>
      <div className="mt-4 flex flex-wrap gap-2">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => {
              setQuery(ex);
              onSearch(ex);
            }}
            disabled={loading}
            className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
