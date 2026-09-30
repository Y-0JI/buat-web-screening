"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteThread,
  fetchModels,
  getHistory,
  getThread,
  listThreads,
  streamChat,
  type ChatEvent,
  type ModelInfo,
  type ThreadSummary,
} from "@/lib/chat";
import { Composer } from "./composer";
import { Message } from "./message";
import { Sidebar } from "./sidebar";
import type { UIChart, UIMessage } from "./types";

const SUGGESTIONS = [
  "Analisa BBCA sekarang",
  "Saham akumulasi broker hari ini",
  "Bandingkan BBCA vs BBRI",
  "Seasonality IHSG bulan ini",
];

const MODEL_KEY = "idx_copilot_model";

let seq = 0;
const uid = () => `m${Date.now()}-${seq++}`;

export function ChatApp() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState("coba9router");
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
    setSidebarOpen(false);
  }, []);

  const selectThread = useCallback(async (id: number) => {
    abortRef.current?.abort();
    setStreaming(false);
    setSidebarOpen(false);
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
          if (m.role !== "user") {
            for (const c of calls) {
              if (c.name !== "get_price_history" || c.ok === false) continue;
              const ticker = String(c.args?.ticker || "");
              const period = String(c.args?.period || "3mo");
              if (!ticker) continue;
              try {
                const series = await getHistory(ticker, period);
                if (series.length) charts.push({ ticker, period, series });
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

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900/40">
        <div className="h-14 flex items-center px-4 border-b border-zinc-800">
          <span className="text-sm font-semibold">Analisis Saham AI</span>
        </div>
        <Sidebar
          threads={threads}
          activeId={activeId}
          onSelect={selectThread}
          onNew={newChat}
          onDelete={removeThread}
        />
      </aside>

      {/* Sidebar mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72 bg-zinc-900 border-r border-zinc-800">
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

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex items-center gap-3 px-4 border-b border-zinc-800">
          <button
            className="md:hidden p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400"
            onClick={() => setSidebarOpen(true)}
            aria-label="Menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <h1 className="text-sm font-semibold leading-tight">Analisis Saham AI</h1>
            <p className="text-[11px] text-zinc-500 leading-tight">IDX Edge PRO · 9router</p>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs px-3 py-2">
                {error}
              </div>
            )}

            {messages.length === 0 && (
              <div className="pt-10 text-center">
                <h2 className="text-lg font-semibold text-zinc-200">Ada yang bisa saya bantu?</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  Tanya soal saham IDX — saya ambilkan data & analisanya.
                </p>
                <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-xl mx-auto">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="text-left px-4 py-3 rounded-xl border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800/70 hover:border-zinc-700 text-sm text-zinc-300 transition-colors"
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

        <div className="border-t border-zinc-800">
          <div className="max-w-3xl mx-auto px-4 py-3">
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
      </main>
    </div>
  );
}
