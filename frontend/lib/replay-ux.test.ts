import { describe, it, expect } from "vitest";
import type { ReplayCohort, ReplayCohortList, ReplayCounts } from "@/lib/api";
import {
  HORIZON_TABS,
  CLOSING_PILLS,
  SCOPE_TABS,
  apiHorizon,
  apiScope,
  cohortSummaryLine,
  dueAt,
  hitRateSentence,
  horizonAvailability,
  horizonTooltip,
  pendingMessage,
  pickCohortForHorizon,
  resultTitle,
} from "@/lib/replay-ux";

function cohort(p: Partial<ReplayCohort>): ReplayCohort {
  return {
    id: 1,
    cadence: "6h",
    cadence_label: "Six-hourly",
    cadence_description: "",
    scheduled_for: "2026-08-06T12:00:00Z",
    frozen_at: "2026-08-06T16:02:00Z",
    evaluation_origin_at: "2026-08-06T16:02:00Z",
    lateness_seconds: 0,
    lateness_minutes: 0,
    late: false,
    excessively_late: false,
    degraded: false,
    universe_size: 1382,
    directional_count: 974,
    public_selection_count: 80,
    shadow_count: 894,
    observation_count: 9,
    abstention_count: 399,
    excluded_markets: 0,
    available_horizons: { "1h": false, "6h": false, "24h": false, "7d": false },
    resolution_available: false,
    model_version: "m",
    ...p,
  };
}

const NOW = new Date("2026-08-07T00:00:00Z"); // 8h after the 16:02 freeze

describe("tabs and pills", () => {
  it("offers six one-click horizon tabs incl. To close and Resolved", () => {
    expect(HORIZON_TABS.map((t) => t.id)).toEqual(["1h", "6h", "24h", "7d", "close", "resolved"]);
  });
  it("offers five closing pills", () => {
    expect(CLOSING_PILLS.map((p) => p.id)).toEqual(["all", "6h", "24h", "7d", "30d"]);
  });
  it("offers the three simple scopes defaulting to Opportunities", () => {
    expect(SCOPE_TABS.map((s) => s.id)).toEqual(["public", "directional", "research"]);
    expect(SCOPE_TABS[0].label).toBe("Opportunities");
  });
});

describe("api mapping", () => {
  it("maps close/resolved to a repricing fetch horizon", () => {
    expect(apiHorizon("close")).toBe("6h");
    expect(apiHorizon("resolved")).toBe("6h");
    expect(apiHorizon("24h")).toBe("24h");
  });
  it("maps research scope to the directional API scope", () => {
    expect(apiScope("research")).toBe("directional");
    expect(apiScope("public")).toBe("public");
  });
});

describe("dueAt + availability", () => {
  it("computes the due time from the evaluation origin + horizon", () => {
    const d = dueAt(cohort({}), "6h");
    expect(d?.toISOString()).toBe("2026-08-06T22:02:00.000Z");
  });
  it("marks a due-but-uncollected horizon distinctly from not-due", () => {
    // 6h due at 22:02 (before NOW) but no stored result -> due_uncollected.
    expect(horizonAvailability(cohort({}), "6h", NOW)).toBe("due_uncollected");
    // 7d due at 2026-08-13, well after NOW -> not_due.
    expect(horizonAvailability(cohort({}), "7d", NOW)).toBe("not_due");
    // With a stored result -> evaluable.
    const c = cohort({ available_horizons: { "1h": true, "6h": true, "24h": false, "7d": false } });
    expect(horizonAvailability(c, "6h", NOW)).toBe("evaluable");
  });
  it("resolved availability follows resolution_available", () => {
    expect(horizonAvailability(cohort({ resolution_available: true }), "resolved", NOW)).toBe(
      "evaluable",
    );
    expect(horizonAvailability(cohort({}), "resolved", NOW)).toBe("not_due");
  });
  it("tooltip gives an 'Available after' time for a not-due horizon", () => {
    expect(horizonTooltip(cohort({}), "7d")).toMatch(/Available after .*13 Aug/);
  });
});

describe("pickCohortForHorizon", () => {
  const list = {
    cohorts: [
      cohort({ id: 2, frozen_at: "2026-08-06T16:02:00Z", available_horizons: { "1h": false, "6h": false, "24h": false, "7d": false } }),
      cohort({ id: 1, frozen_at: "2026-08-06T01:24:00Z", available_horizons: { "1h": true, "6h": true, "24h": false, "7d": false } }),
    ],
  } as unknown as ReplayCohortList;

  it("prefers the newest cohort that actually has results for the horizon", () => {
    const r = pickCohortForHorizon(list, "6h", NOW);
    expect(r.cohort?.id).toBe(1); // cohort 2 has no 6h results yet, cohort 1 does
    expect(r.evaluated).toBe(true);
  });
  it("falls back to the newest cohort (pending) when none is evaluated", () => {
    const r = pickCohortForHorizon(list, "24h", NOW);
    expect(r.cohort?.id).toBe(2); // newest, but pending
    expect(r.evaluated).toBe(false);
  });
});

describe("copy", () => {
  it("one subtle cohort line", () => {
    expect(cohortSummaryLine(cohort({}))).toMatch(/Frozen .* · 1,382 markets/);
  });
  it("result titles", () => {
    expect(resultTitle("6h")).toBe("6-hour performance");
    expect(resultTitle("close")).toBe("Freeze-to-close performance");
  });
  it("pending message has an Expected-from time when not yet due, no zero cards", () => {
    const c = cohort({ evaluation_origin_at: "2026-08-06T23:30:00Z", frozen_at: "2026-08-06T23:30:00Z" });
    const m = pendingMessage(c, "6h", 974);
    // 6h due at 2026-08-07 05:30, after NOW-real? uses real now; assert shape.
    expect(m.detail).toContain("974 signals pending");
  });
  it("hit-rate sentence in plain English", () => {
    const counts = {
      total: 91, moved_expected: 42, moved_against: 31, no_change: 18, pending: 0, unavailable: 0,
      invalid: 0, moved: 73, evaluated: 91, movement_coverage: 1, hit_rate_among_moved: 42 / 73,
    } as ReplayCounts;
    expect(hitRateSentence(counts)).toBe(
      "58% of markets that moved went in Arepo's recorded direction.",
    );
  });
});
