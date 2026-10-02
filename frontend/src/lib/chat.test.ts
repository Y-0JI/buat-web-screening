import { describe, expect, test } from "bun:test";
import { needsAccumulationCard, toolCallNames } from "./chat";

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
