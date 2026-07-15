"use client";

import { useState } from "react";
import { SearchBar } from "@/components/search-bar";
import { UploadArea } from "@/components/upload-area";
import { DynamicRenderer } from "@/components/renderers";
import { Card, Button, EmptyState } from "@/components/ui";
import {
  researchStock,
  compareStocks,
  screenStocks,
  analyzeVision,
  resolveTickers,
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

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const intent = detectIntent(query);

      if (intent === "screen") {
        const res = await screenStocks(mode);
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
          const res = await compareStocks(resolveRes.tickers, mode);
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
    <main className="flex flex-col items-center px-4 py-10">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-zinc-100 mb-2">BSJP AI</h1>
        <p className="text-zinc-500 text-sm">Riset saham Indonesia — cukup tanya</p>
      </div>

      <div className="w-full max-w-3xl space-y-6">
        <SearchBar onSearch={handleSearch} loading={loading} mode={mode} onModeChange={setMode} />
        <UploadArea onFileSelect={handleFileUpload} disabled={loading} />

        {loading && (
          <div className="text-zinc-500 text-sm animate-pulse">Menganalisis...</div>
        )}

        {error && (
          <Card variant="outlined" padding="md" className="border-red-900/50 bg-red-950/20">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 text-red-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          </Card>
        )}

        {result ? (
          <DynamicRenderer result={result} />
        ) : (
          <EmptyState
            icon={
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            }
            title="Mulai riset saham"
            description="Ketik nama saham, minta rekomendasi, atau bandingkan beberapa saham di atas."
          />
        )}
      </div>
    </main>
  );
}