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
import { buildChart, type ChartSeriesKey } from "@/lib/chart-data";

export type ChartSeries = ChartSeriesKey;

interface Props {
  /** Price history keyed by token_id (as returned by the API). */
  priceHistory: Record<string, PricePoint[]>;
  series: ChartSeries[];
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

  const { rows, isLimited, maxSeriesLength } = buildChart(priceHistory, series);

  if (rows.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-card border border-dashed border-arepo-border text-[14px] text-arepo-muted">
        No price history is available for the selected outcome(s).
      </div>
    );
  }

  const colorFor = (i: number) => seriesColors[i % seriesColors.length];
  // With few observations a plain stroke can look blank, so show the points.
  const showDots = maxSeriesLength <= 8;

  // If the whole series spans under two days, label the axis by time of day so
  // intraday points don't all read as the same date.
  const spanMs = rows.length > 1 ? rows[rows.length - 1].ts - rows[0].ts : 0;
  const intraday = spanMs > 0 && spanMs < 2 * 24 * 60 * 60 * 1000;
  const formatTick = (v: number): string =>
    intraday
      ? new Date(v).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
      : formatDay(v);

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
              tickFormatter={formatTick}
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
                strokeWidth={2.5}
                fill={`url(#${gradientBase}-${i})`}
                dot={
                  showDots
                    ? { r: 3, fill: colorFor(i), stroke: theme.surface, strokeWidth: 1.5 }
                    : false
                }
                activeDot={{ r: 4.5, fill: colorFor(i), stroke: theme.surface, strokeWidth: 2 }}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {isLimited ? (
        <p className="mt-2 text-[13px] leading-relaxed text-arepo-muted">
          Only limited history is available for this market in the selected view.
        </p>
      ) : null}

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
                <td key={s.key}>{r[s.key] !== undefined ? formatPercent(r[s.key], 1) : "–"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
