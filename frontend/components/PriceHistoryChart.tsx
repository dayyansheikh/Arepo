"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useId } from "react";
import type { PricePoint } from "@/lib/types";
import { formatPercent } from "@/lib/format";
import { seriesColors, theme } from "@/lib/theme";

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

function formatDay(v: number): string {
  return new Date(v).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

/**
 * Price-history area chart. Primary outcome renders in Arepo red, comparison
 * outcomes in neutral slate then muted supporting hues; gridlines are faint and
 * axes readable. A visually-hidden table gives a non-visual alternative.
 */
export function PriceHistoryChart({ priceHistory, series }: Props) {
  const gradientBase = useId().replace(/[:]/g, "");

  const timestamps = new Set<string>();
  for (const s of series) {
    for (const point of priceHistory[s.key] ?? []) timestamps.add(point.t);
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
      <div className="flex h-64 items-center justify-center text-sm text-arepo-muted">
        No price history available for the selected outcome(s).
      </div>
    );
  }

  const colorFor = (i: number) => seriesColors[i % seriesColors.length];

  return (
    <figure className="m-0">
      {/* Accessible legend, also the visual legend. */}
      <figcaption className="mb-3 flex flex-wrap items-center gap-4">
        {series.map((s, i) => (
          <span key={s.key} className="inline-flex items-center gap-1.5 text-[13px] text-arepo-ink2">
            <span
              aria-hidden="true"
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: colorFor(i) }}
            />
            {s.label}
          </span>
        ))}
      </figcaption>

      <div className="h-72 w-full" role="img" aria-label={`Price history over time for ${series.map((s) => s.label).join(", ")}`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <defs>
              {series.map((s, i) => (
                <linearGradient key={s.key} id={`${gradientBase}-${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colorFor(i)} stopOpacity={0.16} />
                  <stop offset="100%" stopColor={colorFor(i)} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis
              dataKey="ts"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={formatDay}
              stroke={theme.muted}
              tick={{ fontSize: 11, fill: theme.muted }}
              tickLine={false}
              axisLine={{ stroke: theme.border }}
              minTickGap={40}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v: number) => formatPercent(v, 0)}
              stroke={theme.muted}
              tick={{ fontSize: 11, fill: theme.muted }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              formatter={(value: number, name: string) => [formatPercent(value, 1), name]}
              labelFormatter={(v: number) =>
                new Date(v).toLocaleString("en-GB", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              }
              contentStyle={{
                background: theme.surface,
                border: `1px solid ${theme.border}`,
                borderRadius: 10,
                fontSize: 12,
                boxShadow: "0 6px 20px rgba(16,16,16,0.10)",
                color: theme.ink,
              }}
              itemStyle={{ fontVariantNumeric: "tabular-nums" }}
            />
            {series.map((s, i) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={colorFor(i)}
                strokeWidth={2.25}
                fill={`url(#${gradientBase}-${i})`}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Non-visual alternative. */}
      <table className="sr-only">
        <caption>Price history as data</caption>
        <thead>
          <tr>
            <th>Time</th>
            {series.map((s) => (
              <th key={s.key}>{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.ts}>
              <td>{new Date(r.ts).toLocaleString("en-GB")}</td>
              {series.map((s) => (
                <td key={s.key}>{r[s.key] !== undefined ? formatPercent(r[s.key], 1) : "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
