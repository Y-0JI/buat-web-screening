"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Customized,
  Cell,
} from "recharts";

interface OHLCVPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PriceChartProps {
  data: OHLCVPoint[];
  isSimulated?: boolean;
}

interface CandlestickProps {
  yAxisMap?: Record<string, { scale: (v: number) => number }>;
  offset?: { left: number; right: number; width: number };
  data?: OHLCVPoint[];
}

function isValidOHLC(d: OHLCVPoint): boolean {
  return [d.open, d.high, d.low, d.close].every(
    (v) => typeof v === "number" && Number.isFinite(v)
  );
}

function CandlestickRenderer({ yAxisMap, offset, data }: CandlestickProps) {
  if (!yAxisMap?.price || !offset || !data || data.length === 0) return null;

  const yScale = yAxisMap.price.scale;
  const chartWidth = offset.width - offset.left - offset.right;
  const bandwidth = chartWidth / data.length;
  const candleWidth = Math.max(bandwidth * 0.7, 4);

  return (
    <g>
      {data.map((d, i) => {
        if (!isValidOHLC(d)) return null;

        const cx = offset.left + i * bandwidth + bandwidth / 2;
        const yHigh = yScale(d.high);
        const yLow = yScale(d.low);
        const yOpen = yScale(d.open);
        const yClose = yScale(d.close);
        const isUp = d.close >= d.open;
        const color = isUp ? "#10b981" : "#ef4444";
        const bodyTop = Math.min(yOpen, yClose);
        const bodyH = Math.max(Math.abs(yOpen - yClose), 1);

        return (
          <g key={i}>
            <line
              x1={cx}
              y1={yHigh}
              x2={cx}
              y2={yLow}
              stroke={color}
              strokeWidth={1.5}
            />
            <rect
              x={cx - candleWidth / 2}
              y={bodyTop}
              width={candleWidth}
              height={bodyH}
              fill={isUp ? "transparent" : color}
              stroke={color}
              strokeWidth={1.5}
              rx={1}
            />
          </g>
        );
      })}
    </g>
  );
}

export function PriceChart({ data, isSimulated = false }: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-[320px] flex items-center justify-center bg-zinc-900 rounded-xl">
        <p className="text-zinc-500">Tidak ada data harga</p>
      </div>
    );
  }

  const validData = data.filter(isValidOHLC);
  const maxVol = Math.max(...validData.map((d) => d.volume));

  return (
    <div className="space-y-2">
      {isSimulated && (
        <div className="text-xs text-amber-400 text-center px-2 py-1 bg-amber-950/30 border border-amber-800/50 rounded">
          Data simulasi — chart tidak merepresentasikan pergerakan real
        </div>
      )}

      <div className="h-[240px] bg-zinc-900 rounded-xl overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={validData}
            margin={{ top: 10, right: 50, bottom: 5, left: 10 }}
          >
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickFormatter={(v: string) => v.slice(5)}
              minTickGap={30}
            />
            <YAxis
              yAxisId="price"
              orientation="right"
              domain={["auto", "auto"]}
              width={60}
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickFormatter={(v: number) => v.toLocaleString()}
              axisLine={false}
              tickLine={false}
            />
            <CartesianGrid
              strokeDasharray="4 4"
              stroke="#27272a"
              vertical={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181b",
                border: "1px solid #27272a",
                borderRadius: "8px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              }}
              labelStyle={{ color: "#71717a", fontSize: 11 }}
              itemStyle={{ color: "#f4f4f5", fontSize: 12 }}
              labelFormatter={(v: string) => v}
            />
            <Customized
              component={(props: Record<string, unknown>) => (
                <CandlestickRenderer
                  {...(props as CandlestickProps)}
                  data={validData}
                />
              )}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="h-[80px] bg-zinc-900 rounded-xl overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={validData}
            margin={{ top: 0, right: 50, bottom: 20, left: 10 }}
          >
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickFormatter={(v: string) => v.slice(5)}
              minTickGap={30}
            />
            <YAxis
              yAxisId="vol"
              orientation="right"
              width={60}
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickFormatter={(v: number) =>
                v >= 1e9
                  ? `${(v / 1e9).toFixed(1)}B`
                  : v >= 1e6
                  ? `${(v / 1e6).toFixed(1)}M`
                  : v >= 1e3
                  ? `${(v / 1e3).toFixed(0)}K`
                  : String(v)
              }
              domain={[0, maxVol * 1.5]}
              axisLine={false}
              tickLine={false}
            />
            <CartesianGrid
              strokeDasharray="4 4"
              stroke="#27272a"
              vertical={false}
            />
            <Bar
              yAxisId="vol"
              dataKey="volume"
              radius={[2, 2, 0, 0]}
              maxBarSize={8}
            >
              {validData.map((entry, idx) => (
                <Cell
                  key={idx}
                  fill={
                    entry.close >= entry.open
                      ? "rgba(16,185,129,0.4)"
                      : "rgba(239,68,68,0.4)"
                  }
                />
              ))}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
