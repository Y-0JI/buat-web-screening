# Indikator Chart Interaktif Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menambahkan indikator teknikal yang bisa di-toggle (EMA, Bollinger, Volume, Stochastic, RSI, MACD) pada chart candlestick di chat.

**Architecture:** Semua indikator dihitung di frontend dari data OHLCV (`UIChart.series`) memakai fungsi murni di `frontend/src/lib/indicators.ts`. Komponen `chart.tsx` menampilkan bar tombol toggle, menyimpan pilihan di `localStorage`, dan membangun ulang chart (lightweight-charts v5, pane bawaan) setiap kali set indikator aktif berubah.

**Tech Stack:** Next.js 15, React 19, TypeScript 5.7, lightweight-charts 5.2.1, Tailwind 4, Bun 1.3 (test runner).

## Global Constraints

- Frontend-only: TIDAK mengubah backend, API, maupun tipe `UIChart`.
- Tanpa dependensi baru.
- Parameter indikator tetap (tidak ada fitur ubah periode): EMA13/21/100/200, Bollinger(20,2), Stochastic(14,3,3), RSI(14), MACD(12,26,9).
- Default aktif: Volume, Stochastic, EMA13/21/100/200. Default non-aktif: Bollinger, RSI, MACD.
- Kunci penyimpanan: `idx_chart_indicators`.
- Format keluaran indikator: `{ time: string; value: number }` (time = `HistoryPoint.date`).
- Urutan pane tetap: Volume, Stochastic, RSI, MACD.
- Komentar kode gaya repo: ringkas, bahasa Indonesia, tanpa emoji.

---

### Task 1: Modul indikator — kerangka, `sma`, `ema`

**Files:**
- Create: `frontend/src/lib/indicators.ts`
- Test: `frontend/src/lib/indicators.test.ts`

**Interfaces:**
- Consumes: `HistoryPoint` dari `@/lib/chat` (`{ date, open, high, low, close, volume }`).
- Produces:
  - `type LinePoint = { time: string; value: number }`
  - `sma(values: number[], period: number): (number | null)[]`
  - `ema(points: HistoryPoint[], period: number): LinePoint[]`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/indicators.test.ts`:

```typescript
import { describe, expect, test } from "bun:test";
import type { HistoryPoint } from "@/lib/chat";
import { ema, sma } from "./indicators";

function pt(date: string, close: number, high = close, low = close): HistoryPoint {
  return { date, open: close, high, low, close, volume: 0 };
}

describe("sma", () => {
  test("null hingga data cukup lalu rata-rata bergulir", () => {
    expect(sma([1, 2, 3, 4], 2)).toEqual([null, 1.5, 2.5, 3.5]);
  });
});

