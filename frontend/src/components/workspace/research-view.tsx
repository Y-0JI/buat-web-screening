"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { Card, Section, Skeleton, Badge, VerdictBadge } from "@/components/ui";
import { StockReportCard } from "@/components/renderers/stock-report";

export function ResearchView() {
  const { state, openResearch } = useWorkspace();
  const [tickerInput, setTickerInput] = useState(state.activeTicker ?? "");
  const [mode, setMode] = useState<"BSJP" | "BPJS">(state.activeMode);
  const [report, setReport] = useState<ReturnType<typeof StockReportCard>["props"]["data"] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (state.activeTicker) {
      setTickerInput(state.activeTicker);
    }
  }, [state.activeTicker]);

  useEffect(() => {
    if (tickerInput.trim()) {
      loadReport(tickerInput.trim().toUpperCase());
    }
  }, [tickerInput, mode]);

  async function loadReport(t: string) {
    setLoading(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/research`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: t, mode }),
        }
      );
      const json = await res.json();
      if (json.success && json.data) setReport(json.data);
    } catch {
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  function handleTickerChange(e: React.ChangeEvent<HTMLInputElement>) {
    setTickerInput(e.target.value.toUpperCase());
  }

  function handleModeChange(m: "BSJP" | "BPJS") {
    setMode(m);
    setTickerInput(tickerInput); // trigger reload
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <Card padding="md">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-4">
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={tickerInput}
              onChange={handleTickerChange}
              placeholder="Ketik kode saham (contoh: BBCA)..."
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-lg text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={e => e.key === "Enter" && tickerInput.trim() && openResearch(tickerInput.trim().toUpperCase())}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Mode:</span>
            <button
              onClick={() => handleModeChange("BSJP")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "BSJP" ? "bg-blue-600 text-white" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              BSJP
            </button>
            <button
              onClick={() => handleModeChange("BPJS")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "BPJS" ? "bg-blue-600 text-white" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              BPJS
            </button>
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="space-y-4">
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
      ) : report ? (
        <StockReportCard data={report} />
      ) : tickerInput.trim() ? (
        <Card padding="md">
          <p className="text-zinc-500 text-center">Data tidak ditemukan untuk <strong className="text-zinc-200">{tickerInput}</strong>.</p>
        </Card>
      ) : (
        <Card padding="lg" className="text-center">
          <svg className="w-16 h-16 text-zinc-700 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h3 className="text-zinc-300 font-medium mb-2">Mulai Riset Saham</h3>
          <p className="text-zinc-500">Ketik kode saham di atas untuk melihat analisis teknikal, fundamental, dan insight AI.</p>
        </Card>
      )}
    </div>
  );
}