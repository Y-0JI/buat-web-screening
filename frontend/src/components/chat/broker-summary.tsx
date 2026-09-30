"use client";

import { useMemo, useState } from "react";
import { getBrokerSummary, type BrokerRow, type BrokerSummary } from "@/lib/chat";

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
        limit: 20,
      });
      if (res) setData(res);
    } catch {
      /* diamkan */
    } finally {
      setLoading(false);
    }
  };

  const buyers = useMemo(
    () => [...data.brokers].sort((a, b) => b.bval - a.bval).slice(0, 8),
    [data]
  );
  const sellers = useMemo(
    () => [...data.brokers].sort((a, b) => b.sval - a.sval).slice(0, 8),
    [data]
  );

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
        {data.top.map((t) => (
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
        <BrokerColumn title="Top Buyer" rows={buyers} side="buy" />
        <BrokerColumn title="Top Seller" rows={sellers} side="sell" />
      </div>
    </div>
  );
}

function BrokerColumn({
  title,
  rows,
  side,
}: {
  title: string;
  rows: BrokerRow[];
  side: "buy" | "sell";
}) {
  return (
    <div>
      <div className="flex justify-between text-zinc-500 mb-1">
        <span>{title}</span>
        <span>{side === "buy" ? "val · lot · avg" : "val · lot · avg"}</span>
      </div>
      <div className="space-y-0.5">
        {rows.map((b) => {
          const val = side === "buy" ? b.bval : b.sval;
          const vol = side === "buy" ? b.bvol : b.svol;
          const avg = side === "buy" ? b.bavg : b.savg;
          return (
            <div key={`${side}-${b.code}`} className="flex justify-between gap-2">
              <span className={`font-medium ${side === "buy" ? "text-emerald-400" : "text-red-400"}`}>
                {b.code}
              </span>
              <span className="text-zinc-300 tabular-nums">
                {fmtVal(val)} · {fmtVol(vol)} · {fmtRp(avg)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
