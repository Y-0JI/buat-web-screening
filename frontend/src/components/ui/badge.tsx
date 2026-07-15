import { type ReactNode } from "react";

type BadgeVariant =
  | "verdict-buy"
  | "verdict-hold"
  | "verdict-sell"
  | "verdict-avoid"
  | "mode"
  | "status-live"
  | "status-sim";

type BadgeSize = "sm" | "md";

const variantStyles: Record<BadgeVariant, string> = {
  "verdict-buy":
    "bg-green-500/15 text-green-400 border border-green-500/30",
  "verdict-hold":
    "bg-amber-500/15 text-amber-400 border border-amber-500/30",
  "verdict-sell":
    "bg-red-500/15 text-red-400 border border-red-500/30",
  "verdict-avoid":
    "bg-zinc-500/15 text-zinc-400 border border-zinc-500/30",
  mode: "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  "status-live": "bg-green-500/15 text-green-400",
  "status-sim": "bg-amber-500/15 text-amber-400",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "px-1.5 py-0.5 text-[10px]",
  md: "px-2 py-0.5 text-xs",
};

interface BadgeProps {
  variant: BadgeVariant;
  size?: BadgeSize;
  className?: string;
  children: ReactNode;
}

export function Badge({
  variant,
  size = "md",
  className = "",
  children,
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
}

export function VerdictBadge({
  verdict,
  size = "md",
}: {
  verdict: string;
  size?: BadgeSize;
}) {
  const variantMap: Record<string, BadgeVariant> = {
    BUY: "verdict-buy",
    HOLD: "verdict-hold",
    SELL: "verdict-sell",
    AVOID: "verdict-avoid",
  };
  return (
    <Badge variant={variantMap[verdict] || "verdict-avoid"} size={size}>
      {verdict}
    </Badge>
  );
}
