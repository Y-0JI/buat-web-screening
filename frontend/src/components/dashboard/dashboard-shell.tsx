"use client";

import { useState } from "react";
import { FALLBACK_TICKER } from "@/lib/chat";
import { AiPanel, type AiView } from "../ai/ai-panel";
import { ThemeToggle } from "../theme/theme-toggle";
import { DashboardPanel } from "./dashboard-panel";
import { SearchBar } from "./search-bar";

export function DashboardShell() {
  const [aiView, setAiView] = useState<AiView>("normal");
  const [ticker, setTicker] = useState(FALLBACK_TICKER);
  const [homeTick, setHomeTick] = useState(0);

  const goHome = () => {
    setTicker(FALLBACK_TICKER);
    setHomeTick((n) => n + 1);
  };

  return (
    <div className="flex flex-col h-screen bg-surface-0 text-text-primary overflow-hidden">
      <header className="h-14 shrink-0 flex items-center gap-4 px-4 border-b border-border">
        <button
          type="button"
          onClick={goHome}
          className="shrink-0 rounded-lg focus:outline-none cursor-pointer"
          aria-label="Kembali ke beranda"
          title="Kembali ke beranda"
        >
          <img src="/logoswhite.png" alt="Logo" className="logo-dark h-7 w-auto pointer-events-none" />
          <img src="/logos.png" alt="Logo" className="logo-light h-7 w-auto pointer-events-none" />
        </button>
        <SearchBar key={homeTick} value={ticker} onSelect={setTicker} />
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        <main className="flex-1 flex flex-col min-w-0 min-h-0">
          <DashboardPanel
            ticker={ticker}
            onTicker={setTicker}
            onOpenAi={() => setAiView("fullscreen")}
            homeTick={homeTick}
          />
        </main>

        <AiPanel view={aiView} onView={setAiView} ticker={ticker} />
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
