// Pure helpers for turning API price history into chart-ready rows. Extracted so
// the row-building and the "is this chart effectively blank?" logic can be unit
// tested (see lib/chart-data.test.ts). No React or Recharts imports here.

import type { PricePoint } from "@/lib/types";

export interface ChartSeriesKey {
  /** Key into `priceHistory` — the outcome's token_id. */
  key: string;
  /** Human label shown in the legend (the outcome name). */
  label: string;
}

export interface ChartRow {
  ts: number;
  [seriesKey: string]: number;
}

export interface BuiltChart {
  rows: ChartRow[];
  /** Number of distinct timestamps across all series. */
  timestampCount: number;
  /** Total number of plotted observations across all series. */
  observationCount: number;
  /** Max observations in any single series (drives point visibility). */
  maxSeriesLength: number;
  /**
   * True when there is so little history that a plain line would look blank or
   * broken: no data, a single timestamp (a line needs two points), or every
   * series having at most two observations.
   */
  isLimited: boolean;
}

/**
 * Merge each series' points onto a shared, ascending timestamp axis.
 *
 * Root-cause fixes vs the naive version:
 *  - timestamps are parsed once and sorted numerically (string sort collapsed
 *    ISO offsets inconsistently),
 *  - duplicate timestamps within a series keep the last value rather than being
 *    silently dropped or double-plotted,
 *  - the result reports how sparse it is so the view can show points and a
 *    "limited history" note instead of an apparently empty chart.
 */
export function buildChart(
  priceHistory: Record<string, PricePoint[]>,
  series: ChartSeriesKey[]
): BuiltChart {
  // token_id -> (timestamp ms -> price), last value wins on duplicate timestamps.
  const perSeries = new Map<string, Map<number, number>>();
  const allTs = new Set<number>();
  let observationCount = 0;
  let maxSeriesLength = 0;

  for (const s of series) {
    const byTs = new Map<number, number>();
    for (const point of priceHistory[s.key] ?? []) {
      const ms = new Date(point.t).getTime();
      if (Number.isNaN(ms)) continue; // skip unparseable timestamps rather than NaN-plot
      byTs.set(ms, point.p);
      allTs.add(ms);
    }
    perSeries.set(s.key, byTs);
    observationCount += byTs.size;
    maxSeriesLength = Math.max(maxSeriesLength, byTs.size);
  }

  const sortedTs = Array.from(allTs).sort((a, b) => a - b);
  const rows: ChartRow[] = sortedTs.map((ms) => {
    const row: ChartRow = { ts: ms };
    for (const s of series) {
      const v = perSeries.get(s.key)?.get(ms);
      if (v !== undefined) row[s.key] = v;
    }
    return row;
  });

  return {
    rows,
    timestampCount: sortedTs.length,
    observationCount,
    maxSeriesLength,
    isLimited: sortedTs.length <= 1 || maxSeriesLength <= 2,
  };
}
