"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteThread,
  fetchModels,
  getAccumulationLatest,
  getBrokerSummary,
  getFundamentals,
  getHistory,
  getThread,
  listThreads,
  needsAccumulationCard,
  streamChat,
  type AccumulationResult,
  type BrokerSummary,
  type ChatEvent,
  type FundamentalData,
  type ModelInfo,
  type ThreadSummary,
} from "@/lib/chat";
import { Composer } from "../chat/composer";
import { Message } from "../chat/message";
import { Sidebar } from "../chat/sidebar";
import type { UIChart, UIMessage } from "../chat/types";

export type AiView = "normal" | "minimized" | "fullscreen";

const SUGGESTIONS = [
  "Analisa BBCA sekarang",
  "Saham akumulasi broker hari ini",
  "Bandingkan BBCA vs BBRI",
];

const MODEL_KEY = "idx_copilot_model";

let seq = 0;
const uid = () => `m${Date.now()}-${seq++}`;

interface Props {
  view: AiView;
  onView: (v: AiView) => void;
}

export function AiPanel({ view, onView }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState("coba9router");
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [threadsOpen, setThreadsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchModels()
      .then((m) => {
        setModels(m);
        const saved = typeof window !== "undefined" ? localStorage.getItem(MODEL_KEY) : null;
        const ids = new Set(m.map((x) => x.id));
        if (saved && ids.has(saved)) setModel(saved);
        else if (!ids.has("coba9router") && m[0]) setModel(m[0].id);
      })
      .catch(() => setError("Gagal memuat daftar model. Periksa koneksi backend."));
    refreshThreads();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const refreshThreads = useCallback(async () => {
    try {
      setThreads(await listThreads());
    } catch {
      /* diamkan */
    }
  }, []);

  const changeModel = useCallback((id: string) => {
    setModel(id);
    try {
      localStorage.setItem(MODEL_KEY, id);
    } catch {
      /* ignore */
    }
  }, []);

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    setActiveId(null);
    setMessages([]);
    setError(null);
    setThreadsOpen(false);
  }, []);

  const selectThread = useCallback(async (id: number) => {
    abortRef.current?.abort();
    setStreaming(false);
    setThreadsOpen(false);
    try {
      const detail = await getThread(id);
      if (!detail) return;
      setActiveId(id);
      if (detail.model) changeModel(detail.model);

      const loaded = await Promise.all(
        detail.messages.map(async (m): Promise<UIMessage> => {
          const calls = Array.isArray(m.tool_calls)
            ? (m.tool_calls as { name: string; args?: Record<string, unknown>; ok?: boolean }[])
            : [];
          const charts: UIChart[] = [];
          const brokers: BrokerSummary[] = [];
          const fundamentals: FundamentalData[] = [];
          const accumulations: AccumulationResult[] = [];
          const brokerTickers = new Set<string>();
          const fundamentalTickers = new Set<string>();
          if (m.role !== "user") {
            for (const c of calls) {
              if (c.ok === false) continue;
              const ticker = String(c.args?.ticker || "");
              if (!ticker) continue;
              if (c.name === "get_price_history") {
                const period = String(c.args?.period || "3mo");
                try {
                  const series = await getHistory(ticker, period);
                  if (series.length) charts.push({ ticker, period, series });
                } catch {
                  /* lewati */
                }
              } else if (c.name === "get_broker_summary") {
                brokerTickers.add(ticker.toUpperCase());
              } else if (c.name === "get_fundamentals") {
                fundamentalTickers.add(ticker.toUpperCase());
              }
            }
            for (const code of brokerTickers) {
              try {
                const res = await getBrokerSummary(code, { flow: "all", net: true, limit: 50, level_limit: 10 });
                if (res) brokers.push(res);
              } catch {
                /* lewati */
              }
            }
            for (const code of fundamentalTickers) {
              try {
                const res = await getFundamentals(code);
                if (res) fundamentals.push(res);
              } catch {
                /* lewati */
              }
            }
            if (needsAccumulationCard(calls)) {
              try {
                const res = await getAccumulationLatest();
                if (res) accumulations.push(res);
              } catch {
                /* lewati */
              }
            }
          }
          return {
            id: uid(),
            role: m.role === "user" ? "user" : "assistant",
            content: m.content,
            reasoning: m.reasoning || undefined,
            tools: calls.length ? calls.map((t) => ({ name: t.name, ok: t.ok })) : undefined,
            charts: charts.length ? charts : undefined,
            brokers: brokers.length ? brokers : undefined,
            fundamentals: fundamentals.length ? fundamentals : undefined,
            accumulations: accumulations.length ? accumulations : undefined,
          };
        })
      );
      setMessages(loaded);
    } catch {
      setError("Gagal membuka percakapan.");
    }
  }, [changeModel]);

  const removeThread = useCallback(
    async (id: number) => {
      try {
        await deleteThread(id);
        if (activeId === id) newChat();
        refreshThreads();
      } catch {
        setError("Gagal menghapus percakapan.");
      }
    },
    [activeId, newChat, refreshThreads]
  );

  const patchAssistant = useCallback(
    (id: string, patch: (m: UIMessage) => UIMessage) => {
      setMessages((prev) => prev.map((m) => (m.id === id ? patch(m) : m)));
    },
    []
  );

  const send = useCallback(
    async (text?: string) => {
      const content = (text ?? input).trim();
      if (!content || streaming) return;

      const userMsg: UIMessage = { id: uid(), role: "user", content };
      const assistantId = uid();
      const assistantMsg: UIMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        reasoning: "",
        tools: [],
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setStreaming(true);
      setError(null);

      let threadId = activeId;
      const controller = new AbortController();
      abortRef.current = controller;

      const onEvent = (event: ChatEvent) => {
        switch (event.type) {
          case "thread":
            threadId = event.id;
            setActiveId(event.id);
            break;
          case "reasoning":
            patchAssistant(assistantId, (m) => ({ ...m, reasoning: (m.reasoning || "") + event.delta }));
            break;
          case "token":
            patchAssistant(assistantId, (m) => ({ ...m, content: m.content + event.delta }));
            break;
          case "tool_start":
            patchAssistant(assistantId, (m) => ({
              ...m,
              tools: [...(m.tools || []), { name: event.name, running: true }],
            }));
            break;
          case "tool_result":
            patchAssistant(assistantId, (m) => {
              const tools = [...(m.tools || [])];
              const idx = [...tools].reverse().findIndex((t) => t.name === event.name && t.running);
              if (idx >= 0) {
                const real = tools.length - 1 - idx;
                tools[real] = { name: event.name, ok: event.ok, running: false };
              }
              return { ...m, tools };
            });
            break;
          case "chart":
            patchAssistant(assistantId, (m) => ({
              ...m,
              charts: [
                ...(m.charts || []),
                { ticker: event.ticker, period: event.period, series: event.series },
              ],
            }));
            break;
          case "broker": {
            const code = event.ticker;
            void (async () => {
              try {
                const res = await getBrokerSummary(code, { flow: "all", net: true, limit: 50, level_limit: 10 });
                if (!res) return;
                patchAssistant(assistantId, (m) => {
                  if ((m.brokers || []).some((b) => b.stock_code === code)) return m;
                  return { ...m, brokers: [...(m.brokers || []), res] };
                });
              } catch {
                /* lewati */
              }
            })();
            break;
          }
          case "fundamental":
            patchAssistant(assistantId, (m) => {
              if ((m.fundamentals || []).some((f) => f.ticker === event.data.ticker)) return m;
              return { ...m, fundamentals: [...(m.fundamentals || []), event.data] };
            });
            break;
          case "accumulation":
            patchAssistant(assistantId, (m) => ({
              ...m,
              accumulations: [...(m.accumulations || []), event.data],
            }));
            break;
          case "done":
            patchAssistant(assistantId, (m) => ({
              ...m,
              content: event.content || m.content,
              reasoning: event.reasoning || m.reasoning,
              streaming: false,
            }));
            setStreaming(false);
            refreshThreads();
            break;
          case "error":
            patchAssistant(assistantId, (m) => ({
              ...m,
              content: m.content || `⚠️ ${event.message}`,
              streaming: false,
            }));
            setStreaming(false);
            break;
        }
      };

      try {
        await streamChat({
          message: content,
          threadId,
          model,
          signal: controller.signal,
          onEvent,
        });
      } catch {
        patchAssistant(assistantId, (m) => ({
          ...m,
          content: m.content || "⚠️ Koneksi terputus. Coba lagi.",
          streaming: false,
        }));
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [activeId, input, model, patchAssistant, refreshThreads, streaming]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, []);

  if (view === "minimized") {
    return (
      <aside className="hidden md:flex w-12 shrink-0 flex-col items-center gap-2 border-l border-border bg-surface-1/40 py-3">
        <button
          onClick={() => onView("normal")}
          className="p-2 rounded-lg hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
          aria-label="Buka AI Copilot"
          title="Buka AI Copilot"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.5l-2 2m-7 7l-2 2m11 0l-2-2m-7-7l-2-2M12 8a4 4 0 100 8 4 4 0 000-8z" />
          </svg>
        </button>
      </aside>
    );
  }

  const shell =
    view === "fullscreen"
      ? "fixed inset-0 z-50 bg-surface-0 flex flex-col min-h-0"
      : "hidden md:flex w-[400px] shrink-0 flex-col min-h-0 border-l border-border bg-surface-1/40 relative";

  return (
    <aside className={shell}>
      <header className="h-12 shrink-0 flex items-center gap-1 px-2 border-b border-border">
        <button
          className="p-1.5 rounded-lg hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
          onClick={() => setThreadsOpen(true)}
          aria-label="Riwayat percakapan"
          title="Riwayat percakapan"
        >
          <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div className="flex-1 min-w-0 px-1">
          <h2 className="text-xs font-semibold leading-tight truncate">AI Copilot</h2>
          <p className="text-[10px] text-text-muted leading-tight truncate">IDX Edge PRO</p>
        </div>
        <button
          className="p-1.5 rounded-lg hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
          onClick={newChat}
          aria-label="Percakapan baru"
          title="Percakapan baru"
        >
          <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
        {view === "fullscreen" ? (
          <button
            className="p-1.5 rounded-lg hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
            onClick={() => onView("normal")}
            aria-label="Keluar fullscreen"
            title="Keluar fullscreen"
          >
            <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9l-5 5m11-5v-4.5m0 4.5h4.5m-4.5 0l5 5M9 15v4.5M9 15H4.5m4.5 0l-5-5m11 5v4.5m0-4.5h4.5m-4.5 0l5-5" />
            </svg>
          </button>
        ) : (
          <>
            <button
              className="p-1.5 rounded-lg hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
              onClick={() => onView("minimized")}
              aria-label="Minimize"
              title="Minimize"
            >
              <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
            </button>
            <button
              className="p-1.5 rounded-lg hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
              onClick={() => onView("fullscreen")}
              aria-label="Fullscreen"
              title="Fullscreen"
            >
              <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
              </svg>
            </button>
          </>
        )}
      </header>

      {threadsOpen && (
        <div className="absolute inset-0 z-40">
          <div className="absolute inset-0 bg-black/60" onClick={() => setThreadsOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72 bg-surface-1 border-r border-border">
            <Sidebar
              threads={threads}
              activeId={activeId}
              onSelect={selectThread}
              onNew={newChat}
              onDelete={removeThread}
            />
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto min-h-0">
        <div className={`${view === "fullscreen" ? "max-w-3xl" : "max-w-full"} mx-auto px-3 py-4 space-y-3`}>
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-500 text-xs px-3 py-2">
              {error}
            </div>
          )}

          {messages.length === 0 && (
            <div className="pt-6 text-center">
              <h3 className="text-sm font-semibold text-text-primary">Ada yang bisa saya bantu?</h3>
              <p className="text-xs text-text-muted mt-1">
                Tanya soal saham IDX — saya ambilkan data & analisanya.
              </p>
              <div className="mt-4 grid grid-cols-1 gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left px-3 py-2.5 rounded-xl border border-border bg-surface-1/50 hover:bg-surface-2/70 text-xs text-text-secondary transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <Message key={m.id} msg={m} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-border shrink-0">
        <div className={`${view === "fullscreen" ? "max-w-3xl" : "max-w-full"} mx-auto px-3 py-2.5`}>
          <Composer
            value={input}
            onChange={setInput}
            onSend={() => send()}
            onStop={stop}
            streaming={streaming}
            models={models}
            model={model}
            onModel={changeModel}
          />
        </div>
      </div>
    </aside>
  );
}
