// Klien API chat-first: models, threads, dan streaming SSE.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ModelCapabilities {
  vision: boolean;
  tools: boolean;
  reasoning: boolean;
  search: boolean;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  provider_label: string;
  capabilities: ModelCapabilities;
  context_window?: number | null;
}

export interface ThreadSummary {
  id: number;
  title: string;
  model?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ChatMessageRow {
  id: number;
  role: string;
  content: string;
  reasoning?: string | null;
  tool_calls?: unknown;
  model?: string | null;
  created_at?: string | null;
}

export interface ThreadDetail extends ThreadSummary {
  messages: ChatMessageRow[];
}

export interface HistoryPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BrokerRow {
  code: string | null;
  name?: string | null;
  bval: number;
  bvol: number;
  bavg: number | null;
  sval: number;
  svol: number;
  savg: number | null;
  nval: number;
  nvol: number;
}

export interface BrokerSummary {
  stock_code: string | null;
  flow: string | null;
  net: boolean | null;
  start_date: string | null;
  end_date: string | null;
  summary: {
    buyer_count: number;
    seller_count: number;
    net_value: number;
    net_volume: number;
    avg_price: number | null;
  };
  top: { n: number; net_value: number; net_volume: number }[];
  levels: unknown;
  brokers: BrokerRow[];
}

export type ChatEvent =
  | { type: "thread"; id: number; title: string }
  | { type: "reasoning"; delta: string }
  | { type: "token"; delta: string }
  | { type: "tool_start"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; ok: boolean; summary: string }
  | { type: "chart"; ticker: string; period: string; series: HistoryPoint[] }
  | { type: "broker"; ticker: string }
  | { type: "done"; content: string; reasoning: string; tool_calls: unknown[] }
  | { type: "error"; message: string };

const DEVICE_KEY = "idx_copilot_device_id";

export function getDeviceId(): string {
  if (typeof window === "undefined") return "server";
  let id = window.localStorage.getItem(DEVICE_KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `dev-${Math.random().toString(36).slice(2)}`;
    window.localStorage.setItem(DEVICE_KEY, id);
  }
  return id;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  return { "X-Device-Id": getDeviceId(), ...(extra || {}) };
}

async function jsonOrThrow(res: Response) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchModels(): Promise<ModelInfo[]> {
  const res = await fetch(`${API_BASE}/api/models`);
  const data = await jsonOrThrow(res);
  return data.data || [];
}

export async function getHistory(
  ticker: string,
  period = "3mo"
): Promise<HistoryPoint[]> {
  const res = await fetch(
    `${API_BASE}/api/history/${encodeURIComponent(ticker)}?period=${encodeURIComponent(period)}`
  );
  const data = await jsonOrThrow(res);
  return data.data || [];
}

export interface BrokerParams {
  start_date?: string;
  end_date?: string;
  flow?: string;
  net?: boolean;
  limit?: number;
}

export async function getBrokerSummary(
  ticker: string,
  params: BrokerParams = {}
): Promise<BrokerSummary | null> {
  const q = new URLSearchParams();
  if (params.start_date) q.set("start_date", params.start_date);
  if (params.end_date) q.set("end_date", params.end_date);
  if (params.flow) q.set("flow", params.flow);
  q.set("net", String(params.net ?? false));
  if (params.limit) q.set("limit", String(params.limit));
  const res = await fetch(
    `${API_BASE}/api/broker-summary/${encodeURIComponent(ticker)}?${q.toString()}`
  );
  const data = await jsonOrThrow(res);
  return data.success ? (data.data as BrokerSummary) : null;
}

export async function listThreads(): Promise<ThreadSummary[]> {
  const res = await fetch(`${API_BASE}/api/threads`, { headers: authHeaders() });
  const data = await jsonOrThrow(res);
  return data.data || [];
}

export async function createThread(model?: string): Promise<ThreadSummary> {
  const res = await fetch(`${API_BASE}/api/threads`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ model }),
  });
  const data = await jsonOrThrow(res);
  return data.data;
}

export async function getThread(id: number): Promise<ThreadDetail | null> {
  const res = await fetch(`${API_BASE}/api/threads/${id}`, {
    headers: authHeaders(),
  });
  if (res.status === 404) return null;
  const data = await jsonOrThrow(res);
  return data.data;
}

export async function renameThread(id: number, title: string): Promise<void> {
  await fetch(`${API_BASE}/api/threads/${id}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title }),
  });
}

export async function deleteThread(id: number): Promise<void> {
  await fetch(`${API_BASE}/api/threads/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

export interface StreamChatOptions {
  message: string;
  threadId?: number | null;
  model?: string;
  signal?: AbortSignal;
  onEvent: (event: ChatEvent) => void;
}

export async function streamChat(opts: StreamChatOptions): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      message: opts.message,
      thread_id: opts.threadId ?? null,
      model: opts.model,
    }),
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    opts.onEvent({ type: "error", message: text || `HTTP ${res.status}` });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        opts.onEvent(JSON.parse(payload) as ChatEvent);
      } catch {
        // abaikan potongan yang tidak lengkap
      }
    }
  }
}
