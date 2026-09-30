"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  createChart,
} from "lightweight-charts";
import type { UIChart } from "./types";

export function PriceChart({ chart }: { chart: UIChart }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const instance = createChart(el, {
      width: el.clientWidth || 600,
      height: 256,
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

    const candles = instance.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    // lightweight-charts wajib urut naik & tanggal unik.
    const byDate = new Map<string, (typeof chart.series)[number]>();
    for (const p of chart.series) byDate.set(p.date, p);
    const points = [...byDate.values()].sort((a, b) =>
      a.date < b.date ? -1 : a.date > b.date ? 1 : 0
    );

    candles.setData(
      points.map((p) => ({
        time: p.date,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      }))
    );

    const volume = instance.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volume.setData(
      points.map((p) => ({
        time: p.date,
        value: p.volume,
        color:
          p.close >= p.open ? "rgba(34,197,94,0.45)" : "rgba(239,68,68,0.45)",
      }))
    );

    instance.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      instance.applyOptions({ width: el.clientWidth });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      instance.remove();
    };
  }, [chart]);

  return (
    <div className="my-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-1">
      <div className="px-2 py-1 text-[11px] text-zinc-400">
        {chart.ticker} · {chart.period}
      </div>
      <div ref={ref} className="w-full" />
    </div>
  );
}
