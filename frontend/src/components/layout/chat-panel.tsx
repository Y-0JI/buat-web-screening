"use client";

import { useState, useRef, useEffect, useCallback, useMemo, type KeyboardEvent } from "react";
import { sendChatMessage, type ChatMessage } from "@/lib/api";
import { useWorkspace } from "@/lib/workspace-context";

const TICKER_REGEX = /\b[A-Z]{2,5}\b/g;

function extractTickers(text: string): string[] {
  const matches = text.toUpperCase().match(TICKER_REGEX);
  return matches ? [...new Set(matches)] : [];
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let inList = false;
  let listItems: React.ReactNode[] = [];

  function flushList() {
    if (inList && listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-0.5 my-1">
          {listItems}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    let line = escapeHtml(lines[i]);

    line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    line = line.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
    line = line.replace(/`(.+?)`/g, '<code class="bg-zinc-700 px-1 py-0.5 rounded text-xs">$1</code>');

    if (line.match(/^[\s]*[-*]\s/)) {
      inList = true;
      const content = line.replace(/^[\s]*[-*]\s/, "");
      listItems.push(
        <li key={i} dangerouslySetInnerHTML={{ __html: content }} />
      );
      continue;
    }

    flushList();

    if (line.startsWith("### ")) {
      elements.push(
        <h4 key={i} className="text-sm font-bold text-zinc-200 mt-2 mb-1" dangerouslySetInnerHTML={{ __html: line.slice(4) }} />
      );
    } else if (line.startsWith("## ")) {
      elements.push(
        <h3 key={i} className="text-sm font-bold text-zinc-200 mt-2 mb-1" dangerouslySetInnerHTML={{ __html: line.slice(3) }} />
      );
    } else if (line.startsWith("# ")) {
      elements.push(
        <h2 key={i} className="text-base font-bold text-zinc-200 mt-2 mb-1" dangerouslySetInnerHTML={{ __html: line.slice(2) }} />
      );
    } else if (line.trim() === "") {
      elements.push(<br key={i} />);
    } else {
      elements.push(
        <span key={i} dangerouslySetInnerHTML={{ __html: line }} />
      );
      elements.push(<br key={`br-${i}`} />);
    }
  }

  flushList();
  return elements;
}

interface ChatPanelProps {
  open: boolean;
  onClose: () => void;
  mode: string;
}

const viewLabels: Record<string, string> = {
  dashboard: "Beranda",
  research: "Riset",
  screening: "Screening",
  compare: "Perbandingan",
  watchlist: "Watchlist",
};

export function ChatPanel({ open, onClose, mode }: ChatPanelProps) {
  const { state, dispatch, openResearch, openCompare, openWatchlist, openScreening } = useWorkspace();
  const { view, activeTicker, compareTickers, activeMode, chatInputDraft } = state;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevViewRef = useRef(view);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (prevViewRef.current !== view) {
      setMessages([]);
      prevViewRef.current = view;
    }
  }, [view]);

  useEffect(() => {
    if (chatInputDraft) {
      setInput(chatInputDraft);
      dispatch({ type: "SET_CHAT_INPUT", input: "" });
    }
  }, [chatInputDraft, dispatch]);

  const contextPayload = useMemo(() => ({
    view,
    ticker: activeTicker ?? undefined,
    tickers: compareTickers.length > 0 ? compareTickers : undefined,
    mode: activeMode,
  }), [view, activeTicker, compareTickers, activeMode]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: input.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChatMessage(newMessages, activeMode, contextPayload);
      if (res.success && res.reply) {
        setMessages((prev) => [
          ...prev,
          { role: "model", content: res.reply! },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "model", content: "Gagal menghubungi AI. Coba lagi." },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, activeMode, contextPayload]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!open) return null;

  const lastAIReply = [...messages].reverse().find((m) => m.role === "model");
  const replyTickers = lastAIReply ? extractTickers(lastAIReply.content) : [];
  const suggestedTickers = replyTickers.filter((t) => t !== activeMode && t !== "IDX" && t !== "BSJP" && t !== "BPJS");

  return (
    <aside className="w-[380px] h-full bg-zinc-950 border-l border-zinc-800 flex flex-col shrink-0">
      <div className="flex items-center justify-between px-4 h-14 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <h2 className="text-sm font-semibold text-zinc-200">Asisten AI</h2>
          <span className="text-[10px] text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">{activeMode}</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          aria-label="Close chat"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="px-4 py-2 border-b border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center gap-2 text-[11px] text-zinc-500">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
          <span>
            {viewLabels[view] || view}
            {activeTicker && <span className="text-zinc-300 font-medium"> &middot; {activeTicker}</span>}
            {!activeTicker && compareTickers.length > 0 && (
              <span className="text-zinc-300 font-medium"> &middot; {compareTickers.join(", ")}</span>
            )}
          </span>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <svg className="w-10 h-10 text-zinc-700 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-zinc-500 text-sm">Tanya apa saja tentang saham Indonesia</p>
            <p className="text-zinc-600 text-xs mt-1">Contoh: &quot;Gimana BBCA sekarang?&quot;</p>
            {view === "research" && activeTicker && (
              <p className="text-blue-400/60 text-xs mt-2">Sedang di Riset: {activeTicker}</p>
            )}
            {view === "compare" && compareTickers.length > 0 && (
              <p className="text-blue-400/60 text-xs mt-2">Sedang di Perbandingan: {compareTickers.join(", ")}</p>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600/20 text-blue-100 rounded-br-md"
                  : "bg-zinc-800 text-zinc-200 rounded-bl-md"
              }`}
            >
              {msg.role === "model" ? renderMarkdown(msg.content) : msg.content}
            </div>
          </div>
        ))}

        {suggestedTickers.length > 0 && !loading && lastAIReply && (
          <div className="flex flex-wrap gap-1.5 pl-1">
            {suggestedTickers.slice(0, 5).map((ticker) => (
              <button
                key={ticker}
                onClick={() => openResearch(ticker, activeMode)}
                className="px-2.5 py-1 text-[11px] font-medium bg-blue-600/15 text-blue-400 hover:bg-blue-600/30 rounded-full transition-colors border border-blue-500/20"
              >
                {ticker}
              </button>
            ))}
          </div>
        )}

        {suggestedTickers.length >= 2 && !loading && lastAIReply && (
          <div className="flex gap-1.5 pl-1">
            <button
              onClick={() => openCompare(suggestedTickers.slice(0, 5), activeMode)}
              className="px-2.5 py-1 text-[11px] font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 rounded-full transition-colors border border-zinc-700"
            >
              Bandingkan {suggestedTickers.slice(0, 5).join(", ")}
            </button>
            {activeTicker && view !== "watchlist" && (
              <button
                onClick={() => {
                  openResearch(activeTicker, activeMode);
                }}
                className="px-2.5 py-1 text-[11px] font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 rounded-full transition-colors border border-zinc-700"
              >
                Lihat {activeTicker}
              </button>
            )}
          </div>
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 px-3 py-2 rounded-2xl rounded-bl-md">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-zinc-800 space-y-2">
        {messages.length > 0 && !loading && (
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            <button
              onClick={() => openScreening(activeMode)}
              className="shrink-0 px-2 py-0.5 text-[10px] bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 rounded transition-colors"
            >
              Screening
            </button>
            <button
              onClick={() => openCompare(activeTicker ? [activeTicker, "BBCA"] : ["BBCA", "BBRI"], activeMode)}
              className="shrink-0 px-2 py-0.5 text-[10px] bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 rounded transition-colors"
            >
              Bandingkan
            </button>
            <button
              onClick={openWatchlist}
              className="shrink-0 px-2 py-0.5 text-[10px] bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 rounded transition-colors"
            >
              Watchlist
            </button>
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={view === "research" && activeTicker ? `Tanya soal ${activeTicker}...` : "Tanya soal saham..."}
            className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white rounded-lg transition-colors"
            aria-label="Send"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
