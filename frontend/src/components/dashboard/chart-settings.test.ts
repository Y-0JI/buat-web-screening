import { describe, expect, test } from "bun:test";
import { DEFAULT_OVERLAY, normalizeOverlay } from "./chart-settings";

describe("normalizeOverlay", () => {
  test("format lama (angka) jatuh ke default", () => {
    const out = normalizeOverlay({ ma: 20, ema: 20, boll: 20 });
    expect(out).toEqual(DEFAULT_OVERLAY);
  });

  test("input rusak jatuh ke default", () => {
    expect(normalizeOverlay(null)).toEqual(DEFAULT_OVERLAY);
    expect(normalizeOverlay("x")).toEqual(DEFAULT_OVERLAY);
  });

  test("nilai valid dipertahankan, warna jelek diganti default", () => {
    const out = normalizeOverlay({
      ma: [{ on: false, period: 10, color: "red" }],
      ema: DEFAULT_OVERLAY.ema,
      boll: { length: 30, mult: 1.5, colorMid: "#ffffff", colorBand: "#000000" },
    });
    expect(out.ma).toEqual(DEFAULT_OVERLAY.ma);
    expect(out.boll.length).toBe(30);
    expect(out.boll.mult).toBe(1.5);
  });
});
