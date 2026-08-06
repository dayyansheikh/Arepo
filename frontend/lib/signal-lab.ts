/**
 * Pure logic for the complete-scan Signal Lab (prompt sections 10, 11).
 *
 * React-free so it is unit-testable in the node vitest runner. The page renders what these decide;
 * trajectory state and completeness come from the server, never inferred here.
 */
import type { ScanSignalRow, ScanStatus, ScanTrajectory } from "@/lib/api";

export type Bucket = "closing_0_6h" | "closing_6_24h" | "closing_1_7d" | "closing_7_30d";
export type Scope = "public" | "directional";

export const BUCKET_OPTIONS: { id: Bucket; label: string }[] = [
  { id: "closing_0_6h", label: "Closing in the next 6 hours" },
  { id: "closing_6_24h", label: "Closing later today" },
  { id: "closing_1_7d", label: "Closing this week" },
  { id: "closing_7_30d", label: "Closing this month" },
];

export const SCOPE_OPTIONS: { id: Scope; label: string }[] = [
  { id: "public", label: "Public top ten" },
  { id: "directional", label: "All directional signals" },
];

/** Trajectory label -> tone + glyph (colour is never the only cue, prompt section 11). */
export function trajectoryTone(label: string): { tone: "up" | "down" | "flat" | "muted"; glyph: string } {
  switch (label) {
    case "Strengthening":
      return { tone: "up", glyph: "▲" };
    case "Weakening":
      return { tone: "down", glyph: "▼" };
    case "Direction reversed":
      return { tone: "down", glyph: "⇄" };
    case "Stable":
      return { tone: "flat", glyph: "▬" };
    case "New signal":
      return { tone: "flat", glyph: "✦" };
    default: // Temporarily unavailable / Stale
      return { tone: "muted", glyph: "·" };
  }
}

/** "Strength 72, up 6 points over the last hour." Strength is stored 0-1; shown as whole points. */
export function strengthPhrase(strength: number, t: ScanTrajectory): string {
  const points = Math.round(strength * 100);
  const change = t.change_1h ?? t.strength_change_prev;
  if (change == null || Math.abs(change) < 0.005) {
    return `Strength ${points}, little changed`;
  }
  const dir = change > 0 ? "up" : "down";
  const pts = Math.abs(Math.round(change * 100));
  const period = t.change_1h != null ? "over the last hour" : "since the previous scan";
  return `Strength ${points}, ${dir} ${pts} point${pts === 1 ? "" : "s"} ${period}`;
}

export function consecutivePhrase(t: ScanTrajectory): string | null {
  if (t.consecutive_same_direction >= 2) {
    return `Direction unchanged for ${t.consecutive_same_direction} consecutive scans`;
  }
  return null;
}

/** The headline that makes clear ten is a display limit, not the analysed count (prompt section 22). */
export function eligibleHeadline(status: ScanStatus): string {
  if (!status.has_scan) return "No complete scan recorded yet.";
  return (
    `${status.raw_discovered ?? 0} markets discovered, ` +
    `${status.eligible_30d ?? 0} eligible within 30 days analysed, ` +
    `${status.directional ?? 0} directional signals found.`
  );
}

export function timeToCloseLabel(hours: number | null): string {
  if (hours == null) return "unknown";
  if (hours < 48) return `${Math.round(hours)}h left`;
  return `${Math.round(hours / 24)}d left`;
}

/** Rows sorted by frozen bucket rank for display (server already ranks; this is a safety sort). */
export function byRank(rows: ScanSignalRow[]): ScanSignalRow[] {
  return [...rows].sort(
    (a, b) => (a.rank_in_bucket ?? 1e9) - (b.rank_in_bucket ?? 1e9),
  );
}
