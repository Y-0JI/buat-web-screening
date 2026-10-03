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

export interface OverlayLine {
  on: boolean;
  period: number;
  color: string;
}

export interface BollParams {
  length: number;
  mult: number;
  colorMid: string;
  colorBand: string;
}

export interface OverlayParams {
  ma: OverlayLine[];
  ema: OverlayLine[];
  boll: BollParams;
}

export const DEFAULT_OVERLAY: OverlayParams = {
  ma: [
    { on: true, period: 5, color: "#8bc34a" },
    { on: true, period: 10, color: "#3949ab" },
    { on: true, period: 20, color: "#ff9800" },
  ],
  ema: [
    { on: true, period: 5, color: "#ec407a" },
    { on: true, period: 10, color: "#42a5f5" },
    { on: true, period: 20, color: "#ab47bc" },
  ],
  boll: { length: 20, mult: 2, colorMid: "#ffb300", colorBand: "#7e57c2" },
};

export const OVERLAY_KEY = "idx_overlay_params";

function validLine(v: unknown, fb: OverlayLine): OverlayLine {
  if (typeof v !== "object" || v === null) return fb;
  const o = v as Record<string, unknown>;
  const period =
    typeof o.period === "number" && Number.isFinite(o.period) && o.period >= 2
      ? Math.min(200, Math.round(o.period))
      : fb.period;
  return {
    on: typeof o.on === "boolean" ? o.on : fb.on,
    period,
    color: typeof o.color === "string" && /^#[0-9a-fA-F]{6}$/.test(o.color) ? o.color : fb.color,
  };
}

function validLines(v: unknown, fb: OverlayLine[]): OverlayLine[] {
  if (!Array.isArray(v) || v.length !== fb.length) return fb;
  return v.map((x, i) => validLine(x, fb[i]));
}

/** Normalisasi params dari localStorage (tahan format lama/rusak). */
export function normalizeOverlay(raw: unknown): OverlayParams {
  if (typeof raw !== "object" || raw === null) return DEFAULT_OVERLAY;
  const o = raw as Record<string, unknown>;
  const b = o.boll as Record<string, unknown> | undefined;
  const num = (v: unknown, fb: number, min: number, max: number) =>
    typeof v === "number" && Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : fb;
  const col = (v: unknown, fb: string) =>
    typeof v === "string" && /^#[0-9a-fA-F]{6}$/.test(v) ? v : fb;
  return {
    ma: validLines(o.ma, DEFAULT_OVERLAY.ma),
    ema: validLines(o.ema, DEFAULT_OVERLAY.ema),
    boll: {
      length: Math.round(num(b?.length, 20, 2, 200)),
      mult: num(b?.mult, 2, 0.5, 5),
      colorMid: col(b?.colorMid, DEFAULT_OVERLAY.boll.colorMid),
      colorBand: col(b?.colorBand, DEFAULT_OVERLAY.boll.colorBand),
    },
  };
}

type ModalKind = "ma" | "ema" | "boll" | null;

const MODAL_TITLE: Record<"ma" | "ema" | "boll", string> = {
  ma: "Moving Average Settings",
  ema: "EMA Settings",
  boll: "BOLL Settings",
};

interface Props {
  active: IndicatorId[];
  onToggle: (id: IndicatorId) => void;
  params: OverlayParams;
  onSaveParams: (p: OverlayParams) => void;
  chartType: ChartType;
  onChartType: (t: ChartType) => void;
}

function Check({ on }: { on: boolean }) {
  return (
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
  );
}

function NumField({
  value,
  min,
  max,
  step = 1,
  onCommit,
  aria,
}: {
  value: number;
  min: number;
  max: number;
  step?: number;
  onCommit: (v: number) => void;
  aria: string;
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      aria-label={aria}
      onChange={(e) => {
        const v = e.target.valueAsNumber;
        if (Number.isFinite(v)) onCommit(Math.min(max, Math.max(min, v)));
      }}
      className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-2.5 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
    />
  );
}

function ColorField({ value, onCommit, aria }: { value: string; onCommit: (v: string) => void; aria: string }) {
  return (
    <input
      type="color"
      value={value}
      aria-label={aria}
      onChange={(e) => onCommit(e.target.value)}
      className="w-7 h-7 shrink-0 rounded cursor-pointer bg-transparent border border-zinc-700 p-0.5"
    />
  );
}

