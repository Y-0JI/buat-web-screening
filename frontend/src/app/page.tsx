"use client";

import { useState } from "react";
import { SearchBar } from "@/components/search-bar";
import { DynamicRenderer } from "@/components/renderers";
import { researchStock, type StockReport } from "@/lib/api";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<StockReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await researchStock(query);
      if (res.success && res.data) {
        setResult(res.data);
      } else {
        setError(res.error || "Terjadi kesalahan");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal menghubungi server";
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

      <SearchBar onSearch={handleSearch} loading={loading} />

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

      {result && <DynamicRenderer data={result} />}
    </main>
  );
}
