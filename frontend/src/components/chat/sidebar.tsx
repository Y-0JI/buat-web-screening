"use client";

import type { ThreadSummary } from "@/lib/chat";

interface Props {
  threads: ThreadSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onDelete: (id: number) => void;
}

export function Sidebar({ threads, activeId, onSelect, onNew, onDelete }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="p-3">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Percakapan baru
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
        {threads.length === 0 && (
          <p className="px-3 py-6 text-xs text-zinc-600 text-center">Belum ada percakapan</p>
        )}
        {threads.map((t) => (
          <div
            key={t.id}
            className={`group flex items-center gap-1 rounded-lg px-2.5 py-2 cursor-pointer transition-colors ${
              activeId === t.id ? "bg-zinc-800" : "hover:bg-zinc-800/60"
            }`}
            onClick={() => onSelect(t.id)}
          >
            <span className="flex-1 truncate text-sm text-zinc-300">{t.title || "Percakapan"}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(t.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-700 text-zinc-500 hover:text-red-400 transition-all"
              aria-label="Hapus"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
