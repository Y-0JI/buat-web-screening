"use client";

import { type KeyboardEvent, useRef } from "react";
import { ModelPicker } from "./model-picker";
import type { ModelInfo } from "@/lib/chat";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
  streaming: boolean;
  models: ModelInfo[];
  model: string;
  onModel: (id: string) => void;
}

export function Composer({
  value, onChange, onSend, onStop, streaming, models, model, onModel,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!streaming) onSend();
    }
  };

  return (
    <div className="w-full">
      <div className="flex items-end gap-2 rounded-2xl border border-zinc-700 bg-zinc-900 px-3 py-2 focus-within:border-blue-500 transition-colors">
        <button
          type="button"
          className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
          aria-label="Lampiran"
          title="Lampiran (segera)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
        </button>

        <textarea
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          placeholder="Ada yang bisa saya bantu?"
          className="flex-1 resize-none bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none max-h-40 py-1.5"
        />

        <ModelPicker models={models} value={model} onChange={onModel} align="up" />

        {streaming ? (
          <button
            onClick={onStop}
            className="p-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-200 transition-colors"
            aria-label="Stop"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            onClick={onSend}
            disabled={!value.trim()}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white transition-colors"
            aria-label="Kirim"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        )}
      </div>
      <p className="mt-2 text-center text-[11px] text-zinc-600">
        Semua data untuk keperluan informasi. Hasil AI bukan saran keuangan.
      </p>
    </div>
  );
}
