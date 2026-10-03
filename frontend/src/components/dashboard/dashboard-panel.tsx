"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FALLBACK_TICKER,
  getHistory,
  getQuote,
  type HistoryPoint,
  type QuoteData,
} from "@/lib/chat";
import { ChartSettings, DEFAULT_ACTIVE, DEFAULT_OVERLAY, OVERLAY_KEY, type ChartType, type IndicatorId, type OverlayParams } from "./chart-settings";
import { DashboardChart } from "./dashboard-chart";
import { ACTIVE_PERIODS, PERIODS, StockPanel, type Period } from "./stock-panel";

const INDICATOR_KEY = "idx_chart_indicators";
const CHART_TYPE_KEY = "idx_chart_type";

const VALID_IDS: IndicatorId[] = ["ma", "ema", "boll", "volume", "value", "rsi", "macd", "kdj"];

function loadActive(): IndicatorId[] {
  try {
    const raw = localStorage.getItem(INDICATOR_KEY);
    if (!raw) return DEFAULT_ACTIVE;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return DEFAULT_ACTIVE;
    return parsed.filter((x): x is IndicatorId => VALID_IDS.includes(x));
  } catch {
    return DEFAULT_ACTIVE;
  }
}

function loadChartType(): ChartType {
  try {
    const raw = localStorage.getItem(CHART_TYPE_KEY);
    return raw === "line" ? "line" : "candlestick";
  } catch {
    return "candlestick";
  }
}

function loadOverlay(): OverlayParams {
  try {
    const raw = localStorage.getItem(OVERLAY_KEY);
    if (!raw) return DEFAULT_OVERLAY;
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return DEFAULT_OVERLAY;
    const num = (v: unknown, fb: number) =>
      typeof v === "number" && Number.isFinite(v) && v > 0 ? v : fb;
    return {
      ma: num(parsed.ma, DEFAULT_OVERLAY.ma),
      ema: num(parsed.ema, DEFAULT_OVERLAY.ema),
      boll: num(parsed.boll, DEFAULT_OVERLAY.boll),
    };
  } catch {
    return DEFAULT_OVERLAY;
  }
}

export function DashboardPanel({ onOpenAi }: { onOpenAi?: () => void }) {
  const [ticker, setTicker] = useState(FALLBACK_TICKER);
  const [period, setPeriod] = useState<Period>("1M");
  const [series, setSeries] = useState<HistoryPoint[]>([]);
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<IndicatorId[]>(DEFAULT_ACTIVE);
  const [chartType, setChartType] = useState<ChartType>("candlestick");
  const [params, setParams] = useState<OverlayParams>(DEFAULT_OVERLAY);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setActive(loadActive());
    setChartType(loadChartType());
    setParams(loadOverlay());
    setReady(true);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(INDICATOR_KEY, JSON.stringify(active));
    } catch {
      /* abaikan */
    }
  }, [active]);

  useEffect(() => {
    try {
      localStorage.setItem(CHART_TYPE_KEY, chartType);
    } catch {
      /* abaikan */
    }
  }, [chartType]);

  useEffect(() => {
    try {
      localStorage.setItem(OVERLAY_KEY, JSON.stringify(params));
    } catch {
      /* abaikan */
    }
  }, [params]);

  const load = useCallback(async (code: string, p: Period) => {
    setLoading(true);
    setError(null);
    try {
      const [hist, q] = await Promise.all([
        getHistory(code, p),
        getQuote(code).catch(() => null),
      ]);
      if (!hist.length) {
        setError(`Data ${code} tidak tersedia.`);
        setSeries([]);
        setQuote(null);
      } else {
        setSeries(hist);
        setQuote(q);
      }
    } catch {
      setError("Gagal memuat data. Periksa koneksi backend.");
      setSeries([]);
      setQuote(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(ticker, period);
  }, [ticker, period, load]);

  const toggle = (id: IndicatorId) =>
    setActive((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  if (!ready) return null;

  return (
    <div className="h-full flex flex-col min-h-0 bg-zinc-950">
      <div className="flex items-center justify-between px-4 pt-2 md:hidden">
        <span className="text-[11px] text-zinc-600">Data IDX Edge PRO</span>
        <button
          type="button"
          onClick={onOpenAi}
          className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
          aria-label="Buka AI Copilot"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.5l-2 2m-7 7l-2 2m11 0l-2-2m-7-7l-2-2M12 8a4 4 0 100 8 4 4 0 000-8z" />
          </svg>
        </button>
      </div>

      <StockPanel
        ticker={ticker}
        quote={quote}
        series={series}
        period={period}
        loading={loading}
        error={error}
        onTicker={setTicker}
      />

      <div className="flex-1 min-h-0 px-4 pt-1 pb-0 relative">
        {loading && !series.length ? (
          <div className="h-64 flex items-center justify-center text-sm text-zinc-500">
            Memuat chart…
          </div>
        ) : series.length ? (
          <DashboardChart
            ticker={ticker}
            period={period}
            series={series}
            chartType={chartType}
            active={active}
            params={params}
          />
        ) : null}
      </div>

      <div className="px-4 pt-1 pb-1 flex items-center gap-1.5 flex-wrap">
        {PERIODS.map((p) => {
          const enabled = ACTIVE_PERIODS.includes(p);
          const on = period === p;
          return (
            <button
              key={p}
              type="button"
              disabled={!enabled || (loading && p === period)}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                on
                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/60"
                  : enabled
                    ? "text-zinc-400 border border-zinc-800 hover:text-zinc-200 hover:border-zinc-600"
                    : "text-zinc-700 border border-zinc-800/60 cursor-not-allowed"
              }`}
            >
              {p}
            </button>
          );
        })}
        <div className="ml-auto flex items-center gap-1">
          <ChartSettings
            active={active}
            onToggle={toggle}
            params={params}
            onParam={(id, value) => setParams((p) => ({ ...p, [id]: value }))}
            chartType={chartType}
            onChartType={setChartType}
          />
        </div>
      </div>
    </div>
  );
}
