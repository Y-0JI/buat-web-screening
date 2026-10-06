"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fmtCompact,
  fmtRp,
} from "@/lib/format";
import {
  getBrokerSummary,
  getNews,
  getOrderFlow,
  type BrokerSummary,
  type NewsItem,
  type OrderFlowData,
} from "@/lib/chat";
import { BrokerSummaryCard } from "../chat/broker-summary";
import type { LiveTrade } from "@/lib/live";
import { NewsCards } from "./news-cards";

const flowCache = new Map<string, OrderFlowData | null>();

function ActionBadge({ action }: { action: string | null }) {
  const buy = action === "BUY";
  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
        buy ? "bg-emerald-500/15 text-emerald-500" : "bg-red-500/15 text-red-500"
      }`}
    >
      {action || "-"}
    </span>
  );
}

function BrokerBadge({ code, kind }: { code: string | null; kind: string | null }) {
  if (!code) return <span className="text-text-muted">-</span>;
  const foreign = kind === "F";
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-text-primary tabular-nums">{code}</span>
      <span
        className={`w-4 h-4 rounded text-[9px] font-bold flex items-center justify-center ${
          foreign ? "bg-amber-500/20 text-amber-500" : "bg-sky-500/20 text-sky-500"
        }`}
      >
        {kind || "·"}
      </span>
    </span>
  );
}

interface Props {
  ticker: string;
  onOpenArticle: (item: NewsItem) => void;
  onOpenNews: () => void;
  liveTrades: LiveTrade[];
  liveConnected: boolean;
  hideBrokers?: boolean;
}

export function OverviewPanel({ ticker, onOpenArticle, onOpenNews, liveTrades, liveConnected, hideBrokers }: Props) {
  const [flow, setFlow] = useState<OrderFlowData | null | undefined>(() =>
    flowCache.has(ticker) ? flowCache.get(ticker) ?? null : undefined
  );
  const rows = useMemo(
    () =>
      (liveTrades.length ? liveTrades : (flow?.rows ?? [])).slice(0, 50),
    [liveTrades, flow]
  );
  const [brokers, setBrokers] = useState<BrokerSummary[] | null>(null);
  const [news, setNews] = useState<NewsItem[] | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (flowCache.has(ticker)) {
      setFlow(flowCache.get(ticker) ?? null);
    } else {
      setFlow(undefined);
    }
    setBrokers(null);
    setNews(undefined);
    setError(null);
    void (async () => {
      try {
        const [of, bq, nq] = await Promise.all([
          getOrderFlow(ticker, { limit: 50 }).catch(() => null),
          getBrokerSummary(ticker, { flow: "all", net: true, limit: 50, level_limit: 10 }).catch(() => null),
          getNews(ticker, { perPage: 9 }).catch(() => ({ items: [] as NewsItem[], hasMore: false, error: null })),
        ]);
        if (cancelled) return;
        flowCache.set(ticker, of);
        setFlow(of);
        setBrokers(bq ? [bq] : []);
        setNews(nq.items);
      } catch {
        if (!cancelled) {
          setError("Gagal memuat data overview.");
          setFlow((prev) => prev ?? null);
          setBrokers([]);
          setNews([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return (
    <div className="mt-2 space-y-3 pb-1">
      <section className="rounded-lg border border-border bg-surface-1 px-3 py-2.5">
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <h4 className="text-xs font-bold text-text-primary mr-auto">
            Done Details{" "}
            {liveConnected && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-500">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                LIVE
              </span>
            )}
          </h4>
          {flow?.date && (
            <span className="text-[11px] text-text-muted">
              Tanggal <span className="text-text-primary">{flow.date}</span>
            </span>
          )}
          {flow?.total != null && (
            <span className="text-[11px] text-text-muted">
              Total Transaksi: <span className="text-text-primary font-semibold">{flow.total.toLocaleString("id-ID")}</span>
            </span>
          )}
        </div>
        {flow === undefined ? (
          <p className="py-4 text-center text-xs text-text-muted">Memuat done details…</p>
        ) : !(flow?.rows?.length) ? (
          <p className="py-4 text-center text-xs text-text-muted">Done details tidak tersedia.</p>
        ) : (
          <div className="max-h-80 overflow-y-auto rounded-lg border border-border/60">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-surface-2">
                <tr className="text-text-muted">
                  <th className="py-1.5 px-2 text-left font-semibold">Time</th>
                  <th className="py-1.5 px-2 text-left font-semibold">Action</th>
                  <th className="py-1.5 px-2 text-right font-semibold">Price</th>
                  <th className="py-1.5 px-2 text-right font-semibold">Lot</th>
                  <th className="py-1.5 px-2 text-right font-semibold">Val</th>
                  <th className="py-1.5 px-2 text-left font-semibold">Buyer</th>
                  <th className="py-1.5 px-2 text-left font-semibold">Seller</th>
                  <th className="py-1.5 px-2 text-left font-semibold">Board</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {rows.map((r, i) => (
                  <tr key={`${r.time}-${i}`}>
                    <td className="py-1.5 px-2 text-text-secondary tabular-nums whitespace-nowrap">{r.time || "-"}</td>
                    <td className="py-1.5 px-2"><ActionBadge action={r.action} /></td>
                    <td className="py-1.5 px-2 text-right text-text-primary tabular-nums">{r.price != null ? fmtRp(r.price) : "-"}</td>
                    <td className="py-1.5 px-2 text-right text-text-primary tabular-nums">{r.lot != null ? fmtCompact(r.lot) : "-"}</td>
                    <td className="py-1.5 px-2 text-right text-text-primary tabular-nums">{r.value != null ? fmtCompact(r.value) : "-"}</td>
                    <td className="py-1.5 px-2"><BrokerBadge code={r.buyer} kind={r.buyer_type} /></td>
                    <td className="py-1.5 px-2"><BrokerBadge code={r.seller} kind={r.seller_type} /></td>
                    <td className="py-1.5 px-2 text-text-secondary">{r.board || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {brokers?.map((b, i) =>
        hideBrokers ? null : (
          <BrokerSummaryCard key={`ov-broker-${b.stock_code}-${i}`} initial={b} />
        )
      )}

      <section className="rounded-lg border border-border bg-surface-1 px-3 py-2.5">
        <button
          type="button"
          onClick={onOpenNews}
          className="flex items-center gap-1 mb-1 text-lg font-bold text-text-primary hover:text-emerald-500 transition-colors"
        >
          News <span aria-hidden>›</span>
        </button>
        {news === undefined ? (
          <p className="py-4 text-center text-xs text-text-muted">Memuat berita…</p>
        ) : !news.length ? (
          <p className="py-4 text-center text-xs text-text-muted">Belum ada berita untuk emiten ini.</p>
        ) : (
          <NewsCards items={news} onOpen={onOpenArticle} columns={3} />
        )}
      </section>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-500 text-xs px-3 py-2">
          {error}
        </div>
      )}
    </div>
  );
}
