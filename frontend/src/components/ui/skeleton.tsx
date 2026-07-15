interface SkeletonProps {
  variant: "text" | "heading" | "card" | "row" | "avatar" | "chart";
  width?: string | number;
  height?: string | number;
  className?: string;
}

export function Skeleton({
  variant,
  width,
  height,
  className = "",
}: SkeletonProps) {
  const base = "animate-pulse bg-zinc-800 rounded";

  const variantStyles: Record<string, string> = {
    text: "h-4 rounded",
    heading: "h-6 rounded",
    card: "rounded-xl",
    row: "h-14 rounded-xl",
    avatar: "rounded-full",
    chart: "rounded-xl",
  };

  const defaultSizes: Record<string, { w: string; h: string }> = {
    text: { w: "w-full", h: "h-4" },
    heading: { w: "w-48", h: "h-6" },
    card: { w: "w-full", h: "h-32" },
    row: { w: "w-full", h: "h-14" },
    avatar: { w: "w-10", h: "h-10" },
    chart: { w: "w-full", h: "h-64" },
  };

  const defaults = defaultSizes[variant];

  const w =
    typeof width === "number"
      ? `w-[${width}px]`
      : width || defaults.w;
  const h =
    typeof height === "number"
      ? `h-[${height}px]`
      : height || defaults.h;

  return (
    <div
      className={`${base} ${variantStyles[variant]} ${w} ${h} ${className}`}
    />
  );
}
