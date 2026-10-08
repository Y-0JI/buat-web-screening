"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FALLBACK_TICKER,
  SECONDARY_TICKER,
  getHistory,
  getQuote,
  type HistoryPoint,
  type QuoteData,
} from "@/lib/chat";
import { useLiveTicker } from "@/lib/live";
import { ChartSettings, DEFAULT_ACTIVE, DEFAULT_OVERLAY, OVERLAY_KEY, normalizeOverlay, type ChartType, type IndicatorId, type OverlayParams } from "./chart-settings";
import { DashboardChart } from "./dashboard-chart";
import { IndexQuoteStrip } from "./index-quote-strip";
import { QuoteStatsCard } from "./quote-stats-card";
import { isIndexTicker } from "@/lib/index-stats";
import { StockTabs } from "./stock-tabs";
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
    return normalizeOverlay(JSON.parse(raw));
  } catch {
    return DEFAULT_OVERLAY;
  }
}

export function DashboardPanel({
  ticker,
  onTicker,
  onOpenAi,
  homeTick,
}: {
  ticker: string;
  onTicker: (t: string) => void;
  onOpenAi?: () => void;
  homeTick?: number;
}) {
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

  const load = useCallback(async (code: string, p: Period, fb = true): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const [hist, q] = await Promise.all([
        getHistory(code, p),
        getQuote(code).catch(() => null),
      ]);
      if (!hist.length) {
        if (fb && code !== SECONDARY_TICKER) {
          return load(SECONDARY_TICKER, p, false).then((ok) => {
            if (ok) onTicker(SECONDARY_TICKER);
            return ok;
          });
        }
        setError(`Data ${code} tidak tersedia.`);
        setSeries([]);
        setQuote(null);
        return false;
      }
      setSeries(hist);
      setQuote(q);
      return true;
    } catch {
      setError("Gagal memuat data. Periksa koneksi backend.");
      setSeries([]);
      setQuote(null);
      return false;
    } finally {
      setLoading(false);
    }
  }, [onTicker]);

  useEffect(() => {
    load(ticker, period);
  }, [ticker, period, load]);

  // Sinyal "pulang": paksa muat ulang walau ticker sudah sama.
  useEffect(() => {
    load(ticker, period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [homeTick]);

  const marketOpen = quote == null || quote.market_state !== "closed";
  // WS tidak mengirim tick indeks -> indeks tetap pakai polling REST.
  const isIndex = (quote?.lot ?? null) === 0 && (quote?.value ?? null) === 0;
  const live = useLiveTicker(ticker, marketOpen && !isIndex);
  const wsPrice =
    live.connected && !isIndex && live.quote ? live.quote.price : null;
  const restPrice = quote?.last_price ?? null;
  const displayPrice = wsPrice ?? restPrice;
  // WS menimpa change_pct harian; harga periode dihitung di bawah dari series.
  const wsChangePct =
    wsPrice != null && !isIndex ? live.quote?.change_pct ?? null : null;

  useEffect(() => {
    if (!marketOpen) return;
    // WS gagal/nonaktif ATAU indeks (tanpa tick WS) -> polling cadangan 10 detik.
    if (
      (live.connected && live.quote && !isIndex) ||
      document.visibilityState !== "visible"
    )
      return;
    const tick = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const q = await getQuote(ticker);
        if (q) setQuote(q);
      } catch {
        /* diamkan, coba lagi interval berikut */
      }
    };
    const id = setInterval(tick, 10_000);
    return () => clearInterval(id);
  }, [ticker, marketOpen, live.connected]);

  const toggle = (id: IndicatorId) =>
    setActive((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  // Harga WS menimpa harga REST (tanpa mengubah Lot/Val yang hanya datang via REST).
  const displayQuote: QuoteData | null =
    quote && wsPrice != null && !isIndex
      ? {
          ...quote,
          last_price: wsPrice,
          change_pct: wsChangePct ?? quote.change_pct,
          change:
            quote.prev_close != null
              ? wsPrice - quote.prev_close
              : quote.change,
        }
      : quote;
  // Indeks tidak punya lot/value di quote -> data agregat datang dari history.

  if (!ready) return null;

  return (
    <div className="h-full flex flex-col min-h-0 bg-surface-0 overflow-y-auto">
      <div className="flex items-center justify-between px-4 pt-2 md:hidden">
        <span className="text-[11px] text-text-muted">Data IDX Edge PRO</span>
        <button
          type="button"
          onClick={onOpenAi}
          className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
          aria-label="Buka AI Copilot"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.5l-2 2m-7 7l-2-2m-7-7l-2-2M12 8a4 4 0 100 8 4 4 0 000-8z" />
          </svg>
        </button>
      </div>

      {isIndexTicker(ticker) ? (
        <IndexQuoteStrip ticker={ticker} quote={displayQuote} />
      ) : (
        <StockPanel
          ticker={ticker}
          quote={displayQuote}
          series={series}
          period={period}
          loading={loading}
          error={error}
        />
      )}

      <div className="shrink-0 px-4 pt-1 pb-0 relative">
        <div className="absolute right-5 top-2 z-10 flex items-center gap-1.5 flex-wrap justify-end max-w-[85%] rounded-lg bg-surface-0/70 backdrop-blur px-1 py-0.5">
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
                    ? "bg-emerald-500/15 text-emerald-500 border border-emerald-500/60"
                    : enabled
                      ? "text-text-secondary border border-border hover:text-text-primary hover:border-border"
                      : "text-text-muted border border-border/60 cursor-not-allowed"
                }`}
              >
                {p}
              </button>
            );
          })}
          <ChartSettings
            active={active}
            onToggle={toggle}
            params={params}
            onSaveParams={(p) => setParams(normalizeOverlay(p))}
            chartType={chartType}
            onChartType={setChartType}
          />
        </div>
        {loading && !series.length ? (
          <div className="h-64 flex items-center justify-center text-sm text-text-muted">
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
            livePrice={displayPrice}
          />
        ) : null}
      </div>

      {!isIndexTicker(ticker) && (
        <QuoteStatsCard ticker={ticker} quote={displayQuote} series={series} />
      )}

      <StockTabs
        ticker={ticker}
        onTicker={onTicker}
        liveTrades={live.trades}
        liveConnected={live.connected}
        isIndex={isIndex}
      />
    </div>
  );
}
