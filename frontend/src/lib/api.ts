import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30000,
});

export interface StockReport {
  render: string;
  ticker: string;
  company_name?: string;
  price?: number;
  change_percent?: number;
  score: number;
  verdict: "BUY" | "HOLD" | "SELL" | "AVOID";
  confidence: number;
  summary: string;
  indicators: {
    ema: Record<string, number>;
    rsi?: number;
    macd?: { macd: number; signal: number; histogram: number };
    atr?: number;
    vwap?: number;
    volume_ratio?: number;
    gap_percent?: number;
    support_resistance?: { resistance: number; support: number; pivot: number };
  };
  score_breakdown: Array<{
    funnel_layer: string;
    score: number;
    weight: number;
    note: string;
  }>;
  stop_loss?: number;
  risk_percent?: number;
  disclaimer: string;
}

export interface ResearchResponse {
  success: boolean;
  data?: StockReport;
  error?: string;
}

export async function researchStock(
  query: string,
  ticker?: string
): Promise<ResearchResponse> {
  const res = await api.post<ResearchResponse>("/api/research", {
    query,
    ticker,
  });
  return res.data;
}
