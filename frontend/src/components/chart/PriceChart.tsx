"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
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

export function PriceChart({ data, isSimulated = false }: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-[320px] flex items-center justify-center bg-zinc-900 rounded-xl">
        <p className="text-zinc-500">Tidak ada data harga</p>
      </div>
    );
  }

  const maxVol = Math.max(...data.map((d) => d.volume));

  return (
    <div className="space-y-2">
      {isSimulated && (
        <div className="text-xs text-amber-400 text-center px-2 py-1 bg-amber-950/30 border border-amber-800/50 rounded">
          Data simulasi — chart tidak merepresentasikan pergerakan real
        </div>
      )}

      <div className="h-[240px] bg-zinc-900 rounded-xl overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 50, bottom: 5, left: 10 }}>
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
            <CartesianGrid strokeDasharray="4 4" stroke="#27272a" vertical={false} />
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
              formatter={(value: number, name: string) => [
                name === "close" ? value.toLocaleString() : value,
                name === "close" ? "Close" : name,
              ]}
            />
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="close"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#3b82f6", stroke: "#1e40af" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="h-[80px] bg-zinc-900 rounded-xl overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 50, bottom: 20, left: 10 }}>
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
            <CartesianGrid strokeDasharray="4 4" stroke="#27272a" vertical={false} />
            <Bar
              yAxisId="vol"
              dataKey="volume"
              radius={[2, 2, 0, 0]}
              maxBarSize={8}
            >
              {data.map((entry, idx) => (
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
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
