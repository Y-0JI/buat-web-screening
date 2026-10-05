"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
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
import type { ChartType, IndicatorId, OverlayParams } from "./chart-settings";
import { CHART_CHROME } from "./chart-chrome";
import { useTheme } from "../theme/theme-provider";
import { fmtRp } from "@/lib/format";

const BASE_HEIGHT = 300;
const PANEL_HEIGHT = 90;

const PANEL_ORDER: IndicatorId[] = ["volume", "value", "rsi", "macd", "kdj"];

interface Props {
  ticker: string;
  period: string;
  series: HistoryPoint[];
  chartType: ChartType;
  active: IndicatorId[];
  params: OverlayParams;
  livePrice: number | null;
}

interface LegendRow {
  label: string;
  color: string;
  values: { color: string; value: number }[];
}

function histColor(up: boolean): string {
  return up ? "rgba(34,197,94,0.45)" : "rgba(239,68,68,0.45)";
}

export function DashboardChart({ ticker, period, series, chartType, active, params, livePrice }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mainSeriesRef = useRef<ISeriesApi<"Candlestick" | "Line"> | null>(null);
  const priceLineRef = useRef<IPriceLine | null>(null);
  const lastDateRef = useRef<string | null>(null);
  const { theme } = useTheme();
  const chrome = CHART_CHROME[theme];

  const points = useMemo(() => {
    const byDate = new Map<string, HistoryPoint>();
    for (const p of series) byDate.set(p.date, p);
    return [...byDate.values()].sort((a, b) =>
      a.date < b.date ? -1 : a.date > b.date ? 1 : 0
    );
  }, [series]);

  const legend = useMemo<LegendRow[]>(() => {
    if (!points.length) return [];
    const rows: LegendRow[] = [];
    const lastOf = (data: LinePoint[]): number | null =>
      data.length ? data[data.length - 1].value : null;
    if (active.includes("ma")) {
      for (const line of params.ma) {
        if (!line.on) continue;
        const v = lastOf(ma(points, line.period));
        if (v != null)
          rows.push({ label: `MA (${line.period})`, color: line.color, values: [{ color: line.color, value: v }] });
      }
    }
    if (active.includes("ema")) {
      for (const line of params.ema) {
        if (!line.on) continue;
        const v = lastOf(ema(points, line.period));
        if (v != null)
          rows.push({ label: `EMA (${line.period})`, color: line.color, values: [{ color: line.color, value: v }] });
      }
    }
    if (active.includes("boll")) {
      const bb = bollinger(points, params.boll.length, params.boll.mult);
      const mid = lastOf(bb.middle);
      const up = lastOf(bb.upper);
      const lo = lastOf(bb.lower);
      if (mid != null && up != null && lo != null) {
        rows.push({
          label: `BOLL (${params.boll.length}, ${params.boll.mult})`,
          color: params.boll.colorMid,
          values: [
            { color: params.boll.colorMid, value: mid },
            { color: params.boll.colorBand, value: up },
            { color: params.boll.colorBand, value: lo },
          ],
        });
      }
    }
    return rows;
  }, [points, active, params]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !points.length) return;

    const activeSet = new Set(active);
    const panels = PANEL_ORDER.filter((id) => activeSet.has(id));
    const height = BASE_HEIGHT + PANEL_HEIGHT * panels.length;

    const instance = createChart(el, {
      width: el.clientWidth || 600,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: chrome.textColor,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: chrome.grid },
        horzLines: { color: chrome.grid },
      },
      rightPriceScale: { borderColor: chrome.border },
      timeScale: { borderColor: chrome.border },
    });

    if (chartType === "candlestick") {
      const candles = instance.addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });
      candles.setData(
        points.map((p) => ({
          time: p.date,
          open: p.open,
          high: p.high,
          low: p.low,
          close: p.close,
        }))
      );
      mainSeriesRef.current = candles;
    } else {
      const line = instance.addSeries(LineSeries, {
        color: "#22c55e",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      line.setData(points.map((p) => ({ time: p.date, value: p.close })));
      mainSeriesRef.current = line;
    }
    lastDateRef.current = points[points.length - 1].date;

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

    if (activeSet.has("ma")) {
      for (const line of params.ma) {
        if (line.on) overlay(line.color, ma(points, line.period));
      }
    }
    if (activeSet.has("ema")) {
      for (const line of params.ema) {
        if (line.on) overlay(line.color, ema(points, line.period));
      }
    }
    if (activeSet.has("boll")) {
      const bb = bollinger(points, params.boll.length, params.boll.mult);
      overlay(params.boll.colorBand, bb.upper, true);
      overlay(params.boll.colorMid, bb.middle);
      overlay(params.boll.colorBand, bb.lower, true);
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
  }, [points, chartType, active, params, chrome, ticker, period]);

  // Harga live: update candle terakhir + garis harga tanpa rebuild chart.
  useEffect(() => {
    const main = mainSeriesRef.current;
    if (!main) return;
    const prevLine = priceLineRef.current;
    if (prevLine) {
      try {
        main.removePriceLine(prevLine);
      } catch {
        /* abaikan */
      }
      priceLineRef.current = null;
    }
    if (livePrice == null) return;
    const isUp = points.length > 1 ? livePrice >= points[points.length - 2].close : true;
    const color = isUp ? "#22c55e" : "#ef4444";
    try {
      const bar = points[points.length - 1];
      if (chartType === "candlestick") {
        (main as ISeriesApi<"Candlestick">).update({
          time: bar.date,
          open: bar.open,
          high: Math.max(bar.high, livePrice),
          low: Math.min(bar.low, livePrice),
          close: livePrice,
        });
      } else {
        (main as ISeriesApi<"Line">).update({ time: bar.date, value: livePrice });
      }
      priceLineRef.current = main.createPriceLine({
        price: livePrice,
        color,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "",
      });
    } catch {
      /* abaikan */
    }
  }, [livePrice, points, chartType]);

  return (
    <div className="w-full">
      {legend.length > 0 && (
        <div className="flex gap-3 flex-wrap text-[11px] px-1 pb-1">
          {legend.map((row) => (
            <span key={row.label} className="flex items-center gap-1">
              <span style={{ color: row.color }}>{row.label}</span>
              {row.values.map((v, i) => (
                <span key={i} style={{ color: v.color }}>
                  {fmtRp(v.value)}
                </span>
              ))}
            </span>
          ))}
        </div>
      )}
      <div ref={ref} className="w-full" />
    </div>
  );
}
