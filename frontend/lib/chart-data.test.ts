import { describe, it, expect } from "vitest";
import { buildChart } from "./chart-data";
import type { PricePoint } from "./types";

const S = [
  { key: "yes", label: "Yes" },
  { key: "no", label: "No" },
];

function pts(...pairs: [string, number][]): PricePoint[] {
  return pairs.map(([t, p]) => ({ t, p }));
}

describe("buildChart", () => {
  it("merges two series onto one ascending timestamp axis", () => {
    const { rows, timestampCount } = buildChart(
      {
        yes: pts(["2026-08-01T00:00:00Z", 0.4], ["2026-08-02T00:00:00Z", 0.6]),
        no: pts(["2026-08-01T00:00:00Z", 0.6], ["2026-08-02T00:00:00Z", 0.4]),
      },
      S
    );
    expect(timestampCount).toBe(2);
    expect(rows).toEqual([
      { ts: Date.parse("2026-08-01T00:00:00Z"), yes: 0.4, no: 0.6 },
      { ts: Date.parse("2026-08-02T00:00:00Z"), yes: 0.6, no: 0.4 },
    ]);
  });

  it("sorts numerically by real time, not by string", () => {
    // Out-of-order + a timestamp whose string sort would misorder it.
    const { rows } = buildChart(
      { yes: pts(["2026-08-10T00:00:00Z", 0.5], ["2026-08-02T00:00:00Z", 0.3]) },
      [S[0]]
    );
    expect(rows.map((r) => r.ts)).toEqual([
      Date.parse("2026-08-02T00:00:00Z"),
      Date.parse("2026-08-10T00:00:00Z"),
    ]);
  });

  it("keeps the last value on a duplicate timestamp instead of dropping the point", () => {
    const { rows, observationCount } = buildChart(
      { yes: pts(["2026-08-01T00:00:00Z", 0.4], ["2026-08-01T00:00:00Z", 0.7]) },
      [S[0]]
    );
    expect(rows).toEqual([{ ts: Date.parse("2026-08-01T00:00:00Z"), yes: 0.7 }]);
    expect(observationCount).toBe(1);
  });

  it("flags a single-timestamp (collapsed) series as limited — the blank-chart bug", () => {
    // This is exactly the Live/Cached failure: every point shares one timestamp.
    const now = "2026-08-03T12:00:00Z";
    const { isLimited, timestampCount } = buildChart(
      { yes: pts([now, 0.4], [now, 0.5], [now, 0.6]) },
      [S[0]]
    );
    expect(timestampCount).toBe(1);
    expect(isLimited).toBe(true);
  });

  it("flags two-or-fewer observations as limited so points/notes show", () => {
    const { isLimited } = buildChart(
      { yes: pts(["2026-08-01T00:00:00Z", 0.4], ["2026-08-02T00:00:00Z", 0.5]) },
      [S[0]]
    );
    expect(isLimited).toBe(true);
  });

  it("does not flag a healthy multi-point series as limited", () => {
    const { isLimited, maxSeriesLength } = buildChart(
      {
        yes: pts(
          ["2026-08-01T00:00:00Z", 0.4],
          ["2026-08-02T00:00:00Z", 0.5],
          ["2026-08-03T00:00:00Z", 0.55],
          ["2026-08-04T00:00:00Z", 0.6]
        ),
      },
      [S[0]]
    );
    expect(maxSeriesLength).toBe(4);
    expect(isLimited).toBe(false);
  });

  it("skips unparseable timestamps rather than emitting NaN rows", () => {
    const { rows } = buildChart(
      { yes: pts(["not-a-date", 0.4], ["2026-08-02T00:00:00Z", 0.5]) },
      [S[0]]
    );
    expect(rows).toEqual([{ ts: Date.parse("2026-08-02T00:00:00Z"), yes: 0.5 }]);
  });

  it("returns no rows for genuinely empty history", () => {
    const { rows, isLimited } = buildChart({}, S);
    expect(rows).toEqual([]);
    expect(isLimited).toBe(true);
  });
});
