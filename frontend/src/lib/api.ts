import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 45000,
});

export interface StockReport {
  render: string;
  ticker: string;
  company_name?: string;
  price?: number;
  change_percent?: number;
  score: number;
  verdict: "BUY" | "HOLD" | "SELL" | "AVOID";
  confidence: number;
  summary: string;
  ai_available?: boolean;
  mode?: string;
  is_simulated?: boolean;
  indicators: {
    ema: Record<string, number>;
    rsi?: number;
    macd?: { macd: number; signal: number; histogram: number };
    atr?: number;
    vwap?: number;
    volume_ratio?: number;
    gap_percent?: number;
    support_resistance?: { resistance: number; support: number; pivot: number };
  };
  score_breakdown: Array<{
    funnel_layer: string;
    score: number;
    weight: number;
    note: string;
  }>;
  stop_loss?: number;
  risk_percent?: number;
  fundamentals?: Fundamentals | null;
  disclaimer: string;
}

export interface Fundamentals {
  market_cap?: number | null;
  enterprise_value?: number | null;
  pe?: number | null;
  forward_pe?: number | null;
  pbv?: number | null;
  pb?: number | null;
  peg?: number | null;
  eps?: number | null;
  roe?: number | null;
  roa?: number | null;
  revenue?: number | null;
  revenue_growth?: number | null;
  net_income?: number | null;
  gross_margin?: number | null;
  operating_margin?: number | null;
  debt_to_equity?: number | null;
  current_ratio?: number | null;
  free_cash_flow?: number | null;
  dividend_yield?: number | null;
  dividend_payout_ratio?: number | null;
  week_52_high?: number | null;
  week_52_low?: number | null;
  average_volume?: number | null;
  shares_outstanding?: number | null;
  source?: string;
  error?: string;
  [key: string]: number | string | null | undefined;
}

export interface ResearchResponse {
  success: boolean;
  data?: StockReport;
  error?: string;
}

export interface ComparisonResponse {
  success: boolean;
  data?: StockReport[];
  error?: string;
}

export interface RankingItem {
  rank: number;
  ticker: string;
  company_name?: string;
  score: number;
  verdict: "BUY" | "HOLD" | "SELL" | "AVOID";
  confidence: number;
  summary: string;
  price?: number;
  change_percent?: number;
  is_simulated?: boolean;
}

export interface ScreeningResponse {
  success: boolean;
  data?: RankingItem[];
  error?: string;
  generated_at?: string;
}

export interface VisionReport {
  render: "vision-analysis";
  file_name: string;
  analysis_text: string;
  patterns_detected: string[];
  trend?: string;
  support_level?: number;
  resistance_level?: number;
  disclaimer: string;
}

export interface VisionAnalysisResponse {
  success: boolean;
  data?: VisionReport;
  error?: string;
}

export type AppResult =
  | { type: "stock-report"; data: StockReport }
  | { type: "comparison"; data: StockReport[] }
  | { type: "ranking"; data: RankingItem[] }
  | { type: "vision-analysis"; data: VisionReport };

export async function researchStock(
  query: string,
  ticker?: string,
  mode?: string
): Promise<ResearchResponse> {
  const res = await api.post<ResearchResponse>("/api/research", {
    query,
    ticker,
    mode,
  });
  return res.data;
}

export async function compareStocks(
  tickers: string[],
  mode?: string
): Promise<ComparisonResponse> {
  const res = await api.post<ComparisonResponse>("/api/compare", {
    tickers,
    mode,
  });
  return res.data;
}

export async function screenStocks(
  mode?: string
): Promise<ScreeningResponse> {
  const res = await api.get<ScreeningResponse>("/api/screen", {
    params: mode ? { mode } : undefined,
  });
  return res.data;
}

export async function analyzeVision(
  file: File
): Promise<VisionAnalysisResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post<VisionAnalysisResponse>(
    "/api/vision-analysis",
    form
  );
  return res.data;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface WatchlistItem {
  id: number;
  ticker: string;
  note?: string;
  added_at: string;
}

export interface WatchlistResult {
  success: boolean;
  data?: WatchlistItem[];
  error?: string;
}

export interface HistoryItem {
  id: number;
  ticker: string;
  score?: number;
  verdict?: string;
  created_at: string;
}

export interface HistoryResult {
  success: boolean;
  data?: HistoryItem[];
  error?: string;
}

export function setToken(token: string | null) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
}

export async function authRegister(
  username: string,
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/api/auth/register", {
    username,
    email,
    password,
  });
  return res.data;
}

