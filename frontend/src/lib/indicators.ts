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

/** EMA atas deret angka; null bila data belum cukup (dipakai lintas indikator). */
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
    if (values[i] != null) {
      out.push({ time: points[i].date, value: values[i] as number });
    }
  }
  return out;
}

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
  const val = () => (avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
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
