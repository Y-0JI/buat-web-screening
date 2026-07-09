"use client";

import { useState } from "react";
import { SearchBar } from "@/components/search-bar";
import { UploadArea } from "@/components/upload-area";
import { DynamicRenderer } from "@/components/renderers";
import { VALID_TICKERS } from "@/lib/idx-stocks";
import {
  researchStock,
  compareStocks,
  screenStocks,
  analyzeVision,
  type AppResult,
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

function extractTickers(query: string): string[] {
  const candidates = query.toUpperCase().match(/\b([A-Z]{2,5})\b/g) || [];
  return candidates.filter((c) => VALID_TICKERS.includes(c)).slice(0, 5);
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
        const res = await screenStocks();
        if (res.success && res.data) {
          setResult({ type: "ranking", data: res.data });
        } else {
          setError(res.error || "Gagal screening");
        }
      } else if (intent === "compare") {
        const tickers = extractTickers(query);
        if (tickers.length < 2) {
          setError("Setidaknya 2 ticker diperlukan untuk perbandingan");
        } else {
          const res = await compareStocks(tickers);
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
    <main className="flex flex-col items-center px-4 py-16">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-zinc-100 mb-2">BSJP AI</h1>
        <p className="text-zinc-500 text-sm">
          Riset saham Indonesia — cukup tanya
        </p>
      </div>

      <SearchBar onSearch={handleSearch} loading={loading} mode={mode} onModeChange={setMode} />
      <UploadArea onFileSelect={handleFileUpload} disabled={loading} />

      {loading && (
        <div className="mt-8 text-zinc-500 text-sm animate-pulse">
          Menganalisis...
        </div>
      )}

      {error && (
        <div className="mt-6 p-4 bg-red-950/30 border border-red-900/50 rounded-2xl text-red-400 text-sm max-w-2xl w-full">
          {error}
        </div>
      )}

      {result && <DynamicRenderer result={result} />}
    </main>
  );
}
