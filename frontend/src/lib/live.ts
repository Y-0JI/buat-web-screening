// Klien WebSocket live (harga + running trade) ke backend sendiri (/ws/live).
// API key provider tetap di server; browser tidak pernah menyentuhnya.

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "./chat";
import type { OrderFlowRow } from "./chat";

export interface LiveQuote {
  ticker: string;
  price: number;
  change_pct: number | null;
  time: string | null;
}

export interface LiveTrade extends OrderFlowRow {
  ticker: string;
}

export function wsUrl(ticker: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/live?ticker=${encodeURIComponent(ticker)}`;
}

const TRADE_CAP = 100;

export interface LiveLoadedState {
  quote: LiveQuote | null;
  trades: LiveTrade[];
}

export function reduceLiveMessage(
  prev: LiveLoadedState,
  ticker: string,
  msg: Record<string, unknown>
): LiveLoadedState {
  if (msg.type === "quote") {
    return {
      ...prev,
      quote: {
        ticker: String(msg.ticker ?? ticker),
        price: Number(msg.price),
        change_pct: msg.change_pct == null ? null : Number(msg.change_pct),
        time: (msg.time as string | null) ?? null,
      },
    };
  }
  if (msg.type === "trade" && msg.data && typeof msg.data === "object") {
    const d = msg.data as Record<string, unknown>;
    const t: LiveTrade = {
      ticker: String(d.t ?? ticker),
      time: (d.time as string | null) ?? null,
      action: (d.action as string | null) ?? null,
      price: (d.price as number | null) ?? null,
      lot: (d.lot as number | null) ?? null,
      value: (d.value as number | null) ?? null,
      buyer: (d.buyer as string | null) ?? null,
      seller: (d.seller as string | null) ?? null,
      buyer_type: null,
      seller_type: null,
      board: (d.board as string | null) ?? null,
    };
    return {
      quote:
        t.price != null
          ? { ticker: t.ticker, price: t.price, change_pct: null, time: t.time }
          : prev.quote,
      trades: [t, ...prev.trades].slice(0, TRADE_CAP),
    };
  }
  if (msg.type === "snapshot" && Array.isArray(msg.recent)) {
    const rows: LiveTrade[] = (msg.recent as Record<string, unknown>[]).map((d) => ({
      ticker,
      time: (d.time as string | null) ?? null,
      action: (d.action as string | null) ?? null,
      price: (d.price as number | null) ?? null,
      lot: (d.lot as number | null) ?? null,
      value: (d.value as number | null) ?? null,
      buyer: (d.buyer as string | null) ?? null,
      seller: (d.seller as string | null) ?? null,
      buyer_type: null,
      seller_type: null,
      board: (d.board as string | null) ?? null,
    }));
    return { ...prev, trades: rows };
  }
  return prev;
}

export function mergeTradeRows(
  rest: OrderFlowRow[],
  live: LiveTrade[],
  cap = 50
): OrderFlowRow[] {
  const key = (r: OrderFlowRow) =>
    `${r.time ?? ""}|${r.price ?? ""}|${r.lot ?? ""}|${r.buyer ?? ""}|${r.seller ?? ""}`;
  const seen = new Set<string>();
  const out: OrderFlowRow[] = [];
  for (const r of rest) {
    seen.add(key(r));
    out.push(r);
  }
  for (const l of live) {
    const k = key(l);
    if (!seen.has(k)) {
      seen.add(k);
      out.push(l);
    }
  }
  out.sort((a, b) => String(b.time ?? "").localeCompare(String(a.time ?? "")));
  return out.slice(0, cap);
}

interface LiveState {
  quote: LiveQuote | null;
  trades: LiveTrade[];
  connected: boolean;
  failed: boolean;
}

export function useLiveTicker(ticker: string, enabled: boolean) {
  const [state, setState] = useState<LiveState>({ quote: null, trades: [], connected: false, failed: false });
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled || !ticker) {
      setState({ quote: null, trades: [], connected: false, failed: false });
      return;
    }
    let closed = false;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(wsUrl(ticker));
      } catch {
        retryRef.current += 1;
        timerRef.current = setTimeout(connect, Math.min(2000 * retryRef.current, 15000));
        return;
      }
      ws.onopen = () => {
        retryRef.current = 0;
        setState((s) => ({ ...s, connected: true, failed: false }));
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data)) as Record<string, unknown>;
          if (msg.type === "hello" || msg.type === "ping") return;
          setState((s) => {
            const next = reduceLiveMessage({ quote: s.quote, trades: s.trades }, ticker, msg);
            return { ...s, quote: next.quote, trades: next.trades };
          });
        } catch {
          /* abaikan pesan rusak */
        }
      };
      const scheduleRetry = () => {
        if (closed) return;
        setState((s) => ({ ...s, connected: false }));
        retryRef.current += 1;
        const delay = Math.min(2000 * retryRef.current, 30000);
        timerRef.current = setTimeout(connect, delay);
      };
      ws.onclose = scheduleRetry;
      ws.onerror = () => {
        try {
          ws?.close();
        } catch {
          /* abaikan */
        }
        setState((s) => ({ ...s, failed: true }));
      };
    };

    connect();
    return () => {
      closed = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      try {
        ws?.close();
      } catch {
        /* abaikan */
      }
    };
  }, [ticker, enabled]);

  return state;
}
