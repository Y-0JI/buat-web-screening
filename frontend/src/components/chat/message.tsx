"use client";

import { useState } from "react";
import { Markdown } from "./markdown";
import { PriceChart } from "./chart";
import { BrokerSummaryCard } from "./broker-summary";
import { FundamentalsCard } from "./fundamentals";
import { AccumulationCard } from "./accumulation";
import type { UIMessage } from "./types";

function ToolChips({ tools }: { tools: NonNullable<UIMessage["tools"]> }) {
  if (!tools.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      {tools.map((t, i) => (
        <span
          key={`${t.name}-${i}`}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] border ${
            t.running
              ? "border-blue-500/30 bg-blue-500/10 text-blue-500"
              : t.ok === false
                ? "border-red-500/30 bg-red-500/10 text-red-500"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
          }`}
        >
          {t.running ? (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          ) : (
            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
          {t.name}
        </span>
      ))}
    </div>
  );
}

function Reasoning({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-[11px] text-text-muted hover:text-text-secondary transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Berpikir…
      </button>
      {open && (
        <pre className="mt-1.5 max-h-48 overflow-y-auto whitespace-pre-wrap text-[11px] leading-relaxed text-text-muted bg-surface-1/60 border border-border rounded-lg p-2.5">
          {text}
        </pre>
      )}
    </div>
  );
}

export function Message({ msg }: { msg: UIMessage }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-md bg-blue-600 text-white text-sm leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] px-4 py-3 rounded-2xl rounded-bl-md bg-surface-2/80 text-text-primary text-sm">
        {msg.charts?.map((c, i) => (
          <PriceChart key={`${c.ticker}-${i}`} chart={c} />
        ))}
        {msg.brokers?.map((b, i) => (
          <BrokerSummaryCard key={`broker-${b.stock_code}-${i}`} initial={b} />
        ))}
        {msg.fundamentals?.map((f, i) => (
          <FundamentalsCard key={`fund-${f.ticker}-${i}`} data={f} />
        ))}
        {msg.accumulations?.map((a, i) => (
          <AccumulationCard key={`acc-${a.scan_date}-${i}`} data={a} />
        ))}
        {msg.reasoning ? <Reasoning text={msg.reasoning} /> : null}
        {msg.tools ? <ToolChips tools={msg.tools} /> : null}
        {msg.content ? (
          <Markdown text={msg.content} />
        ) : msg.streaming ? (
          <div className="flex gap-1 py-1">
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-bounce" />
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-bounce [animation-delay:0.15s]" />
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-bounce [animation-delay:0.3s]" />
          </div>
        ) : null}
      </div>
    </div>
  );
}
