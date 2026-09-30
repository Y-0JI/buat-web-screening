"use client";

import { useEffect, useMemo, useState } from "react";
import { getBrokerSummary, type BrokerSummary } from "@/lib/chat";

function fmtVal(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (a >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return String(Math.round(v));
}

function fmtVol(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return String(Math.round(v));
}

function fmtRp(v: number | null): string {
  return v == null ? "-" : Math.round(v).toLocaleString("id-ID");
}

const INVESTORS = [
  { value: "all", label: "All Investor" },
  { value: "F", label: "Foreign" },
  { value: "D", label: "Domestic" },
];

interface Row {
  code: string | null;
  val: number;
  vol: number;
  avg: number | null;
}

export function BrokerSummaryCard({ initial }: { initial: BrokerSummary }) {
  const [data, setData] = useState<BrokerSummary>(initial);
  const [flow, setFlow] = useState(initial.flow || "all");
  const [net, setNet] = useState(Boolean(initial.net));
  const [startDate, setStartDate] = useState(initial.start_date || "");
  const [endDate, setEndDate] = useState(initial.end_date || "");
  const [loading, setLoading] = useState(false);

  const ticker = data.stock_code || initial.stock_code || "";

  const reload = async (next: {
    flow?: string;
    net?: boolean;
    start?: string;
    end?: string;
  }) => {
    if (!ticker) return;
    setLoading(true);
    try {
      const res = await getBrokerSummary(ticker, {
        flow: next.flow ?? flow,
        net: next.net ?? net,
        start_date: next.start ?? (startDate || undefined),
        end_date: next.end ?? (endDate || undefined),
        limit: 50,
        level_limit: 10,
      });
      if (res) setData(res);
    } catch {
      /* diamkan */
    } finally {
      setLoading(false);
    }
  };

  // Ambil ulang data default (Net, limit besar) saat mount agar net seller lengkap.
  useEffect(() => {
    void reload({ flow: "all", net: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { buyers, sellers, tops } = useMemo(() => {
    const list = data.brokers || [];
    const levels = data.levels || [];

    const buyers: Row[] = net
      ? levels
          .map((l) => ({
            code: l.buy.code,
            val: l.buy.val ?? 0,
            vol: l.buy.vol ?? 0,
            avg: l.buy.avg,
          }))
          .filter((x) => x.code)
      : [...list]
          .sort((a, b) => b.bval - a.bval)
          .slice(0, 10)
          .map((x) => ({ code: x.code, val: x.bval, vol: x.bvol, avg: x.bavg }));

    const sellers: Row[] = net
      ? levels
          .map((l) => ({
            code: l.sell.code,
            val: l.sell.val ?? 0,
            vol: l.sell.vol ?? 0,
            avg: l.sell.avg,
          }))
          .filter((x) => x.code)
      : [...list]
          .sort((a, b) => b.sval - a.sval)
          .slice(0, 10)
          .map((x) => ({ code: x.code, val: x.sval, vol: x.svol, avg: x.savg }));

    const key = net
      ? (x: { nval: number }) => Math.abs(x.nval)
      : (x: { bval: number; sval: number }) => x.bval + x.sval;
    const ranked = [...list].sort((a, b) => key(b) - key(a));
    const tops = [1, 3, 5].map((n) => {
      const chunk = ranked.slice(0, n);
      return {
        n,
        net_value: chunk.reduce((s, x) => s + (x.bval - x.sval), 0),
        net_volume: chunk.reduce((s, x) => s + (x.bvol - x.svol), 0),
      };
    });

    return { buyers, sellers, tops };
  }, [data, net]);

  const s = data.summary;

  return (
    <div className="my-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 text-zinc-200">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-semibold">
          Broker Summary <span className="text-zinc-400">{ticker}</span>
        </div>
        {loading && <span className="text-[11px] text-zinc-500">memuat…</span>}
      </div>

      {/* Kontrol */}
      <div className="flex flex-wrap items-center gap-2 mb-3 text-[11px]">
        <input
          type="date"
          value={startDate}
          onChange={(e) => {
            setStartDate(e.target.value);
            reload({ start: e.target.value });
          }}
          className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200"
        />
        <span className="text-zinc-500">s/d</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => {
            setEndDate(e.target.value);
            reload({ end: e.target.value });
          }}
          className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200"
        />
        <select
          value={flow}
          onChange={(e) => {
            setFlow(e.target.value);
            reload({ flow: e.target.value });
          }}
          className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200"
        >
          {INVESTORS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={net ? "net" : "gross"}
          onChange={(e) => {
            const isNet = e.target.value === "net";
            setNet(isNet);
            reload({ net: isNet });
          }}
          className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200"
        >
          <option value="gross">Gross</option>
          <option value="net">Net</option>
        </select>
      </div>

      {/* Top 1/3/5 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
        {tops.map((t) => (
          <div key={t.n} className="rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-2">
            <div className="text-[11px] text-zinc-500">Top {t.n}</div>
            <div
              className={`text-sm font-semibold ${
                t.net_value >= 0 ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {fmtVal(t.net_value)}
            </div>
            <div className="text-[11px] text-zinc-400">{fmtVol(t.net_volume)} vol</div>
          </div>
        ))}
      </div>

      {/* Agregat */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 text-[11px]">
        <div className="rounded-lg border border-zinc-800 px-3 py-2">
          <div className="text-zinc-500">Broker</div>
          <div>
            <span className="text-emerald-400">{s.buyer_count}</span> /{" "}
            <span className="text-red-400">{s.seller_count}</span>
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 px-3 py-2">
          <div className="text-zinc-500">Net Volume</div>
          <div className={s.net_volume >= 0 ? "text-emerald-400" : "text-red-400"}>
            {fmtVol(s.net_volume)}
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 px-3 py-2">
          <div className="text-zinc-500">Net Value</div>
          <div className={s.net_value >= 0 ? "text-emerald-400" : "text-red-400"}>
            {fmtVal(s.net_value)}
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 px-3 py-2">
          <div className="text-zinc-500">Average (Rp)</div>
          <div>{fmtRp(s.avg_price)}</div>
        </div>
      </div>

      {/* Tabel dua sisi */}
      <div className="grid grid-cols-2 gap-3 text-[11px]">
        <BrokerColumn title="Top Buyer" rows={buyers} tone="buy" />
        <BrokerColumn title="Top Seller" rows={sellers} tone="sell" />
      </div>
    </div>
  );
}

function BrokerColumn({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: Row[];
  tone: "buy" | "sell";
}) {
  return (
    <div>
      <div className="flex justify-between text-zinc-500 mb-1">
        <span>{title}</span>
        <span>val · lot · avg</span>
      </div>
      <div className="space-y-0.5">
        {rows.map((b) => (
          <div key={`${tone}-${b.code}`} className="flex justify-between gap-2">
            <span className={`font-medium ${tone === "buy" ? "text-emerald-400" : "text-red-400"}`}>
              {b.code}
            </span>
            <span className="text-zinc-300 tabular-nums">
              {fmtVal(b.val)} · {fmtVol(b.vol)} · {fmtRp(b.avg)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