export async function authLogin(
  username: string,
  password: string
): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/api/auth/login", {
    username,
    password,
  });
  return res.data;
}

export interface ForgotPasswordResponse {
  detail: string;
}

// Endpoint backend /api/auth/forgot-password sudah tersedia dan mengembalikan
// { detail: string } — alur reset password tersambung langsung ke backend.
export async function authForgotPassword(
  email: string
): Promise<ForgotPasswordResponse> {
  try {
    const res = await api.post<ForgotPasswordResponse>(
      "/api/auth/forgot-password",
      { email }
    );
    return res.data;
  } catch (err) {
    if (err && typeof err === "object" && "response" in err) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      if (detail) throw new Error(detail);
    }
    throw new Error("Gagal mengirim permintaan. Coba lagi nanti.");
  }
}

export interface ResetPasswordResponse {
  detail: string;
}

export async function authResetPassword(
  token: string,
  password: string
): Promise<ResetPasswordResponse> {
  try {
    const res = await api.post<ResetPasswordResponse>(
      "/api/auth/reset-password",
      { token, password }
    );
    return res.data;
  } catch (err) {
    if (err && typeof err === "object" && "response" in err) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      if (detail) throw new Error(detail);
    }
    throw new Error("Gagal mereset password. Coba lagi nanti.");
  }
}

export async function fetchWatchlist(): Promise<WatchlistResult> {
  const res = await api.get<WatchlistResult>("/api/watchlist");
  return res.data;
}

export async function addWatchlist(
  ticker: string,
  note?: string
): Promise<WatchlistResult> {
  const res = await api.post<WatchlistResult>("/api/watchlist", {
    ticker,
    note,
  });
  return res.data;
}

export async function removeWatchlist(
  ticker: string
): Promise<WatchlistResult> {
  const res = await api.delete<WatchlistResult>(`/api/watchlist/${ticker}`);
  return res.data;
}

export async function fetchHistory(
  limit?: number
): Promise<HistoryResult> {
  const res = await api.get<HistoryResult>("/api/history", {
    params: { limit },
  });
  return res.data;
}

export interface OHLCVPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceHistoryResponse {
  success: boolean;
  ticker: string;
  period: string;
  is_simulated: boolean;
  data: OHLCVPoint[];
  error?: string;
}

export async function fetchStockHistory(
  ticker: string,
  period: string = "6mo"
): Promise<PriceHistoryResponse> {
  const res = await api.get<PriceHistoryResponse>(
    `/api/stock/${ticker}/history`,
    { params: { period } }
  );
  return res.data;
}

export interface NewsItem {
  headline: string;
  publisher: string;
  published_date: string;
  summary?: string;
  url: string;
  related_ticker: string;
  source: string;
}

export interface StockNewsResponse {
  success: boolean;
  ticker: string;
  data?: NewsItem[];
  fetched_at?: string;
  error?: string;
}

export async function fetchStockNews(
  ticker: string,
  limit: number = 5
): Promise<StockNewsResponse> {
  const res = await api.get<StockNewsResponse>(`/api/stock/${ticker}/news`, {
    params: { limit },
  });
  return res.data;
}

export interface CompanyProfile {
  name?: string;
  symbol?: string;
  exchange?: string;
  country?: string;
  sector?: string;
  sub_sector?: string;
  industry?: string;
  website?: string;
  business_summary?: string;
  listing_date?: string;
  market_segment?: string;
  address?: string;
  phone?: string;
  email?: string;
  status?: string;
  market_cap?: number;
  shares_outstanding?: number;
  employees?: number | null;
  logo?: string | null;
  source?: string;
}

export interface CompanyProfileResponse {
  success: boolean;
  ticker: string;
  data?: CompanyProfile;
  error?: string;
}

export async function fetchCompanyProfile(
  ticker: string
): Promise<CompanyProfileResponse> {
  const res = await api.get<CompanyProfileResponse>(
    `/api/stock/${ticker}/profile`
  );
  return res.data;
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  mode?: string;
}

export interface ChatResponse {
  success: boolean;
  reply?: string;
  error?: string;
}

export interface ChatContext {
  view: string;
  ticker?: string;
  tickers?: string[];
  mode: string;
}

export async function sendChatMessage(
  messages: ChatMessage[],
  mode?: string,
  context?: ChatContext
): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/api/chat", { messages, mode, context });
  return res.data;
}

export interface ResolveTickersResponse {
  tickers: string[];
}

export async function resolveTickers(
  text: string
): Promise<ResolveTickersResponse> {
  const res = await api.post<ResolveTickersResponse>("/api/resolve-tickers", { text });
  return res.data;
}
