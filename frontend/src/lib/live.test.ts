import { describe, expect, test } from "bun:test";
import { reduceLiveMessage, wsUrl } from "./live";

const EMPTY = { quote: null, trades: [] };

describe("wsUrl", () => {
  test("bangun URL /ws/live?ticker dari API_BASE", () => {
    expect(wsUrl("BBCA")).toMatch(/^ws:\/\//);
    expect(wsUrl("BBCA")).toContain("/ws/live?ticker=BBCA");
  });
});

describe("reduceLiveMessage", () => {
  test("quote menimpa harga terakhir", () => {
    const next = reduceLiveMessage(EMPTY, "BBCA", {
      type: "quote",
      ticker: "BBCA",
      price: 6100,
      change_pct: 0.5,
      time: "10:00:01",
    });
    expect(next.quote).toEqual({ ticker: "BBCA", price: 6100, change_pct: 0.5, time: "10:00:01" });
    expect(next.trades).toEqual([]);
  });

  test("trade menaruh di depan dan update quote harga", () => {
    const next = reduceLiveMessage(EMPTY, "BBCA", {
      type: "trade",
      data: { t: "BBCA", time: "10:00:02", action: "BUY", price: 6125, lot: 1, value: 612500 },
    });
    expect(next.quote?.price).toBe(6125);
    expect(next.trades[0].price).toBe(6125);
    expect(next.trades[0].action).toBe("BUY");
  });

  test("trade membatasi 100 baris terbaru", () => {
    let state = EMPTY;
    for (let i = 0; i < 120; i++) {
      state = reduceLiveMessage(state, "BBCA", {
        type: "trade",
        data: { t: "BBCA", time: `10:00:${i}`, price: 6000 + i, lot: 1 },
      });
    }
    expect(state.trades).toHaveLength(100);
    expect(state.trades[0].price).toBe(6119);
  });

  test("snapshot mengisi ulang daftar trades", () => {
    const next = reduceLiveMessage(EMPTY, "BBCA", {
      type: "snapshot",
      recent: [{ time: "09:59:00", action: "SELL", price: 6090, lot: 3, board: "RG" }],
    });
    expect(next.trades).toHaveLength(1);
    expect(next.trades[0].ticker).toBe("BBCA");
  });

  test("pesan tak dikenal diabaikan", () => {
    expect(reduceLiveMessage(EMPTY, "BBCA", { type: "top5" })).toEqual(EMPTY);
  });
});
