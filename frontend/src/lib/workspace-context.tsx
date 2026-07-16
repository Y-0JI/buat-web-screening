"use client";

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { useSearchParams } from "next/navigation";
import { type AppResult } from "@/lib/api";

export type WorkspaceView =
  | "dashboard"
  | "research"
  | "screening"
  | "compare"
  | "watchlist";

export interface RecentResult {
  id: string;
  type: AppResult["type"];
  view: WorkspaceView;
  label: string;
  ticker?: string;
  tickers?: string[];
  mode: string;
  timestamp: number;
  data: unknown;
}

interface WorkspaceState {
  view: WorkspaceView;
  activeTicker: string | null;
  activeMode: "BSJP" | "BPJS";
  compareTickers: string[];
  isChatOpen: boolean;
  chatInputDraft: string;
  recentResults: RecentResult[];
  loading: boolean;
  error: string | null;
}

type WorkspaceAction =
  | { type: "SET_VIEW"; view: WorkspaceView; ticker?: string; tickers?: string[]; mode?: string }
  | { type: "TOGGLE_CHAT"; open?: boolean }
  | { type: "SET_CHAT_INPUT"; input: string }
  | { type: "ADD_RESULT"; result: RecentResult }
  | { type: "REMOVE_RESULT"; id: string }
  | { type: "CLEAR_HISTORY" }
  | { type: "SET_MODE"; mode: "BSJP" | "BPJS" }
  | { type: "SET_TICKER"; ticker: string | null }
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "RESTORE_STATE"; state: Partial<WorkspaceState> };

const STORAGE_KEY = "bsjp_workspace_history";

function loadHistory(): RecentResult[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(results: RecentResult[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(results));
  } catch {
    // ignore
  }
}

function reducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case "SET_VIEW":
      return {
        ...state,
        view: action.view,
        activeTicker: action.ticker === undefined ? state.activeTicker : action.ticker,
        compareTickers: action.tickers === undefined ? state.compareTickers : action.tickers,
        activeMode: (action.mode as "BSJP" | "BPJS") ?? state.activeMode,
      };
    case "TOGGLE_CHAT":
      return {
        ...state,
        isChatOpen: action.open ?? !state.isChatOpen,
      };
    case "SET_CHAT_INPUT":
      return {
        ...state,
        chatInputDraft: action.input,
        isChatOpen: true,
      };
    case "ADD_RESULT": {
      const filtered = state.recentResults.filter((r) => r.id !== action.result.id);
      const updated = [action.result, ...filtered].slice(0, 20);
      saveHistory(updated);
      return { ...state, recentResults: updated };
    }
    case "REMOVE_RESULT": {
      const updated = state.recentResults.filter((r) => r.id !== action.id);
      saveHistory(updated);
      return { ...state, recentResults: updated };
    }
    case "CLEAR_HISTORY":
      saveHistory([]);
      return { ...state, recentResults: [] };
    case "SET_MODE":
      return { ...state, activeMode: action.mode };
    case "SET_TICKER":
      return { ...state, activeTicker: action.ticker };
    case "SET_LOADING":
      return { ...state, loading: action.loading };
    case "SET_ERROR":
      return { ...state, error: action.error };
    case "RESTORE_STATE":
      return { ...state, ...action.state };
    default:
      return state;
  }
}

interface WorkspaceContextValue {
  state: WorkspaceState;
  dispatch: React.Dispatch<WorkspaceAction>;
  openResearch: (ticker: string, mode?: string) => void;
  openCompare: (tickers: string[], mode?: string) => void;
  openScreening: (mode?: string) => void;
  openWatchlist: () => void;
  setDashboard: () => void;
  setMode: (mode: "BSJP" | "BPJS") => void;
  handleSearch: (query: string) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}

function detectIntent(query: string): "compare" | "screen" | "research" {
  const q = query.toLowerCase();
  if (q.includes("bandingkan") || q.includes("compare") || q.includes("vs")) return "compare";
  if (q.includes("cari") || q.includes("terbaik") || q.includes("screen") || q.includes("rekomendasi")) return "screen";
  return "research";
}

