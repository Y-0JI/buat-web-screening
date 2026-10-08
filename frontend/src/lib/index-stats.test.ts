import { describe, expect, test } from "bun:test";
import { buildIndexStats, isIndexTicker } from "./index-stats";
import type { QuoteData } from "./chat";

const ihsg: QuoteData = {
  ticker: "IHSG",
  name: "Indeks Harga Saham Gabungan",
  last_price: 6154.11,
  lot: 165830000,
  value: 1887228,
  freq: 1523083,
  market_state: "open",
  market_label: "Sesi 1",
  prev_close: 6146.72,
  change: 7.39,
  change_pct: 0.12,
  day_open: 6154.97,
  day_high: 6179.09,
  day_low: 6137.66,
  day_volume: 165830000,
};

function cellsOf(q: QuoteData) {
  const built = buildIndexStats("IHSG", q);
  if (!built) throw new Error("buildIndexStats null");
  return { title: built.title, byKey: Object.fromEntries(built.cells.map((c) => [c.key, c])) as Record<string, { value: string; label: string; tone: string }> };
}

describe("isIndexTicker", () => {
  test("IHSG/COMPOSITE/JKSE (case-insensitive) = indeks", () => {
    expect(isIndexTicker("IHSG")).toBe(true);
    expect(isIndexTicker("ihsg")).toBe(true);
    expect(isIndexTicker("COMPOSITE")).toBe(true);
    expect(isIndexTicker("JKSE")).toBe(true);
  });

  test("saham bukan indeks", () => {
    expect(isIndexTicker("BBCA")).toBe(false);
    expect(isIndexTicker("FORU")).toBe(false);
    expect(isIndexTicker("")).toBe(false);
  });
});

describe("buildIndexStats", () => {
  test("urutan 9 sel sesuai gambar", () => {
    const built = buildIndexStats("IHSG", ihsg);
    expect(built?.cells.map((c) => c.key)).toEqual([
      "prev", "open", "lot", "chg", "high", "val", "pct", "low", "avg",
    ]);
  });

  test("format en-US sesuai gambar", () => {
    const { title, byKey } = cellsOf(ihsg);
    expect(title.price).toBe("6,154.11");
    expect(title.changeText).toBe("+7.39 (+0.12%)");
    expect(title.tone).toBe("up");
    expect(byKey.prev.value).toBe("6,146.72");
    expect(byKey.open.value).toBe("6,154.97");
    expect(byKey.lot.value).toBe("165.83M");
    expect(byKey.chg.value).toBe("+7.39");
    expect(byKey.high.value).toBe("6,179.09");
    expect(byKey.val.value).toBe("1.89M");
    expect(byKey.pct.value).toBe("0.12%");
    expect(byKey.low.value).toBe("6,137.66");
    expect(byKey.avg.value).toBe("0");
  });

  test("turun -> tone down & tanda minus", () => {
    const { title, byKey } = cellsOf({ ...ihsg, change: -46.2, change_pct: -0.75 });
    expect(title.tone).toBe("down");
    expect(title.changeText).toBe("-46.20 (-0.75%)");
    expect(byKey.chg.tone).toBe("down");
    expect(byKey.pct.tone).toBe("down");
  });

  test("Val triliun diringkas agar muat", () => {
    const { byKey } = cellsOf({ ...ihsg, value: 8715185031500 });
    expect(byKey.val.value).toBe("8.72T");
  });

  test("field kosong -> '-'; quote null -> null", () => {
    const { byKey } = cellsOf({ ...ihsg, day_open: null, lot: null });
    expect(byKey.open.value).toBe("-");
    expect(byKey.lot.value).toBe("-");
    expect(buildIndexStats("IHSG", null)).toBeNull();
  });
});
