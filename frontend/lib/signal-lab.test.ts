import { describe, it, expect } from "vitest";
import type { ScanStatus, ScanTrajectory } from "@/lib/api";
import {
  BUCKET_OPTIONS,
  SCOPE_OPTIONS,
  consecutivePhrase,
  eligibleHeadline,
  strengthPhrase,
  timeToCloseLabel,
  trajectoryTone,
} from "@/lib/signal-lab";

function traj(p: Partial<ScanTrajectory>): ScanTrajectory {
  return {
    label: "Stable",
    strength_change_prev: null,
    change_1h: null,
    consecutive_same_direction: 1,
    first_detected: null,
    scans: 1,
    ...p,
  };
}

describe("bucket + scope options", () => {
  it("offers the four non-overlapping closing buckets", () => {
    expect(BUCKET_OPTIONS.map((b) => b.id)).toEqual([
      "closing_0_6h",
      "closing_6_24h",
      "closing_1_7d",
      "closing_7_30d",
    ]);
  });
  it("defaults to all directional signals, with the public shortlist as the secondary option", () => {
    expect(SCOPE_OPTIONS.map((s) => s.id)).toEqual(["directional", "public"]);
  });
});

describe("trajectoryTone", () => {
  it("pairs each label with a non-colour glyph", () => {
    for (const l of ["Strengthening", "Weakening", "Direction reversed", "Stable", "New signal"]) {
      expect(trajectoryTone(l).glyph.length).toBeGreaterThan(0);
    }
    expect(trajectoryTone("Strengthening").tone).toBe("up");
    expect(trajectoryTone("Weakening").tone).toBe("down");
  });
});

describe("strengthPhrase", () => {
  it("describes a score change, never a probability", () => {
    const s = strengthPhrase(0.72, traj({ change_1h: 0.06 }));
    expect(s).toBe("Strength 72, up 6 points over the last hour");
    expect(s).not.toMatch(/likely|probability|profit/i);
  });
  it("says little changed when within noise", () => {
    expect(strengthPhrase(0.5, traj({ change_1h: 0.002 }))).toContain("little changed");
  });
  it("falls back to the previous scan when no 1h delta", () => {
    expect(strengthPhrase(0.4, traj({ strength_change_prev: -0.03 }))).toContain(
      "down 3 points since the previous scan",
    );
  });
});

describe("consecutivePhrase", () => {
  it("reports a run of same-direction scans", () => {
    expect(consecutivePhrase(traj({ consecutive_same_direction: 9 }))).toBe(
      "Direction unchanged for 9 consecutive scans",
    );
    expect(consecutivePhrase(traj({ consecutive_same_direction: 1 }))).toBeNull();
  });
});

describe("eligibleHeadline", () => {
  it("makes clear the full universe is analysed, not just ten", () => {
    const st: ScanStatus = {
      has_scan: true,
      raw_discovered: 2100,
      eligible_30d: 181,
      directional: 83,
      total_matching: 0,
    } as unknown as ScanStatus;
    expect(eligibleHeadline(st)).toBe(
      "2100 markets discovered, 181 eligible within 30 days analysed, 83 directional signals found.",
    );
  });
  it("handles the no-scan state", () => {
    expect(eligibleHeadline({ has_scan: false } as ScanStatus)).toContain("No complete scan");
  });
});

describe("timeToCloseLabel", () => {
  it("shows hours then days", () => {
    expect(timeToCloseLabel(5)).toBe("5h left");
    expect(timeToCloseLabel(72)).toBe("3d left");
    expect(timeToCloseLabel(null)).toBe("unknown");
  });
});