export function ChartSettings({ active, onToggle, params, onSaveParams, chartType, onChartType }: Props) {
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState<ModalKind>(null);
  const [draft, setDraft] = useState<OverlayParams>(DEFAULT_OVERLAY);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const openModal = (kind: "ma" | "ema" | "boll") => {
    setDraft(JSON.parse(JSON.stringify(params)) as OverlayParams);
    setModal(kind);
    setOpen(false);
  };

  const closeModal = () => setModal(null);

  const saveModal = () => {
    onSaveParams(normalizeOverlay(draft));
    setModal(null);
  };

  const resetModal = () => {
    if (!modal) return;
    setDraft((d) => ({ ...d, [modal]: DEFAULT_OVERLAY[modal] }));
  };

  const setLine = (kind: "ma" | "ema", i: number, patch: Partial<OverlayLine>) =>
    setDraft((d) => ({
      ...d,
      [kind]: d[kind].map((l, k) => (k === i ? { ...l, ...patch } : l)),
    }));

  const lineLabel = (kind: "ma" | "ema", i: number) =>
    `${kind === "ma" ? "MA" : "EMA"}${i + 1}`;

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
              const hasSub = id === "ma" || id === "ema" || id === "boll";
              return (
                <div
                  key={id}
                  className="flex items-center rounded-lg hover:bg-zinc-800 transition-colors"
                >
                  <button
                    type="button"
                    onClick={() => onToggle(id)}
                    className="flex-1 flex items-center gap-2.5 px-2 py-1.5 text-left"
                  >
                    <Check on={on} />
                    <span className="text-sm text-zinc-200">{INDICATOR_LABELS[id]}</span>
                  </button>
                  {hasSub && (
                    <button
                      type="button"
                      onClick={() => openModal(id)}
                      className="p-1.5 text-zinc-500 hover:text-zinc-200"
                      aria-label={`Atur ${INDICATOR_LABELS[id]}`}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  )}
                </div>
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

      {modal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={closeModal}
        >
          <div
            className="w-full max-w-sm rounded-xl border border-zinc-700 bg-zinc-900 shadow-xl p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-zinc-100">{MODAL_TITLE[modal]}</h3>
              <button
                type="button"
                onClick={closeModal}
                className="p-1 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
                aria-label="Tutup"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {(modal === "ma" || modal === "ema") && (
              <div className="space-y-2">
                {draft[modal].map((line, i) => (
                  <div key={i} className="flex items-center gap-2.5">
                    <button
                      type="button"
                      onClick={() => setLine(modal, i, { on: !line.on })}
                      className="flex items-center gap-2 w-16 shrink-0"
                      aria-label={`${lineLabel(modal, i)} nyala/mati`}
                    >
                      <Check on={line.on} />
                      <span className="text-sm text-zinc-200">{lineLabel(modal, i)}</span>
                    </button>
                    <NumField
                      value={line.period}
                      min={2}
                      max={200}
                      aria={`${lineLabel(modal, i)} periode`}
                      onCommit={(v) => setLine(modal, i, { period: Math.round(v) })}
                    />
                    <ColorField
                      value={line.color}
                      aria={`${lineLabel(modal, i)} warna`}
                      onCommit={(v) => setLine(modal, i, { color: v })}
                    />
                  </div>
                ))}
              </div>
            )}

            {modal === "boll" && (
              <div className="space-y-2">
                <div className="flex items-center gap-2.5">
                  <span className="text-sm text-zinc-200 w-20 shrink-0">Length</span>
                  <NumField
                    value={draft.boll.length}
                    min={2}
                    max={200}
                    aria="BOLL length"
                    onCommit={(v) => setDraft((d) => ({ ...d, boll: { ...d.boll, length: Math.round(v) } }))}
                  />
                  <ColorField
                    value={draft.boll.colorMid}
                    aria="BOLL warna tengah"
                    onCommit={(v) => setDraft((d) => ({ ...d, boll: { ...d.boll, colorMid: v } }))}
                  />
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-sm text-zinc-200 w-20 shrink-0">Multiplier</span>
                  <NumField
                    value={draft.boll.mult}
                    min={0.5}
                    max={5}
                    step={0.5}
                    aria="BOLL multiplier"
                    onCommit={(v) => setDraft((d) => ({ ...d, boll: { ...d.boll, mult: v } }))}
                  />
                  <ColorField
                    value={draft.boll.colorBand}
                    aria="BOLL warna pita"
                    onCommit={(v) => setDraft((d) => ({ ...d, boll: { ...d.boll, colorBand: v } }))}
                  />
                </div>
              </div>
            )}

            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={resetModal}
                className="flex-1 px-3 py-2 rounded-lg border border-zinc-600 text-sm font-semibold text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                Reset
              </button>
              <button
                type="button"
                onClick={saveModal}
                className="flex-1 px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-sm font-semibold text-white transition-colors"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