describe("ema", () => {
  test("seed SMA lalu smoothing", () => {
    const pts = [1, 2, 3, 4, 5].map((v, i) => pt(`2024-01-0${i + 1}`, v));
    expect(ema(pts, 3)).toEqual([
      { time: "2024-01-03", value: 2 },
      { time: "2024-01-04", value: 3 },
      { time: "2024-01-05", value: 4 },
    ]);
  });

  test("data kurang dari periode -> array kosong", () => {
    const pts = [1, 2].map((v, i) => pt(`2024-01-0${i + 1}`, v));
    expect(ema(pts, 3)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bun test src/lib/indicators.test.ts` (workdir `frontend`)
Expected: FAIL — `Cannot find module "./indicators"` / `ema is not a function`.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/lib/indicators.ts`:

```typescript
// Perhitungan indikator teknikal dari deret OHLCV. Fungsi murni, tanpa dependensi.
import type { HistoryPoint } from "@/lib/chat";

export type LinePoint = { time: string; value: number };

function closes(points: HistoryPoint[]): number[] {
  return points.map((p) => p.close);
}

/** Rata-rata bergulir sederhana; null bila data belum cukup. */
export function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

/** EMA atas deret angka; null bila data belum cukup (untuk dipakai lintas indikator). */
function emaValues(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;
  const k = 2 / (period + 1);
  let prev = values.slice(0, period).reduce((s, v) => s + v, 0) / period;
  out[period - 1] = prev;
  for (let i = period; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function ema(points: HistoryPoint[], period: number): LinePoint[] {
  const values = emaValues(closes(points), period);
  const out: LinePoint[] = [];
  for (let i = 0; i < values.length; i++) {
    if (values[i] != null) out.push({ time: points[i].date, value: values[i] as number });
  }
  return out;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bun test src/lib/indicators.test.ts` (workdir `frontend`)
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/indicators.ts frontend/src/lib/indicators.test.ts
git commit -m "feat: modul indikator chart (sma, ema) + test"
```

---

### Task 2: Indikator `bollinger` dan `rsi`

**Files:**
- Modify: `frontend/src/lib/indicators.ts` (tambah fungsi di akhir file)
- Test: `frontend/src/lib/indicators.test.ts` (tambah describe)

**Interfaces:**
- Consumes: `closes`, `sma` dari Task 1.
- Produces:
  - `bollinger(points, period=20, mult=2): { upper: LinePoint[]; middle: LinePoint[]; lower: LinePoint[] }`
  - `rsi(points, period=14): LinePoint[]`

- [ ] **Step 1: Write the failing test**

Tambah ke `frontend/src/lib/indicators.test.ts`:

```typescript
import { bollinger, ema, rsi, sma } from "./indicators";

const flat = (n: number, v: number) =>
  Array.from({ length: n }, (_, i) => pt(`d${i}`, v));

describe("bollinger", () => {
  test("harga konstan -> upper=middle=lower", () => {
    const bb = bollinger(flat(4, 5), 3, 2);
    expect(bb.middle).toEqual([
      { time: "d2", value: 5 },
      { time: "d3", value: 5 },
    ]);
    expect(bb.upper).toEqual(bb.middle);
    expect(bb.lower).toEqual(bb.middle);
  });
});

describe("rsi", () => {
  test("harga naik monoton -> 100", () => {
    const up = Array.from({ length: 15 }, (_, i) => pt(`d${i}`, i + 1));
    const r = rsi(up, 14);
    expect(r.length).toBe(1);
    expect(r[0].value).toBe(100);
  });

  test("data kurang dari periode -> array kosong", () => {
    expect(rsi(flat(10, 5), 14)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bun test src/lib/indicators.test.ts` (workdir `frontend`)
Expected: FAIL — `bollinger`/`rsi` belum diexport (import error).

- [ ] **Step 3: Write minimal implementation**

Tambah ke akhir `frontend/src/lib/indicators.ts`:

```typescript
/** Bollinger Bands (default 20, 2). */
export function bollinger(
  points: HistoryPoint[],
  period = 20,
  mult = 2
): { upper: LinePoint[]; middle: LinePoint[]; lower: LinePoint[] } {
  const c = closes(points);
  const mid = sma(c, period);
  const upper: LinePoint[] = [];
  const middle: LinePoint[] = [];
  const lower: LinePoint[] = [];
  for (let i = period - 1; i < c.length; i++) {
    const m = mid[i] as number;
    const slice = c.slice(i - period + 1, i + 1);
    const variance = slice.reduce((s, v) => s + (v - m) ** 2, 0) / period;
    const sd = Math.sqrt(variance);
    const t = points[i].date;
    middle.push({ time: t, value: m });
    upper.push({ time: t, value: m + mult * sd });
    lower.push({ time: t, value: m - mult * sd });
  }
  return { upper, middle, lower };
}

/** RSI (Wilder, default 14). */
export function rsi(points: HistoryPoint[], period = 14): LinePoint[] {
  const out: LinePoint[] = [];
  const c = closes(points);
  if (c.length <= period) return out;
  let gain = 0;
  let loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = c[i] - c[i - 1];
    if (d >= 0) gain += d;
    else loss -= d;
  }
  let avgGain = gain / period;
  let avgLoss = loss / period;
  const val = () =>
    avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  out.push({ time: points[period].date, value: val() });
  for (let i = period + 1; i < c.length; i++) {
    const d = c[i] - c[i - 1];
    const g = d > 0 ? d : 0;
    const l = d < 0 ? -d : 0;
    avgGain = (avgGain * (period - 1) + g) / period;
    avgLoss = (avgLoss * (period - 1) + l) / period;
    out.push({ time: points[i].date, value: val() });
  }
  return out;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bun test src/lib/indicators.test.ts` (workdir `frontend`)
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/indicators.ts frontend/src/lib/indicators.test.ts
git commit -m "feat: indikator bollinger dan rsi + test"
```

---

### Task 3: Indikator `macd` dan `stochastic`

**Files:**
- Modify: `frontend/src/lib/indicators.ts` (tambah fungsi di akhir file)
- Test: `frontend/src/lib/indicators.test.ts` (tambah describe)

**Interfaces:**
- Consumes: `closes`, `emaValues` dari Task 1.
- Produces:
  - `macd(points, fast=12, slow=26, signal=9): { macd: LinePoint[]; signal: LinePoint[]; histogram: LinePoint[] }`
  - `stochastic(points, kPeriod=14, kSmooth=3, dPeriod=3): { k: LinePoint[]; d: LinePoint[] }`

- [ ] **Step 1: Write the failing test**

Tambah ke `frontend/src/lib/indicators.test.ts`:

```typescript
import { bollinger, ema, macd, rsi, sma, stochastic } from "./indicators";

describe("macd", () => {
  test("harga konstan -> macd/signal/histogram nol", () => {
    const m = macd(flat(40, 5));
    expect(m.macd.length).toBe(15);
    expect(m.signal.length).toBe(7);
    expect(m.macd.every((p) => p.value === 0)).toBe(true);
    expect(m.signal.every((p) => p.value === 0)).toBe(true);
    expect(m.histogram.every((p) => p.value === 0)).toBe(true);
  });
});

describe("stochastic", () => {
  test("high=low -> nilai 50", () => {
    const s = stochastic(flat(20, 10), 14, 3, 3);
    expect(s.k.length).toBe(5);
    expect(s.d.length).toBe(3);
    expect(s.k.every((p) => p.value === 50)).toBe(true);
    expect(s.d.every((p) => p.value === 50)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bun test src/lib/indicators.test.ts` (workdir `frontend`)
Expected: FAIL — `macd`/`stochastic` belum diexport.

- [ ] **Step 3: Write minimal implementation**

Tambah ke akhir `frontend/src/lib/indicators.ts`:

```typescript
/** MACD (default 12, 26, 9). */
export function macd(
  points: HistoryPoint[],
  fast = 12,
  slow = 26,
  signal = 9
): { macd: LinePoint[]; signal: LinePoint[]; histogram: LinePoint[] } {
  const c = closes(points);
  const fastE = emaValues(c, fast);
  const slowE = emaValues(c, slow);
  const lineVals: number[] = [];
  const lineTimes: string[] = [];
  const macdLine: LinePoint[] = [];
  for (let i = 0; i < c.length; i++) {
    if (fastE[i] != null && slowE[i] != null) {
      const v = (fastE[i] as number) - (slowE[i] as number);
      macdLine.push({ time: points[i].date, value: v });
      lineVals.push(v);
      lineTimes.push(points[i].date);
    }
  }
  const sig = emaValues(lineVals, signal);
  const signalLine: LinePoint[] = [];
  const histogram: LinePoint[] = [];
  for (let i = 0; i < lineVals.length; i++) {
    if (sig[i] != null) {
      signalLine.push({ time: lineTimes[i], value: sig[i] as number });
      histogram.push({ time: lineTimes[i], value: lineVals[i] - (sig[i] as number) });
    }
  }
  return { macd: macdLine, signal: signalLine, histogram };
}

/** Stochastic lambat (default 14, 3, 3). */
export function stochastic(
  points: HistoryPoint[],
  kPeriod = 14,
  kSmooth = 3,
  dPeriod = 3
): { k: LinePoint[]; d: LinePoint[] } {
  const raw: number[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i < kPeriod - 1) {
      raw.push(NaN);
      continue;
    }
    let hh = -Infinity;
    let ll = Infinity;
    for (let j = i - kPeriod + 1; j <= i; j++) {
      hh = Math.max(hh, points[j].high);
      ll = Math.min(ll, points[j].low);
    }
    raw.push(hh === ll ? 50 : ((points[i].close - ll) / (hh - ll)) * 100);
  }

  const kValues: number[] = [];
  const kTimes: string[] = [];
  const k: LinePoint[] = [];
  const kStart = kPeriod - 1 + kSmooth - 1;
  for (let i = kStart; i < points.length; i++) {
    let s = 0;
    for (let j = i - kSmooth + 1; j <= i; j++) s += raw[j];
    const v = s / kSmooth;
    k.push({ time: points[i].date, value: v });
    kValues.push(v);
    kTimes.push(points[i].date);
  }

  const d: LinePoint[] = [];
  for (let i = dPeriod - 1; i < kValues.length; i++) {
    let s = 0;
    for (let j = i - dPeriod + 1; j <= i; j++) s += kValues[j];
    d.push({ time: kTimes[i], value: s / dPeriod });
  }
  return { k, d };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bun test src/lib/indicators.test.ts` (workdir `frontend`)
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/indicators.ts frontend/src/lib/indicators.test.ts
git commit -m "feat: indikator macd dan stochastic + test"
```

---

### Task 4: Bar toggle indikator & wiring chart

**Files:**
- Modify: `frontend/src/components/chat/chart.tsx` (ganti seluruh isi file)

**Interfaces:**
- Consumes: `ema`, `bollinger`, `rsi`, `macd`, `stochastic` dari `@/lib/indicators`; `UIChart` dari `./types`.
- Produces: komponen `PriceChart` dengan bar toggle; tidak ada API baru untuk komponen lain.

- [ ] **Step 1: Ganti isi `chart.tsx`**

Tulis ulang `frontend/src/components/chat/chart.tsx` menjadi:

```tsx
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

    const overlay = (color: string, data: ReturnType<typeof ema>, dashed = false) =>
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
            { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false },
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
          .addSeries(LineSeries, { color: "#22d3ee", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, paneIndex)
          .setData(st.k);
        instance
          .addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, paneIndex)
          .setData(st.d);
      } else if (id === "rsi") {
        instance
          .addSeries(LineSeries, { color: "#a78bfa", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, paneIndex)
          .setData(rsi(points, 14));
      } else if (id === "macd") {
        const m = macd(points, 12, 26, 9);
        instance
          .addSeries(LineSeries, { color: "#22d3ee", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, paneIndex)
          .setData(m.macd);
        instance
          .addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, paneIndex)
          .setData(m.signal);
        instance
          .addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, paneIndex)
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
```

- [ ] **Step 2: Run typecheck + build**

Run: `bun run build` (workdir `frontend`)
Expected: build sukses, tidak ada error TypeScript.

- [ ] **Step 3: Manual verification**

Jalankan `bun run dev` (frontend) dan backend, buka chat, minta chart (mis. "chart BBCA 3mo"). Cek:
1. Bar toggle muncul; default aktif Volume, Stoch, EMA13/21/100/200.
2. Klik BB/RSI/MACD → panel/overlay muncul; klik lagi → hilang, tanpa error console.
3. Tinggi chart bertambah/berkurang sesuai jumlah panel.
4. Refresh halaman → pilihan toggle tersimpan.
5. Chart dengan data pendek (< 200 bar) tidak crash (EMA200/BB kosong).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/chart.tsx
git commit -m "feat: bar toggle indikator pada chart (EMA, BB, Stoch, RSI, MACD)"
```

---

## Self-Review

- **Spec coverage:** EMA (Task 1), Bollinger + RSI (Task 2), MACD + Stochastic (Task 3), bar toggle + localStorage + pane + tinggi dinamis + default (Task 4). Edge case data pendek ditangani di fungsi (`array kosong`) dan diverifikasi Task 4 Step 3. Semua bagian spec tercakup.
- **Placeholder scan:** tidak ada TBD/TODO; setiap langkah kode memuat kode lengkap.
- **Type consistency:** `LinePoint`, `sma`, `ema`, `bollinger`, `rsi`, `macd`, `stochastic` konsisten antar task. `emaValues` internal dipakai Task 1 & 3.
