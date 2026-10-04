"use client";

import { useEffect, useState } from "react";
import { KeyStatsPanel } from "./key-stats-panel";

interface TabDef {
  id: string;
  label: string;
  disabled?: boolean;
}

const TABS: TabDef[] = [
  { id: "key-stats", label: "Key Stats" },
  { id: "analysis", label: "Analysis" },
  { id: "financials", label: "Financials" },
  { id: "fundachart", label: "Fundachart" },
  { id: "insider", label: "Insider" },
  { id: "corp-action", label: "Corp. Action", disabled: true },
  { id: "profile", label: "Profile" },
];

export function StockTabs({ ticker }: { ticker: string }) {
  const [tab, setTab] = useState<string | null>(null);

  useEffect(() => {
    setTab(null);
  }, [ticker]);

  const click = (id: string) => setTab((prev) => (prev === id ? null : id));
  const active = TABS.find((t) => t.id === tab);

  return (
    <div className="px-4 pb-3">
      <div className="flex overflow-x-auto rounded-lg border border-border divide-x divide-border bg-surface-1">
        {TABS.map((t) => {
          const on = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              disabled={t.disabled}
              onClick={() => click(t.id)}
              className={`flex-1 whitespace-nowrap px-3 py-2 text-xs font-medium transition-colors ${
                on
                  ? "text-emerald-500"
                  : t.disabled
                    ? "text-text-muted/50 cursor-not-allowed"
                    : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === "key-stats" ? (
        <KeyStatsPanel ticker={ticker} />
      ) : active ? (
        <div className="mt-2 rounded-lg border border-border bg-surface-1 px-3 py-6 text-center text-xs text-text-muted">
          Konten {active.label} — segera
        </div>
      ) : null}
    </div>
  );
}
