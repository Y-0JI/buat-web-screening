import { describe, expect, test } from "bun:test";
import { buildQuoteStats } from "./quote-stats";
import type { QuoteData } from "./chat";

const base: QuoteData = {
  ticker: "FORU",
  name: "Fortune Indonesia Tbk",
  last_price: 144,
  lot: 17020785,
  value: 222314109000,
  freq: 44554,
  market_state: "closed",
  market_label: "Market tutup",
  prev_close: 124,
  change: 20,
  change_pct: 16.13,
  day_open: 124,
  day_high: 144,
  day_low: 122,
  day_volume: 17020785,
  avg: 130.61,
  f_buy_value: 21_470_000_000,
  f_sell_value: 8_640_000_000,
};

function byKey(list: ReturnType<typeof buildQuoteStats>, key: string) {
  const item = list.find((s) => s.key === key);
  if (!item) throw new Error(`tidak ada stat ${key}`);
  return item;
}

describe("buildQuoteStats", () => {
  test("urutan & 12 sel sesuai gambar", () => {
    const list = buildQuoteStats(base);
    expect(list.map((s) => s.key)).toEqual([
      "open", "high", "low", "prev", "lot", "value", "avg", "freq", "fbuy", "fsell", "ara", "arb",
    ]);
    expect(list.map((s) => s.label)).toEqual([
      "Open", "High", "Low", "Prev", "Lot", "Val", "Avg", "Freq", "F Buy", "F Sell", "ARA", "ARB",
    ]);
  });

  test("tone harga vs prev close", () => {
    const list = buildQuoteStats(base);
    expect(byKey(list, "high").tone).toBe("up"); // 144 > 124
    expect(byKey(list, "low").tone).toBe("down"); // 122 < 124
    expect(byKey(list, "open").tone).toBe("neutral"); // 124 == 124
    expect(byKey(list, "avg").tone).toBe("up"); // 130.61 > 124
    expect(byKey(list, "prev").tone).toBe("neutral");
  });

  test("F Buy hijau, F Sell merah, ARA/ARB netral", () => {
    const list = buildQuoteStats(base);
    expect(byKey(list, "fbuy").tone).toBe("up");
    expect(byKey(list, "fsell").tone).toBe("down");
    expect(byKey(list, "ara").value).toBe("-");
    expect(byKey(list, "arb").value).toBe("-");
  });

  test("format nilai ringkas", () => {
    const list = buildQuoteStats(base);
    expect(byKey(list, "lot").value).toBe("17.02M");
    expect(byKey(list, "value").value).toBe("222.31B");
    expect(byKey(list, "freq").value).toBe("44.554");
    expect(byKey(list, "open").value).toBe("124");
  });

  test("field kosong -> '-' dan tone netral, tanpa error", () => {
    const list = buildQuoteStats({ ...base, avg: null, f_buy_value: null, f_sell_value: null, day_open: null });
    expect(byKey(list, "avg").value).toBe("-");
    expect(byKey(list, "avg").tone).toBe("neutral");
    expect(byKey(list, "fbuy").tone).toBe("neutral");
    expect(byKey(list, "open").value).toBe("-");
  });

  test("quote null -> []", () => {
    expect(buildQuoteStats(null)).toEqual([]);
  });
});
