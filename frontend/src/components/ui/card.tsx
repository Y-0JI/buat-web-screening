import { type ReactNode } from "react";

type CardVariant = "default" | "elevated" | "outlined" | "interactive";
type CardPadding = "none" | "sm" | "md" | "lg";

const variantStyles: Record<CardVariant, string> = {
  default: "bg-zinc-900 border border-zinc-800",
  elevated: "bg-zinc-900 border border-zinc-800 shadow-md",
  outlined: "border border-zinc-800",
  interactive: "bg-zinc-900 border border-zinc-800 hover:bg-zinc-800/60 cursor-pointer transition-colors",
};

const paddingStyles: Record<CardPadding, string> = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

interface CardProps {
  variant?: CardVariant;
  padding?: CardPadding;
  className?: string;
  children: ReactNode;
  onClick?: () => void;
}

export function Card({
  variant = "default",
  padding = "md",
  className = "",
  children,
  onClick,
}: CardProps) {
  const base = "rounded-xl";
  const classes = `${base} ${variantStyles[variant]} ${paddingStyles[padding]} ${className}`;

  if (onClick) {
    return (
      <button
        type="button"
        className={classes}
        onClick={onClick}
      >
        {children}
      </button>
    );
  }

  return (
    <div className={classes}>
      {children}
    </div>
  );
}
