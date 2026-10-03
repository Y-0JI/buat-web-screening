"use client";

import { useEffect, useRef, useState } from "react";

export type IndicatorId =
  | "ma"
  | "ema"
  | "boll"
  | "volume"
  | "value"
  | "rsi"
  | "macd"
  | "kdj";

export type ChartType = "candlestick" | "line";

export const INDICATOR_LABELS: Record<IndicatorId, string> = {
  ma: "MA",
  ema: "EMA",
  boll: "BOLL",
  volume: "Volume",
  value: "Value",
  rsi: "RSI",
  macd: "MACD",
  kdj: "KDJ",
};

export const INDICATOR_IDS = Object.keys(INDICATOR_LABELS) as IndicatorId[];

export const DEFAULT_ACTIVE: IndicatorId[] = ["volume"];

interface Props {
  active: IndicatorId[];
  onToggle: (id: IndicatorId) => void;
  chartType: ChartType;
  onChartType: (t: ChartType) => void;
}

export function ChartSettings({ active, onToggle, chartType, onChartType }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
        aria-label="Pengaturan chart"
        title="Pengaturan chart"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M10.343 3.94a1.5 1.5 0 012.314 0l.14.17a1 1 0 00.871.34l.214-.035a1.5 1.5 0 011.5 1.05l.064.21a1 1 0 00.65.65l.211.064a1.5 1.5 0 011.05 1.5l-.036.214a1 1 0 00.341.871l.17.14a1.5 1.5 0 010 2.314l-.17.14a1 1 0 00-.34.871l.035.214a1.5 1.5 0 01-1.05 1.5l-.21.064a1 1 0 00-.65.65l-.064.211a1.5 1.5 0 01-1.5 1.05l-.214-.036a1 1 0 00-.871.341l-.14.17a1.5 1.5 0 01-2.314 0l-.14-.17a1 1 0 00-.871-.34l-.214.035a1.5 1.5 0 01-1.5-1.05l-.064-.21a1 1 0 00-.65-.65l-.211-.064a1.5 1.5 0 01-1.05-1.5l.036-.214a1 1 0 00-.341-.871l-.17-.14a1.5 1.5 0 010-2.314l.17-.14a1 1 0 00.34-.871l-.035-.214a1.5 1.5 0 011.05-1.5l.21-.064a1 1 0 00.65-.65l.064-.211a1.5 1.5 0 011.5-1.05l.214.036a1 1 0 00.871-.341l.14-.17z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 bottom-full mb-2 z-30 w-56 rounded-xl border border-zinc-700 bg-zinc-900 shadow-xl p-2">
          <div className="px-2 py-1.5 text-xs font-semibold text-zinc-200">
            Show Indicator
          </div>
          <div className="max-h-64 overflow-y-auto">
            {INDICATOR_IDS.map((id) => {
              const on = active.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onToggle(id)}
                  className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-left hover:bg-zinc-800 transition-colors"
                >
                  <span
                    className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 transition-colors ${
                      on ? "border-emerald-500 bg-emerald-500" : "border-zinc-600"
                    }`}
                  >
                    {on && (
                      <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3.5} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </span>
                  <span className="text-sm text-zinc-200">{INDICATOR_LABELS[id]}</span>
                </button>
              );
            })}
          </div>

          <div className="mt-1 pt-1 border-t border-zinc-800">
            <div className="px-2 py-1.5 text-xs font-semibold text-zinc-200">
              Chart Type
            </div>
            {(["candlestick", "line"] as ChartType[]).map((t) => {
              const on = chartType === t;
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => onChartType(t)}
                  className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-left hover:bg-zinc-800 transition-colors"
                >
                  <span
                    className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 transition-colors ${
                      on ? "border-emerald-500 bg-emerald-500" : "border-zinc-600"
                    }`}
                  >
                    {on && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </span>
                  <span className="text-sm text-zinc-200 capitalize">{t}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
