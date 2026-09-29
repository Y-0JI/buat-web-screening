"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ModelInfo } from "@/lib/chat";

interface Props {
  models: ModelInfo[];
  value: string;
  onChange: (id: string) => void;
  align?: "up" | "down";
}

function Caps({ model }: { model: ModelInfo }) {
  const tags: string[] = [];
  if (model.capabilities.vision) tags.push("Vision");
  if (model.capabilities.tools) tags.push("Tools");
  return (
    <span className="text-[10px] text-zinc-500">{tags.join(" · ")}</span>
  );
}

export function ModelPicker({ models, value, onChange, align = "up" }: Props) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const combo = useMemo(() => models.filter((m) => m.provider === "combo"), [models]);
  const groups = useMemo(() => {
    const map = new Map<string, { label: string; models: ModelInfo[] }>();
    for (const m of models) {
      if (m.provider === "combo") continue;
      if (!map.has(m.provider)) map.set(m.provider, { label: m.provider_label, models: [] });
      map.get(m.provider)!.models.push(m);
    }
    return [...map.values()];
  }, [models]);

  const current = models.find((m) => m.id === value);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors"
      >
        <span className="max-w-[160px] truncate">{current?.name || value || "Pilih model"}</span>
        <svg className="w-3 h-3 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className={`absolute right-0 z-30 w-72 max-h-80 overflow-y-auto rounded-xl border border-zinc-700 bg-zinc-900 shadow-xl p-2 ${
            align === "up" ? "bottom-full mb-2" : "top-full mt-2"
          }`}
        >
          <div className="px-2 py-1 text-[10px] uppercase tracking-wide text-zinc-500">Combo</div>
          {combo.map((m) => (
            <button
              key={m.id}
              onClick={() => {
                onChange(m.id);
                setOpen(false);
              }}
              className={`w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-zinc-800 ${
                value === m.id ? "bg-zinc-800" : ""
              }`}
            >
              <span className="text-sm text-zinc-100 truncate">{m.name}</span>
              <span className="flex items-center gap-1.5 shrink-0">
                <Caps model={m} />
                {value === m.id && <span className="text-[10px] text-blue-400">Current</span>}
              </span>
            </button>
          ))}

          {!showAll ? (
            <button
              onClick={() => setShowAll(true)}
              className="w-full flex items-center justify-between px-2 py-2 mt-1 rounded-lg text-left text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Lihat semua model
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ) : (
            <>
              {groups.map((g) => (
                <div key={g.label} className="mt-1">
                  <div className="px-2 py-1 text-[10px] uppercase tracking-wide text-zinc-500">
                    {g.label}
                  </div>
                  {g.models.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => {
                        onChange(m.id);
                        setOpen(false);
                      }}
                      className={`w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-zinc-800 ${
                        value === m.id ? "bg-zinc-800" : ""
                      }`}
                    >
                      <span className="text-xs text-zinc-200 truncate">{m.name}</span>
                      <Caps model={m} />
                    </button>
                  ))}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
