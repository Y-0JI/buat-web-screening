"use client";

import type { ReactNode } from "react";

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function inline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>")
    .replace(
      /`(.+?)`/g,
      '<code class="bg-surface-3/70 px-1 py-0.5 rounded text-[0.85em]">$1</code>'
    );
}

export function Markdown({ text }: { text: string }) {
  const lines = (text || "").split("\n");
  const nodes: ReactNode[] = [];
  let list: ReactNode[] = [];

  const flush = () => {
    if (list.length) {
      nodes.push(
        <ul key={`ul-${nodes.length}`} className="list-disc list-inside space-y-1 my-1.5">
          {list}
        </ul>
      );
      list = [];
    }
  };

  lines.forEach((raw, i) => {
    const bullet = raw.match(/^\s*[-*]\s+(.*)$/);
    if (bullet) {
      list.push(
        <li key={i} dangerouslySetInnerHTML={{ __html: inline(bullet[1]) }} />
      );
      return;
    }
    flush();

    if (raw.startsWith("### ")) {
      nodes.push(
        <h4 key={i} className="text-sm font-bold text-text-primary mt-3 mb-1"
          dangerouslySetInnerHTML={{ __html: inline(raw.slice(4)) }} />
      );
    } else if (raw.startsWith("## ")) {
      nodes.push(
        <h3 key={i} className="text-base font-bold text-text-primary mt-3 mb-1"
          dangerouslySetInnerHTML={{ __html: inline(raw.slice(3)) }} />
      );
    } else if (raw.startsWith("# ")) {
      nodes.push(
        <h2 key={i} className="text-lg font-bold text-text-primary mt-3 mb-1"
          dangerouslySetInnerHTML={{ __html: inline(raw.slice(2)) }} />
      );
    } else if (raw.trim() === "") {
      nodes.push(<div key={i} className="h-2" />);
    } else {
      nodes.push(
        <p key={i} className="leading-relaxed"
          dangerouslySetInnerHTML={{ __html: inline(raw) }} />
      );
    }
  });

  flush();
  return <div className="space-y-0.5">{nodes}</div>;
}
