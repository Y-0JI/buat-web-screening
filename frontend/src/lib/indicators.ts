import type { HistoryPoint } from "@/lib/chat";

export type LinePoint = { time: string; value: number };

function closes(points: HistoryPoint[]): number[] {
  return points.map((p) => p.close);
}

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

function lined(points: HistoryPoint[], values: (number | null)[]): LinePoint[] {
  const out: LinePoint[] = [];
  for (let i = 0; i < values.length; i++) {
    if (values[i] != null) out.push({ time: points[i].date, value: values[i] as number });
  }
  return out;
}

export function ema(points: HistoryPoint[], period: number): LinePoint[] {
  return lined(points, emaValues(closes(points), period));
}

export function ma(points: HistoryPoint[], period: number): LinePoint[] {
  return lined(points, sma(closes(points), period));
}

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
    avgGain = (avgGain * (period - 1) + (d > 0 ? d : 0)) / period;
    avgLoss = (avgLoss * (period - 1) + (d < 0 ? -d : 0)) / period;
    out.push({ time: points[i].date, value: val() });
  }
  return out;
}

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

export function kdj(
  points: HistoryPoint[],
  period = 9,
  kSmooth = 3,
  dSmooth = 3
): { k: LinePoint[]; d: LinePoint[]; j: LinePoint[] } {
  const rsv: (number | null)[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i < period - 1) {
      rsv.push(null);
      continue;
    }
    let hh = -Infinity;
    let ll = Infinity;
    for (let j = i - period + 1; j <= i; j++) {
      hh = Math.max(hh, points[j].high);
      ll = Math.min(ll, points[j].low);
    }
    rsv.push(hh === ll ? 50 : ((points[i].close - ll) / (hh - ll)) * 100);
  }
  const kVals: number[] = [];
  const kTimes: string[] = [];
  const k: LinePoint[] = [];
  for (let i = 0; i < points.length; i++) {
    if (rsv[i] == null) continue;
    const prev = kVals.length ? kVals[kVals.length - 1] : 50;
    const v = (prev * (kSmooth - 1) + (rsv[i] as number)) / kSmooth;
    kVals.push(v);
    kTimes.push(points[i].date);
    k.push({ time: points[i].date, value: v });
  }
  const d: LinePoint[] = [];
  const dVals: number[] = [];
  for (let i = 0; i < kVals.length; i++) {
    const prev = dVals.length ? dVals[dVals.length - 1] : 50;
    const v = (prev * (dSmooth - 1) + kVals[i]) / dSmooth;
    dVals.push(v);
    d.push({ time: kTimes[i], value: v });
  }
  const j: LinePoint[] = k.map((p, i) => ({
    time: p.time,
    value: 3 * p.value - 2 * dVals[i],
  }));
  return { k, d, j };
}

export function valueSeries(points: HistoryPoint[]): LinePoint[] {
  return points.map((p) => ({
    time: p.date,
    value: p.value ?? p.close * p.volume,
  }));
}
