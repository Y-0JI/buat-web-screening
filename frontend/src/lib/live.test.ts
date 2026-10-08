import { describe, expect, test } from "bun:test";
import { mergeTradeRows, reduceLiveMessage, todayWib, wsUrl } from "./live";
import type { OrderFlowRow } from "./chat";
import type { LiveTrade } from "./live";

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

describe("mergeTradeRows", () => {
  const rest = (time: string, extra: Partial<OrderFlowRow> = {}): OrderFlowRow => ({
    time,
    action: "BUY",
    price: 100,
    lot: 1,
    value: 10000,
    buyer: "A",
    seller: "B",
    buyer_type: "D",
    seller_type: "D",
    board: "RG",
    ...extra,
  });
  const live = (time: string, extra: Partial<LiveTrade> = {}): LiveTrade => ({
    ticker: "BBCA",
    ...rest(time),
    buyer_type: null,
    seller_type: null,
    ...extra,
  });

  test("tick live baru di depan, history REST tetap ada", () => {
    const out = mergeTradeRows(
      [rest("10:00:01"), rest("10:00:00")],
      [live("10:00:02")]
    );
    expect(out.map((r) => r.time)).toEqual(["10:00:02", "10:00:01", "10:00:00"]);
  });

  test("duplikat REST/live hanya sekali, metadata REST menang", () => {
    const out = mergeTradeRows([rest("10:00:01")], [live("10:00:01")]);
    expect(out).toHaveLength(1);
    expect(out[0].buyer_type).toBe("D");
  });

  test("dibatasi 50 baris terbaru", () => {
    const many = Array.from({ length: 60 }, (_, i) => live(`10:00:${String(i).padStart(2, "0")}`));
    expect(mergeTradeRows([], many)).toHaveLength(50);
  });

  test("tanpa live tetap mengembalikan tape REST", () => {
    expect(mergeTradeRows([rest("10:00:01")], [])).toHaveLength(1);
  });

  test("tick live dicap tanggal WIB hari ini", () => {
    const next = reduceLiveMessage(EMPTY, "BBCA", {
      type: "trade",
      data: { t: "BBCA", time: "10:47:07", action: "BUY", price: 6075, lot: 1 },
    });
    expect(next.trades[0].tradeDate).toBe(todayWib());
    expect(/^\d{4}-\d{2}-\d{2}$/.test(next.trades[0].tradeDate ?? "")).toBe(true);
  });

  test("live beda tanggal tampil di depan history kemarin", () => {
    const out = mergeTradeRows(
      [rest("16:14:11")],
      [live("10:47:07", { tradeDate: "2026-10-08" })],
      100,
      "2026-10-07"
    );
    expect(out.map((r) => (r as LiveTrade).tradeDate ?? "2026-10-07")).toEqual([
      "2026-10-08",
      "2026-10-07",
    ]);
  });

  test("jam sama beda tanggal bukan duplikat", () => {
    const out = mergeTradeRows(
      [rest("10:47:07")],
      [live("10:47:07", { tradeDate: "2026-10-08" })],
      100,
      "2026-10-07"
    );
    expect(out).toHaveLength(2);
  });

  test("kompatibel: tanpa tanggal pakai perilaku lama", () => {
    const out = mergeTradeRows([rest("10:00:01")], [live("10:00:01")]);
    expect(out).toHaveLength(1);
    expect(out.map((r) => r.time)).toEqual(["10:00:01", ...[]].slice(0, 1));
  });
});
