import { type ReactNode } from "react";

interface StatProps {
  label: string;
  value: string | number;
  delta?: number;
  deltaSuffix?: string;
  icon?: ReactNode;
  className?: string;
}

export function Stat({
  label,
  value,
  delta,
  deltaSuffix = "%",
  icon,
  className = "",
}: StatProps) {
  const deltaColor =
    delta !== undefined
      ? delta > 0
        ? "text-green-400"
        : delta < 0
        ? "text-red-400"
        : "text-zinc-400"
      : "";

  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
          {label}
        </span>
        {icon && <span className="text-zinc-500">{icon}</span>}
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-zinc-100">{value}</span>
        {delta !== undefined && (
          <span className={`text-xs font-medium ${deltaColor} mb-1`}>
            {delta > 0 ? "+" : ""}
            {delta}
            {deltaSuffix}
          </span>
        )}
      </div>
    </div>
  );
}
