import { describe, expect, test } from "bun:test";
import type { HistoryPoint } from "@/lib/chat";
import { ema, kdj, ma, sma, valueSeries } from "./indicators";

function pt(
  date: string,
  close: number,
  high = close,
  low = close,
  value?: number
): HistoryPoint {
  return {
    date,
    open: close,
    high,
    low,
    close,
    volume: 100,
    ...(value !== undefined ? { value } : {}),
  };
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

describe("ma", () => {
  test("garis mulai saat data cukup", () => {
    const pts = [1, 2, 3, 4].map((v, i) => pt(`2024-01-0${i + 1}`, v));
    expect(ma(pts, 2)).toEqual([
      { time: "2024-01-02", value: 1.5 },
      { time: "2024-01-03", value: 2.5 },
      { time: "2024-01-04", value: 3.5 },
    ]);
  });
});

describe("kdj", () => {
  test("naik monoton: J >= K >= D", () => {
    const pts = Array.from({ length: 20 }, (_, i) =>
      pt(
        `2024-01-${String(i + 1).padStart(2, "0")}`,
        100 + i,
        101 + i,
        99 + i
      )
    );
    const { k, d, j } = kdj(pts, 9, 3, 3);
    expect(k.length).toBeGreaterThan(0);
    const last = (a: { value: number }[]) => a[a.length - 1].value;
    for (const arr of [k, d])
      for (const p of arr) {
        expect(p.value).toBeGreaterThanOrEqual(0);
        expect(p.value).toBeLessThanOrEqual(100);
      }
    expect(last(j)).toBeGreaterThanOrEqual(last(k));
    expect(last(k)).toBeGreaterThanOrEqual(last(d));
  });
});

describe("valueSeries", () => {
  test("pakai value bila ada, else close*volume", () => {
    const pts = [pt("2024-01-01", 10, 10, 10, 500), pt("2024-01-02", 20)];
    expect(valueSeries(pts)).toEqual([
      { time: "2024-01-01", value: 500 },
      { time: "2024-01-02", value: 2000 },
    ]);
  });
});
