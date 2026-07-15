interface BarSegment {
  value: number;
  color: string;
  label?: string;
}

interface BarProps {
  variant: "score" | "sentiment" | "progress";
  value?: number;
  segments?: BarSegment[];
  height?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

const heightStyles = {
  sm: "h-1.5",
  md: "h-2.5",
  lg: "h-3.5",
};

function ScoreBar({
  value,
  height,
  showLabel,
  className,
}: {
  value: number;
  height: string;
  showLabel: boolean;
  className: string;
}) {
  return (
    <div className={className}>
      <div className={`w-full bg-zinc-800 rounded-full ${height} overflow-hidden`}>
        <div
          className="h-full rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500 transition-all duration-500"
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-xs text-zinc-400 text-center mt-1">{value}</div>
      )}
    </div>
  );
}

function SentimentBar({
  segments,
  height,
  showLabel,
  className,
}: {
  segments: BarSegment[];
  height: string;
  showLabel: boolean;
  className: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <div className={className}>
      <div className={`w-full bg-zinc-800 rounded-full ${height} overflow-hidden flex`}>
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`${height} ${seg.color} transition-all duration-500`}
            style={{ width: `${total > 0 ? (seg.value / total) * 100 : 0}%` }}
            title={seg.label}
          />
        ))}
      </div>
      {showLabel && (
        <div className="flex gap-2 mt-1">
          {segments.map(
            (seg, i) =>
              seg.label && (
                <span key={i} className="text-[10px] text-zinc-500">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full ${seg.color} mr-0.5`} />
                  {seg.label}
                </span>
              )
          )}
        </div>
      )}
    </div>
  );
}

export function Bar({
  variant,
  value = 0,
  segments = [],
  height = "md",
  showLabel = false,
  className = "",
}: BarProps) {
  const h = heightStyles[height];

  if (variant === "score") {
    return (
      <ScoreBar value={value} height={h} showLabel={showLabel} className={className} />
    );
  }

  if (variant === "sentiment") {
    return (
      <SentimentBar
        segments={segments}
        height={h}
        showLabel={showLabel}
        className={className}
      />
    );
  }

  return (
    <div className={className}>
      <div className={`w-full bg-zinc-800 rounded-full ${h} overflow-hidden`}>
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-500"
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
    </div>
  );
}
