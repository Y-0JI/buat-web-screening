"use client";

import { useState } from "react";
import { SearchBar } from "@/components/search-bar";
import { UploadArea } from "@/components/upload-area";
import { DynamicRenderer } from "@/components/renderers";
import {
  researchStock,
  compareStocks,
  screenStocks,
  analyzeVision,
  resolveTickers,
  sendChatMessage,
  type AppResult,
  type ChatMessage,
} from "@/lib/api";

function detectIntent(
  query: string
): "research" | "compare" | "screen" {
  const q = query.toLowerCase();
  if (
    q.includes("bandingkan") ||
    q.includes("compare") ||
    q.includes("vs")
  ) {
    return "compare";
  }
  if (
    q.includes("cari") ||
    q.includes("terbaik") ||
    q.includes("screen") ||
    q.includes("rekomendasi")
  ) {
    return "screen";
  }
  return "research";
}

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AppResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<string>("BSJP");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [showChat, setShowChat] = useState(false);

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const intent = detectIntent(query);

      if (intent === "screen") {
        const res = await screenStocks();
        if (res.success && res.data) {
          setResult({ type: "ranking", data: res.data });
        } else {
          setError(res.error || "Gagal screening");
        }
      } else if (intent === "compare") {
        const resolveRes = await resolveTickers(query);
        if (!resolveRes.tickers || resolveRes.tickers.length < 2) {
          setError("Butuh minimal 2 ticker valid untuk perbandingan");
        } else {
          const res = await compareStocks(resolveRes.tickers);
          if (res.success && res.data) {
            setResult({ type: "comparison", data: res.data });
          } else {
            setError(res.error || "Gagal membandingkan");
          }
        }
      } else {
        const res = await researchStock(query, undefined, mode);
        if (res.success && res.data) {
          setResult({ type: "stock-report", data: res.data });
        } else {
          setError(res.error || "Terjadi kesalahan");
        }
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Gagal menghubungi server";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async (message: string) => {
    if (!message.trim() || chatLoading) return;

    const userMsg: ChatMessage = { role: "user", content: message };
    setChatHistory((prev) => [...prev, userMsg]);
    setChatLoading(true);

    try {
      const res = await sendChatMessage([...chatHistory, userMsg], mode);
      if (res.success && res.reply) {
        const modelMsg: ChatMessage = { role: "model", content: res.reply };
        setChatHistory((prev) => [...prev, modelMsg]);
      } else {
        setError(res.error || "Chat gagal");
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Gagal menghubungi server";
      setError(msg);
    } finally {
      setChatLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await analyzeVision(file);
      if (res.success && res.data) {
        setResult({ type: "vision-analysis", data: res.data });
      } else {
        setError(res.error || "Gagal menganalisis gambar");
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Gagal menghubungi server";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex flex-col items-center px-4 py-16">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-zinc-100 mb-2">BSJP AI</h1>
        <p className="text-zinc-500 text-sm">
          Riset saham Indonesia — cukup tanya
        </p>
      </div>

      <div className="w-full max-w-3xl space-y-6">
        <SearchBar onSearch={handleSearch} loading={loading} mode={mode} onModeChange={setMode} />
        <UploadArea onFileSelect={handleFileUpload} disabled={loading} />

        {loading && (
          <div className="text-zinc-500 text-sm animate-pulse">
            Menganalisis...
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-950/30 border border-red-900/50 rounded-2xl text-red-400 text-sm">
            {error}
          </div>
        )}

        {result && <DynamicRenderer result={result} />}

        <div className="border-t border-zinc-800 pt-6">
          <button
            onClick={() => setShowChat(!showChat)}
            className="w-full text-left text-zinc-400 hover:text-zinc-100 font-medium flex items-center gap-2"
          >
            <svg className={`w-5 h-5 transition-transform ${showChat ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span>Mode Chat AI ({chatHistory.length} pesan)</span>
          </button>

          {showChat && (
            <div className="mt-4 space-y-3 max-h-96 overflow-y-auto">
              {chatHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                      msg.role === "user"
                        ? "bg-blue-950/50 text-blue-100 rounded-br-none"
                        : "bg-zinc-800/50 text-zinc-100 rounded-bl-none"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start gap-3">
                  <div className="bg-zinc-800/50 p-3 rounded-2xl rounded-bl-none text-sm text-zinc-400 animate-pulse">
                    Mengetik...
                  </div>
                </div>
              )}
              <div className="flex gap-2 mt-2">
                <input
                  type="text"
                  placeholder="Tanya soal saham... (mis. gimana CDIA sekarang?)"
                  className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.currentTarget.value.trim()) {
                      handleChat(e.currentTarget.value.trim());
                      e.currentTarget.value = "";
                    }
                  }}
                  disabled={chatLoading}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}