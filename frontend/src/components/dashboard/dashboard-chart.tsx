"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
} from "lightweight-charts";
import type { HistoryPoint } from "@/lib/chat";
import {
  bollinger,
  ema,
  kdj,
  ma,
  macd,
  rsi,
  valueSeries,
  type LinePoint,
} from "@/lib/indicators";
import type { ChartType, IndicatorId } from "./chart-settings";

const BASE_HEIGHT = 300;
const PANEL_HEIGHT = 90;

const PANEL_ORDER: IndicatorId[] = ["volume", "value", "rsi", "macd", "kdj"];

interface Props {
  ticker: string;
  period: string;
  series: HistoryPoint[];
  chartType: ChartType;
  active: IndicatorId[];
}

function histColor(up: boolean): string {
  return up ? "rgba(34,197,94,0.45)" : "rgba(239,68,68,0.45)";
}

export function DashboardChart({ ticker, period, series, chartType, active }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const byDate = new Map<string, HistoryPoint>();
    for (const p of series) byDate.set(p.date, p);
    const points = [...byDate.values()].sort((a, b) =>
      a.date < b.date ? -1 : a.date > b.date ? 1 : 0
    );
    if (!points.length) return;

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

    if (chartType === "candlestick") {
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
    } else {
      instance
        .addSeries(LineSeries, {
          color: "#22c55e",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        .setData(points.map((p) => ({ time: p.date, value: p.close })));
    }

    const overlay = (color: string, data: LinePoint[], dashed = false) => {
      if (!data.length) return;
      instance
        .addSeries(LineSeries, {
          color,
          lineWidth: 1,
          lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        .setData(data);
    };

    if (activeSet.has("ma")) overlay("#22d3ee", ma(points, 20));
    if (activeSet.has("ema")) overlay("#f59e0b", ema(points, 20));
    if (activeSet.has("boll")) {
      const bb = bollinger(points, 20, 2);
      overlay("#71717a", bb.upper, true);
      overlay("#a1a1aa", bb.middle);
      overlay("#71717a", bb.lower, true);
    }

    panels.forEach((id, i) => {
      const paneIndex = i + 1;
      instance.addPane().setHeight(PANEL_HEIGHT);
      const line = (color: string, data: LinePoint[]) => {
        if (!data.length) return;
        instance
          .addSeries(
            LineSeries,
            { color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
            paneIndex
          )
          .setData(data);
      };

      if (id === "volume") {
        instance
          .addSeries(
            HistogramSeries,
            { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false },
            paneIndex
          )
          .setData(
            points.map((p) => ({
              time: p.date,
              value: p.volume,
              color: histColor(p.close >= p.open),
            }))
          );
      } else if (id === "value") {
        instance
          .addSeries(
            HistogramSeries,
            { priceLineVisible: false, lastValueVisible: false },
            paneIndex
          )
          .setData(
            valueSeries(points).map((p, k) => ({
              time: p.time,
              value: p.value,
              color: histColor(points[k].close >= points[k].open),
            }))
          );
      } else if (id === "rsi") {
        line("#a78bfa", rsi(points, 14));
      } else if (id === "macd") {
        const m = macd(points, 12, 26, 9);
        line("#22d3ee", m.macd);
        line("#f59e0b", m.signal);
        if (m.histogram.length) {
          instance
            .addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, paneIndex)
            .setData(
              m.histogram.map((p) => ({
                time: p.time,
                value: p.value,
                color: histColor(p.value >= 0),
              }))
            );
        }
      } else if (id === "kdj") {
        const s = kdj(points, 9, 3, 3);
        line("#22d3ee", s.k);
        line("#f59e0b", s.d);
        line("#a78bfa", s.j);
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
  }, [series, chartType, active, ticker, period]);

  return (
    <div className="w-full">
      <div className="px-1 pb-1 text-[11px] text-zinc-500">
        {ticker} · {period}
      </div>
      <div ref={ref} className="w-full" />
    </div>
  );
}
