"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "@/lib/types";
import { formatPercent } from "@/lib/format";

const SERIES_COLORS = ["#E7B24C", "#46C7A8", "#F27289", "#7AA2F7", "#B48EAD", "#9ECE6A"];

interface Props {
  priceHistory: Record<string, PricePoint[]>;
  visibleOutcomes: string[];
}

interface ChartRow {
  t: string;
  ts: number;
  [outcome: string]: number | string;
}

export function PriceHistoryChart({ priceHistory, visibleOutcomes }: Props) {
  const timestamps = new Set<string>();
  for (const name of visibleOutcomes) {
    for (const point of priceHistory[name] ?? []) {
      timestamps.add(point.t);
    }
  }

  const sortedTimestamps = Array.from(timestamps).sort(
    (a, b) => new Date(a).getTime() - new Date(b).getTime()
  );

  const rows: ChartRow[] = sortedTimestamps.map((t) => {
    const row: ChartRow = { t, ts: new Date(t).getTime() };
    for (const name of visibleOutcomes) {
      const points = priceHistory[name] ?? [];
      const match = points.find((p) => p.t === t);
      if (match) row[name] = match.p;
    }
    return row;
  });

  if (rows.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-fg">
        No price history available for the selected outcome(s).
      </div>
    );
  }

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" opacity={0.1} />
          <XAxis
            dataKey="ts"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v: number) => new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            stroke="currentColor"
            opacity={0.6}
            fontSize={11}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v: number) => formatPercent(v, 0)}
            stroke="currentColor"
            opacity={0.6}
            fontSize={11}
            width={44}
          />
          <Tooltip
            formatter={(value: number) => formatPercent(value, 1)}
            labelFormatter={(v: number) => new Date(v).toLocaleString()}
            contentStyle={{
              background: "#151A24",
              border: "1px solid #232C3B",
              borderRadius: 6,
              fontSize: 12,
              fontFamily: "var(--font-mono)",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {visibleOutcomes.map((name, i) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
              strokeWidth={1.75}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
