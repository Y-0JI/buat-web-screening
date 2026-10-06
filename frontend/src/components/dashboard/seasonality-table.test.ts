import { describe, expect, test } from "bun:test";
import { buildSeasonalityTable, yearlyReturn } from "./seasonality-table";

describe("yearlyReturn", () => {
  test("return majemuk, bukan penjumlahan", () => {
    // 2024 Stockbit: 0,0,0,0,0,-33.33,0,50,0,133.33,142.86,176.47 -> ~1466%
    // (Stockbit pakai data mentah, jadi 1466.67; dari nilai yang sudah dibulatkan jadi 1466.74)
    const cells = [0, 0, 0, 0, 0, -33.33, 0, 50, 0, 133.33, 142.86, 176.47];
    expect(yearlyReturn(cells)).toBeCloseTo(1466.74, 1);
  });

  test("tanpa data -> null", () => {
    expect(yearlyReturn([])).toBeNull();
    expect(yearlyReturn([null, null])).toBeNull();
  });

  test("nilai null di tengah dilewati", () => {
    expect(yearlyReturn([10, null, -5])).toBeCloseTo(4.5, 10);
  });
});

const DATA = {
  months: ["Jan", "Feb"],
  years: ["2023", "2026", "2025", "2024"],
  monthly_returns: {
    Jan: { "2023": 50, "2024": -30, "2025": 20, "2026": 10 },
    Feb: { "2023": -25, "2024": 5, "2025": 10, "2026": -5 },
  },
  monthly_stats: [
    { month: "Jan", avg: 10, up: 3, down: 1, total: 4, up_prob: 75 },
    { month: "Feb", avg: -5, up: 2, down: 2, total: 4, up_prob: 50 },
  ],
};

describe("buildSeasonalityTable", () => {
  const t = buildSeasonalityTable(DATA);

  test("tahun diurutkan menurun", () => {
    expect(t.rows.map((r) => r.year)).toEqual(["2026", "2025", "2024", "2023"]);
  });

  test("kolom = bulan sesuai urutan header", () => {
    expect(t.months).toEqual(["Jan", "Feb"]);
    expect(t.rows[0].cells).toEqual([10, -5]);
  });

  test("kolom Year = return majemuk tiap tahun", () => {
    expect(t.rows[0].total).toBeCloseTo(4.5, 10);
    expect(t.rows[1].total).toBeCloseTo(32, 10);
    expect(t.rows[2].total).toBeCloseTo(-26.5, 10);
    expect(t.rows[3].total).toBeCloseTo(12.5, 10);
  });

  test("baris Average kolom Year = rata-rata return tahunan", () => {
    expect(t.average).toEqual([10, -5]);
    expect(t.averageTotal).toBeCloseTo(5.625, 10);
  });

  test("baris statistik ikut bulan", () => {
    expect(t.hasStats).toBe(true);
    expect(t.up).toEqual([3, 2]);
    expect(t.down).toEqual([1, 2]);
    expect(t.total).toEqual([4, 4]);
    expect(t.upProb).toEqual([75, 50]);
  });

  test("kolom Year baris bawah = hitungan tahun", () => {
    expect(t.annualUp).toBe(3);
    expect(t.annualDown).toBe(1);
    expect(t.annualTotal).toBe(4);
    expect(t.annualUpProb).toBe(75);
  });
});

describe("buildSeasonalityTable tanpa summary", () => {
  const t = buildSeasonalityTable({
    months: ["Jan"],
    years: ["2024"],
    monthly_returns: { Jan: { "2024": 1 } },
  });

  test("baris statistik kosong tapi baris tahun tetap ada", () => {
    expect(t.hasStats).toBe(false);
    expect(t.rows).toHaveLength(1);
    expect(t.rows[0].total).toBeCloseTo(1, 10);
    expect(t.up).toEqual([null]);
    expect(t.upProb).toEqual([null]);
  });

  test("tahun tanpa data -> annual null, bukan NaN", () => {
    const e = buildSeasonalityTable({
      months: ["Jan"],
      years: ["2024"],
      monthly_returns: {},
    });
    expect(e.rows[0].total).toBeNull();
    expect(e.averageTotal).toBeNull();
    expect(e.annualTotal).toBe(0);
    expect(e.annualUpProb).toBeNull();
  });
});