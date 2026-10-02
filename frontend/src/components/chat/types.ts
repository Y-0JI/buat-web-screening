import type {
  AccumulationResult,
  BrokerSummary,
  FundamentalData,
  HistoryPoint,
} from "@/lib/chat";

export interface UITool {
  name: string;
  ok?: boolean;
  running?: boolean;
}

export interface UIChart {
  ticker: string;
  period: string;
  series: HistoryPoint[];
}

export interface UIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  tools?: UITool[];
  charts?: UIChart[];
  brokers?: BrokerSummary[];
  fundamentals?: FundamentalData[];
  accumulations?: AccumulationResult[];
  streaming?: boolean;
}
