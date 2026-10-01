import { describe, expect, test } from "bun:test";
import type { HistoryPoint } from "@/lib/chat";
import { bollinger, ema, macd, rsi, sma, stochastic } from "./indicators";

function pt(date: string, close: number, high = close, low = close): HistoryPoint {
  return { date, open: close, high, low, close, volume: 0 };
}

const flat = (n: number, v: number) =>
  Array.from({ length: n }, (_, i) => pt(`d${i}`, v));

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
