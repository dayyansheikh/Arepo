import { describe, it, expect } from "vitest";
import type { ReplayCounts, ReplayCohortList } from "@/lib/api";
import {
  CLOSING_OPTIONS,
  HORIZON_OPTIONS,
  SCOPE_OPTIONS,
  cadenceCopy,
  cohortById,
  defaultCohortId,
  headlineSentence,
  hitRateAmongMovedText,
  movementCoverageText,
  newestCohortForCadence,
  normaliseReplayParam,
  qualifyingCaption,
  resultLabel,
} from "@/lib/replay";

function counts(p: Partial<ReplayCounts>): ReplayCounts {
  const base: ReplayCounts = {
    total: 0,
    moved_expected: 0,
    moved_against: 0,
    no_change: 0,
    pending: 0,
    unavailable: 0,
    invalid: 0,
    moved: 0,
    evaluated: 0,
    movement_coverage: null,
    hit_rate_among_moved: null,
  };
  const merged = { ...base, ...p };
  merged.moved = merged.moved_expected + merged.moved_against;
  merged.evaluated = merged.moved + merged.no_change;
  merged.movement_coverage = merged.total ? merged.evaluated / merged.total : null;
  merged.hit_rate_among_moved = merged.moved ? merged.moved_expected / merged.moved : null;
  return merged;
}

// The real 6h cohort's combined directional result.
const COMBINED_6H = counts({ total: 19, moved_expected: 4, moved_against: 4, no_change: 11 });

describe("headlineSentence", () => {
  it("leads with the full count and never hides flat markets", () => {
    expect(headlineSentence(COMBINED_6H)).toBe(
      "Of 19 directional calls, 4 moved as expected, 4 moved against the call and 11 did not change.",
    );
  });

  it("appends pending and unavailable when present", () => {
    const c = counts({ total: 19, moved_expected: 0, moved_against: 0, no_change: 0, pending: 19 });
    expect(headlineSentence(c)).toContain("19 pending at this horizon.");
  });

  it("uses the singular noun for a single call", () => {
    const c = counts({ total: 1, moved_expected: 1 });
    expect(headlineSentence(c)).toContain("Of 1 directional call,");
  });
});

describe("hitRateAmongMovedText", () => {
  it("labels the hit rate explicitly as among markets that moved (4 of 8 = 50%)", () => {
    expect(hitRateAmongMovedText(COMBINED_6H)).toBe(
      "Hit rate among markets that moved: 50% (4 of 8)",
    );
  });

  it("returns null when nothing moved, so no rate is shown for an all-flat sample", () => {
    const c = counts({ total: 10, no_change: 10 });
    expect(hitRateAmongMovedText(c)).toBeNull();
  });
});

describe("movementCoverageText", () => {
  it("reports coverage of stored observations, not a hit rate", () => {
    expect(movementCoverageText(COMBINED_6H)).toBe(
      "Movement coverage 100% (19 of 19 have a stored observation at this horizon).",
    );
  });

  it("handles all-pending horizons", () => {
    const c = counts({ total: 19, pending: 19 });
    expect(movementCoverageText(c)).toContain("Movement coverage 0% (0 of 19");
  });
});

describe("resultLabel", () => {
  it("maps each state to an intuitive, colour-independent label + glyph", () => {
    expect(resultLabel("moved_expected")).toMatchObject({ label: "Moved as expected", tone: "good" });
    expect(resultLabel("moved_against")).toMatchObject({ label: "Moved against the call", tone: "bad" });
    expect(resultLabel("no_change")).toMatchObject({ label: "No price change", tone: "flat" });
    expect(resultLabel("pending")).toMatchObject({ label: "Pending", tone: "pending" });
    expect(resultLabel("unavailable")).toMatchObject({ label: "Unavailable" });
    expect(resultLabel("invalid")).toMatchObject({ label: "Invalid" });
    // Every label carries a non-colour glyph.
    for (const s of ["moved_expected", "moved_against", "no_change", "pending"]) {
      expect(resultLabel(s).glyph.length).toBeGreaterThan(0);
    }
  });
});

describe("cadenceCopy", () => {
  it("gives dynamic wording per cadence and never calls a six-hour cohort weekly", () => {
    expect(cadenceCopy("6h")).toContain("six-hourly cohort");
    expect(cadenceCopy("6h")).not.toContain("weekly");
    expect(cadenceCopy("weekly")).toContain("weekly scheduled job");
    expect(cadenceCopy("daily")).toContain("daily cohort");
  });

  it("never claims tracking has not started and measures from the actual freeze time", () => {
    for (const cad of ["6h", "daily", "weekly", "unknown"]) {
      expect(cadenceCopy(cad)).toContain("actual freeze time");
      expect(cadenceCopy(cad)).not.toContain("has not started");
    }
  });
});

describe("qualifyingCaption", () => {
  it("shows the qualifying count rather than padding to ten", () => {
    expect(qualifyingCaption(7, 7, "directional")).toBe("Showing 7 qualifying directional signals.");
    expect(qualifyingCaption(10, 19, "directional")).toBe(
      "Showing the top 10 of 19 qualifying directional signals by frozen rank.",
    );
    expect(qualifyingCaption(0, 0, "public")).toBe("No qualifying public selections in this set.");
  });
});

describe("normaliseReplayParam", () => {
  it("maps every legacy mode to the single prospective view", () => {
    for (const raw of ["reconstructed", "synthetic", "demo", "historical", "prospective", "", null]) {
      expect(normaliseReplayParam(raw)).toBe("prospective");
    }
  });
});

describe("option lists", () => {
  it("offers the four short-term horizons; final resolution is handled separately", () => {
    expect(HORIZON_OPTIONS.map((h) => h.id)).toEqual(["1h", "6h", "24h", "7d"]);
  });

  it("offers the five frozen closing windows with explicit at-freeze labels", () => {
    expect(CLOSING_OPTIONS.map((c) => c.id)).toEqual(["6h", "24h", "7d", "30d", "all"]);
    for (const c of CLOSING_OPTIONS) {
      if (c.id !== "all") expect(c.label).toContain("at the time of the freeze");
    }
  });

  it("defaults scope to all directional signals including shadow", () => {
    expect(SCOPE_OPTIONS[0].id).toBe("directional");
  });
});

describe("cohort selection", () => {
  const list = {
    cohorts: [
      { id: 3, cadence: "6h" },
      { id: 2, cadence: "6h" },
      { id: 1, cadence: "weekly" },
    ],
    default_cohort_id: 3,
    cadences: [],
  } as unknown as ReplayCohortList;

  it("defaults to the newest cohort", () => {
    expect(defaultCohortId(list)).toBe(3);
  });

  it("finds the newest cohort per cadence (newest-first order)", () => {
    expect(newestCohortForCadence(list, "6h")?.id).toBe(3);
    expect(newestCohortForCadence(list, "weekly")?.id).toBe(1);
  });

  it("looks up a cohort by id", () => {
    expect(cohortById(list, 2)?.cadence).toBe("6h");
    expect(cohortById(list, 99)).toBeUndefined();
  });
});
