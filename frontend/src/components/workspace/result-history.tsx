"use client";

import { useWorkspace, type RecentResult, type WorkspaceView } from "@/lib/workspace-context";
import { Tooltip } from "@/components/ui/tooltip";

interface ResultHistoryProps {
  maxItems?: number;
}

const viewLabels: Record<WorkspaceView, string> = {
  dashboard: "Beranda",
  research: "Riset",
  screening: "Screening",
  compare: "Perbandingan",
  watchlist: "Watchlist",
};

const viewIcons: Record<WorkspaceView, React.ReactNode> = {
  dashboard: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
  research: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  screening: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>,
  compare: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  watchlist: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>,
};

export function ResultHistory({ maxItems = 10 }: ResultHistoryProps) {
  const { state, dispatch, openResearch, openCompare, openScreening, openWatchlist, setDashboard } = useWorkspace();
  const items = state.recentResults.slice(0, maxItems);

  function handleResultClick(result: RecentResult) {
    switch (result.view) {
      case "research":
        if (result.ticker) openResearch(result.ticker, result.mode);
        break;
      case "compare":
        if (result.tickers?.length) openCompare(result.tickers, result.mode);
        break;
      case "screening":
        openScreening(result.mode);
        break;
      case "watchlist":
        openWatchlist();
        break;
      case "dashboard":
        setDashboard();
        break;
    }
  }

  function handleRemove(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    dispatch({ type: "REMOVE_RESULT", id });
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-4">
        <svg className="w-8 h-8 text-zinc-700 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-zinc-500 text-xs">Belum ada riwayat</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <h4 className="px-3 py-1 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Riwayat Terakhir</h4>
      {items.map((result) => (
        <Tooltip
          key={result.id}
          content={`Hapus ${result.label}`}
          side="right"
        >
          <div
            onClick={() => handleResultClick(result)}
            className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800/60 transition-colors cursor-pointer group"
          >
            <span className="text-zinc-500 shrink-0">{viewIcons[result.view]}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-zinc-200 text-sm truncate font-medium">{result.label}</span>
                <span className="text-[10px] text-zinc-500 flex-shrink-0">{viewLabels[result.view]}</span>
              </div>
              <div className="text-[10px] text-zinc-500 truncate">
                {result.ticker ? `Ticker: ${result.ticker}` : result.tickers?.join(", ")}
              </div>
            </div>
            <button
              onClick={(e) => handleRemove(e, result.id)}
              className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 p-0.5 transition-opacity shrink-0"
              aria-label="Hapus dari riwayat"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </Tooltip>
      ))}
    </div>
  );
}