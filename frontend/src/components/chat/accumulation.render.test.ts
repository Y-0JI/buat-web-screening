import { describe, expect, test } from "bun:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AccumulationCard } from "./accumulation";
import type { AccumulationResult } from "@/lib/chat";

const sample: AccumulationResult = {
  scan_date: "2026-09-30",
  status: "partial",
  stale: false,
  stale_trading_days: null,
  candidates: [
    {
      ticker: "EMAS", score: 48.2, depth: "broker", reasons: "asing beli 14/20; broker besar net beli",
      cmf: -0.05, obv_slope: 0.01, ad_slope: -0.02, foreign_net: 26263600, foreign_ratio: 0.7, runup: -0.09,
    },
    {
      ticker: "KEEN", score: 19, depth: "foreign", reasons: "sinyal lemah",
      cmf: -0.1, obv_slope: -0.01, ad_slope: 0.01, foreign_net: -1000, foreign_ratio: 0.3, runup: 0,
    },
  ],
};

describe("AccumulationCard (render)", () => {
  test("menampilkan tier, badge, sinyal bertentangan, dan catatan", () => {
    const html = renderToStaticMarkup(createElement(AccumulationCard, { data: sample }));
    expect(html).toContain("EMAS");
    expect(html).toContain("Broker besar");
    expect(html).toContain("Arus asing");
    expect(html).toContain("scan tidak lengkap");
    expect(html).toContain("arus asing net jual");
    expect(html).toContain("CMF negatif");
    expect(html).toContain("Bukan label institusi");
  });

  test("kasus kosong + data basi", () => {
    const html = renderToStaticMarkup(
      createElement(AccumulationCard, {
        data: { scan_date: null, status: null, stale: true, stale_trading_days: 5, candidates: [] },
      })
    );
    expect(html).toContain("Tidak ada kandidat");
    expect(html).toContain("data basi");
  });

  test("error jelas", () => {
    const html = renderToStaticMarkup(
      createElement(AccumulationCard, {
        data: { scan_date: null, status: null, stale: false, stale_trading_days: null, candidates: [], error: "Belum ada hasil scan akumulasi." },
      })
    );
    expect(html).toContain("Belum ada hasil scan");
  });
});
