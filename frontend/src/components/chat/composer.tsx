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
      <div className="rounded-3xl bg-surface-1 px-4 pt-3 pb-2.5">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          placeholder="Tanyakan apa saja"
          className="w-full resize-none bg-transparent text-sm text-text-primary placeholder-text-muted focus:outline-none max-h-40"
        />
        <div className="mt-1.5 flex items-center justify-between">
          <button
            type="button"
            className="p-1.5 rounded-full text-text-secondary hover:text-text-primary hover:bg-surface-2 transition-colors"
            aria-label="Lampiran"
            title="Lampiran (segera)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>

          <div className="flex items-center gap-1.5">
            <ModelPicker models={models} value={model} onChange={onModel} align="up" />

            {streaming ? (
              <button
                onClick={onStop}
                className="p-2.5 rounded-full bg-surface-3 hover:bg-surface-2 text-text-primary transition-colors"
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
                className="p-2.5 rounded-full bg-surface-3 hover:bg-surface-2 disabled:bg-surface-1 disabled:text-text-muted text-text-primary transition-colors"
                aria-label="Kirim"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-text-muted">
        Semua data untuk keperluan informasi. Hasil AI bukan saran keuangan.
      </p>
    </div>
  );
}
