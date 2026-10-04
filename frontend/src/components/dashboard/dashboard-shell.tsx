"use client";

import { useState } from "react";
import { FALLBACK_TICKER } from "@/lib/chat";
import { AiPanel, type AiView } from "../ai/ai-panel";
import { DashboardPanel } from "./dashboard-panel";
import { SearchBar } from "./search-bar";

export function DashboardShell() {
  const [aiView, setAiView] = useState<AiView>("normal");
  const [ticker, setTicker] = useState(FALLBACK_TICKER);

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      <header className="h-14 shrink-0 flex items-center gap-4 px-4 border-b border-zinc-800">
        <img src="/logos.png" alt="Logo" className="h-7 w-auto shrink-0" />
        <SearchBar value={ticker} onSelect={setTicker} />
      </header>

      <div className="flex flex-1 min-h-0">
        <main className="flex-1 flex flex-col min-w-0 min-h-0">
          <DashboardPanel
            ticker={ticker}
            onTicker={setTicker}
            onOpenAi={() => setAiView("fullscreen")}
          />
        </main>

        <AiPanel view={aiView} onView={setAiView} />
      </div>

      {aiView !== "fullscreen" && (
        <button
          type="button"
          onClick={() => setAiView("fullscreen")}
          className="md:hidden fixed bottom-5 right-4 z-40 flex items-center gap-2 px-4 py-3 rounded-full bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium shadow-lg transition-colors"
          aria-label="Buka AI Copilot"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.5l-2 2m-7 7l-2 2m11 0l-2-2m-7-7l-2-2M12 8a4 4 0 100 8 4 4 0 000-8z" />
          </svg>
          AI Copilot
        </button>
      )}
    </div>
  );
}
