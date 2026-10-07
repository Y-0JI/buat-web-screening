import { describe, expect, test } from "bun:test";
import { getOrderFlow, needsAccumulationCard, toolCallNames } from "./chat";

describe("replay helper akumulasi", () => {
  test("mendeteksi tool akumulasi dari riwayat thread", () => {
    const calls = [
      { name: "get_broker_summary" },
      { name: "get_accumulation_candidates" },
    ];
    expect(needsAccumulationCard(calls)).toBe(true);
    expect(toolCallNames(calls)).toEqual([
      "get_broker_summary",
      "get_accumulation_candidates",
    ]);
  });

  test("false bila tidak ada tool akumulasi / input bukan array", () => {
    expect(needsAccumulationCard([{ name: "get_price_history" }])).toBe(false);
    expect(needsAccumulationCard(null)).toBe(false);
    expect(needsAccumulationCard("x")).toBe(false);
  });
});

describe("getOrderFlow paging", () => {
  test("mengirim param page dan membaca page/total_pages", async () => {
    let url = "";
    const realFetch = globalThis.fetch;
    globalThis.fetch = (async (u: string | URL | Request) => {
      url = String(u);
      return new Response(
        JSON.stringify({
          success: true,
          data: { code: "BBCA", date: "2026-10-06", total: 250, page: 2, per_page: 100, total_pages: 3, rows: [] },
        })
      );
    }) as typeof fetch;
    try {
      const out = await getOrderFlow("BBCA", { page: 2 });
      expect(url).toContain("page=2");
      expect(out?.page).toBe(2);
      expect(out?.total_pages).toBe(3);
    } finally {
      globalThis.fetch = realFetch;
    }
  });
});