function extractTickers(query: string): string[] {
  return query.match(/\b[A-Z]{2,5}\b/g)?.map((t) => t.toUpperCase()) ?? [];
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();

  const initView = ((): WorkspaceView => {
    const v = searchParams.get("view");
    if (v && ["dashboard", "research", "screening", "compare", "watchlist"].includes(v)) return v as WorkspaceView;
    if (searchParams.get("ticker")) return "research";
    if (searchParams.get("tickers")) return "compare";
    return "dashboard";
  })();

  const initTicker = searchParams.get("ticker");
  const initTickers = searchParams.get("tickers")?.split(",") ?? [];
  const initMode = (searchParams.get("mode") as "BSJP" | "BPJS") ?? "BSJP";

  const [state, dispatch] = useReducer(reducer, {
    view: initView,
    activeTicker: initTicker,
    activeMode: initMode,
    compareTickers: initTickers,
    isChatOpen: false,
    chatInputDraft: "",
    recentResults: loadHistory(),
    loading: false,
    error: null,
  });

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("view", state.view);
    params.set("mode", state.activeMode);
    if (state.activeTicker) params.set("ticker", state.activeTicker);
    if (state.compareTickers.length > 0) params.set("tickers", state.compareTickers.join(","));
    window.history.replaceState({}, "", `?${params.toString()}`);
  }, [state.view, state.activeMode, state.activeTicker, state.compareTickers]);

  useEffect(() => {
    function handlePopState() {
      const params = new URLSearchParams(window.location.search);
      const v = params.get("view") as WorkspaceView | null;
      if (v && v !== state.view) {
        dispatch({ type: "SET_VIEW", view: v, ticker: params.get("ticker"), tickers: params.get("tickers")?.split(",").filter(Boolean) });
      }
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [state.view]);

  const openResearch = useCallback(
    (ticker: string, mode?: string) => {
      dispatch({ type: "SET_VIEW", view: "research", ticker, mode: mode ?? state.activeMode });
    },
    [state.activeMode],
  );

  const openCompare = useCallback(
    (tickers: string[], mode?: string) => {
      dispatch({ type: "SET_VIEW", view: "compare", tickers, mode: mode ?? state.activeMode });
    },
    [state.activeMode],
  );

  const openScreening = useCallback(
    (mode?: string) => {
      dispatch({ type: "SET_VIEW", view: "screening", mode: mode ?? state.activeMode });
    },
    [state.activeMode],
  );

  const openWatchlist = useCallback(() => {
    dispatch({ type: "SET_VIEW", view: "watchlist" });
  }, []);

  const setDashboard = useCallback(() => {
    dispatch({ type: "SET_VIEW", view: "dashboard", ticker: null, tickers: [] });
  }, []);

  const setMode = useCallback((mode: "BSJP" | "BPJS") => {
    dispatch({ type: "SET_MODE", mode });
  }, []);

  const handleSearch = useCallback(
    (query: string) => {
      const intent = detectIntent(query);
      if (intent === "compare") {
        const tickers = extractTickers(query);
        if (tickers.length >= 2) {
          openCompare(tickers);
        } else {
          dispatch({ type: "SET_ERROR", error: "Butuh minimal 2 ticker untuk perbandingan" });
        }
      } else if (intent === "screen") {
        openScreening();
      } else {
        const tickers = extractTickers(query);
        if (tickers.length > 0) {
          openResearch(tickers[0]);
        } else {
          dispatch({ type: "SET_CHAT_INPUT", input: query });
        }
      }
    },
    [openCompare, openScreening, openResearch],
  );

  const value: WorkspaceContextValue = {
    state,
    dispatch,
    openResearch,
    openCompare,
    openScreening,
    openWatchlist,
    setDashboard,
    setMode,
    handleSearch,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export type { WorkspaceContextValue };
