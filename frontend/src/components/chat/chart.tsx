"use client";

import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
} from "lightweight-charts";
import type { UIChart } from "./types";
import { bollinger, ema, macd, rsi, stochastic } from "@/lib/indicators";

type IndicatorId =
  | "ema13"
  | "ema21"
  | "ema100"
  | "ema200"
  | "bb"
  | "volume"
  | "stoch"
  | "rsi"
  | "macd";

type IndicatorDef = {
  id: IndicatorId;
  label: string;
  kind: "overlay" | "panel";
  defaultOn: boolean;
};

const INDICATORS: IndicatorDef[] = [
  { id: "ema13", label: "EMA13", kind: "overlay", defaultOn: true },
  { id: "ema21", label: "EMA21", kind: "overlay", defaultOn: true },
  { id: "ema100", label: "EMA100", kind: "overlay", defaultOn: true },
  { id: "ema200", label: "EMA200", kind: "overlay", defaultOn: true },
  { id: "bb", label: "BB", kind: "overlay", defaultOn: false },
  { id: "volume", label: "Volume", kind: "panel", defaultOn: true },
  { id: "stoch", label: "Stoch", kind: "panel", defaultOn: true },
  { id: "rsi", label: "RSI", kind: "panel", defaultOn: false },
  { id: "macd", label: "MACD", kind: "panel", defaultOn: false },
];

const PANEL_ORDER: IndicatorId[] = ["volume", "stoch", "rsi", "macd"];
const STORAGE_KEY = "idx_chart_indicators";
const BASE_HEIGHT = 256;
const PANEL_HEIGHT = 80;

const EMA_COLORS: Record<string, string> = {
  ema13: "#22d3ee",
  ema21: "#f59e0b",
  ema100: "#a78bfa",
  ema200: "#f472b6",
};

function defaults(): IndicatorId[] {
  return INDICATORS.filter((i) => i.defaultOn).map((i) => i.id);
}

function loadActive(): IndicatorId[] {
  if (typeof window === "undefined") return defaults();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return defaults();
    return parsed.filter((x): x is IndicatorId =>
      INDICATORS.some((i) => i.id === x)
    );
  } catch {
    return defaults();
  }
}

export function PriceChart({ chart }: { chart: UIChart }) {
  const ref = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState<IndicatorId[]>(loadActive);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(active));
    } catch {
      /* abaikan */
    }
  }, [active]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const activeSet = new Set(active);
    const panels = PANEL_ORDER.filter((id) => activeSet.has(id));
    const height = BASE_HEIGHT + PANEL_HEIGHT * panels.length;

    const instance = createChart(el, {
      width: el.clientWidth || 600,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#a1a1aa",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(63,63,70,0.35)" },
        horzLines: { color: "rgba(63,63,70,0.35)" },
      },
      rightPriceScale: { borderColor: "rgba(63,63,70,0.6)" },
      timeScale: { borderColor: "rgba(63,63,70,0.6)" },
    });

    // lightweight-charts wajib urut naik & tanggal unik.
    const byDate = new Map<string, (typeof chart.series)[number]>();
    for (const p of chart.series) byDate.set(p.date, p);
    const points = [...byDate.values()].sort((a, b) =>
      a.date < b.date ? -1 : a.date > b.date ? 1 : 0
    );

    instance
      .addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      })
      .setData(
        points.map((p) => ({
          time: p.date,
          open: p.open,
          high: p.high,
          low: p.low,
          close: p.close,
        }))
      );

    const overlay = (
      color: string,
      data: ReturnType<typeof ema>,
      dashed = false
    ) =>
      instance
        .addSeries(LineSeries, {
          color,
          lineWidth: 1,
          lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        .setData(data);

    if (activeSet.has("ema13")) overlay(EMA_COLORS.ema13, ema(points, 13));
    if (activeSet.has("ema21")) overlay(EMA_COLORS.ema21, ema(points, 21));
    if (activeSet.has("ema100")) overlay(EMA_COLORS.ema100, ema(points, 100));
    if (activeSet.has("ema200")) overlay(EMA_COLORS.ema200, ema(points, 200));

    if (activeSet.has("bb")) {
      const bb = bollinger(points, 20, 2);
      overlay("#71717a", bb.upper, true);
      overlay("#a1a1aa", bb.middle);
      overlay("#71717a", bb.lower, true);
    }

    panels.forEach((id, i) => {
      const paneIndex = i + 1;
      instance.addPane().setHeight(PANEL_HEIGHT);

      if (id === "volume") {
        instance
          .addSeries(
            HistogramSeries,
            {
              priceFormat: { type: "volume" },
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex
          )
          .setData(
            points.map((p) => ({
              time: p.date,
              value: p.volume,
              color:
                p.close >= p.open
                  ? "rgba(34,197,94,0.45)"
                  : "rgba(239,68,68,0.45)",
            }))
          );
      } else if (id === "stoch") {
        const st = stochastic(points, 14, 3, 3);
        instance
          .addSeries(
            LineSeries,
            {
              color: "#22d3ee",
              lineWidth: 1,
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex
          )
          .setData(st.k);
        instance
          .addSeries(
            LineSeries,
            {
              color: "#f59e0b",
              lineWidth: 1,
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex
          )
          .setData(st.d);
      } else if (id === "rsi") {
        instance
          .addSeries(
            LineSeries,
            {
              color: "#a78bfa",
              lineWidth: 1,
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex
          )
          .setData(rsi(points, 14));
      } else if (id === "macd") {
        const m = macd(points, 12, 26, 9);
        instance
          .addSeries(
            LineSeries,
            {
              color: "#22d3ee",
              lineWidth: 1,
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex
          )
          .setData(m.macd);
        instance
          .addSeries(
            LineSeries,
            {
              color: "#f59e0b",
              lineWidth: 1,
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex
          )
          .setData(m.signal);
        instance
          .addSeries(
            HistogramSeries,
            { priceLineVisible: false, lastValueVisible: false },
            paneIndex
          )
          .setData(
            m.histogram.map((p) => ({
              time: p.time,
              value: p.value,
              color:
                p.value >= 0
                  ? "rgba(34,197,94,0.45)"
                  : "rgba(239,68,68,0.45)",
            }))
          );
      }
    });

    instance.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      instance.applyOptions({ width: el.clientWidth });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      instance.remove();
    };
  }, [chart, active]);

  const toggle = (id: IndicatorId) =>
    setActive((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  return (
    <div className="my-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-1">
      <div className="px-2 py-1 text-[11px] text-zinc-400">
        {chart.ticker} · {chart.period}
      </div>
      <div className="flex flex-wrap gap-1 px-2 pb-1">
        {INDICATORS.map((ind) => {
          const on = active.includes(ind.id);
          return (
            <button
              key={ind.id}
              type="button"
              onClick={() => toggle(ind.id)}
              className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors ${
                on
                  ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
                  : "border-zinc-700 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {ind.label}
            </button>
          );
        })}
      </div>
      <div ref={ref} className="w-full" />
    </div>
  );
}
