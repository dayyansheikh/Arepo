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

export interface ChartSeries {
  /** Key into `priceHistory` — the outcome's token_id. */
  key: string;
  /** Human label shown in the legend (the outcome name). */
  label: string;
}

interface Props {
  /** Price history keyed by token_id (as returned by the API). */
  priceHistory: Record<string, PricePoint[]>;
  series: ChartSeries[];
}

interface ChartRow {
  ts: number;
  [seriesKey: string]: number;
}

export function PriceHistoryChart({ priceHistory, series }: Props) {
  const timestamps = new Set<string>();
  for (const s of series) {
    for (const point of priceHistory[s.key] ?? []) {
      timestamps.add(point.t);
    }
  }

  const sortedTimestamps = Array.from(timestamps).sort(
    (a, b) => new Date(a).getTime() - new Date(b).getTime()
  );

  const rows: ChartRow[] = sortedTimestamps.map((t) => {
    const row: ChartRow = { ts: new Date(t).getTime() };
    for (const s of series) {
      const match = (priceHistory[s.key] ?? []).find((p) => p.t === t);
      if (match) row[s.key] = match.p;
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
            tickFormatter={(v: number) =>
              new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })
            }
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
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
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
