/**
 * Pure logic for the prospective Replay product (refinement prompt sections 1-11).
 *
 * Kept free of React so it is unit-testable in the node vitest runner, mirroring the other pure
 * lib modules (signal-arrange, url-state). The page component renders what these functions decide;
 * no important result state is derived from loose client assumptions (the server owns the truth,
 * prompt section 11), so these helpers only format and select, never re-classify a market.
 */
import type { ReplayCohort, ReplayCohortList, ReplayCounts } from "@/lib/api";

export type ClosingFilter = "6h" | "24h" | "7d" | "30d" | "all";
export type Horizon = "1h" | "6h" | "24h" | "7d";
export type Scope = "public" | "directional";

/** Closing-window options, filtered on the FROZEN time-to-close (never the current time-to-close).
 * Labels are explicit that the window is measured "at the time of the freeze" and never imply that
 * closing sooner means a stronger signal (prompt section 4). */
export const CLOSING_OPTIONS: { id: ClosingFilter; label: string }[] = [
  { id: "6h", label: "Closing within 6 hours at the time of the freeze" },
  { id: "24h", label: "Closing within 24 hours at the time of the freeze" },
  { id: "7d", label: "Closing within 7 days at the time of the freeze" },
  { id: "30d", label: "Closing within 30 days at the time of the freeze" },
  { id: "all", label: "All closing times" },
];

/** Evaluation horizons (prompt section 3). Short-term repricing horizons plus final resolution,
 * which is handled separately and never conflated with a short-term move. */
export const HORIZON_OPTIONS: { id: Horizon; label: string }[] = [
  { id: "1h", label: "1 hour" },
  { id: "6h", label: "6 hours" },
  { id: "24h", label: "24 hours" },
  { id: "7d", label: "7 days" },
];

export const SCOPE_OPTIONS: { id: Scope; label: string }[] = [
  { id: "directional", label: "Top directional signals, including shadow signals" },
  { id: "public", label: "Top public selections" },
];

export interface ResultLabel {
  label: string;
  tone: "good" | "bad" | "flat" | "pending";
  /** A short glyph paired with the label so colour is never the only cue (prompt section 7). */
  glyph: string;
}

/** Map a server-computed result state to an intuitive, colour-independent label (prompt section 7). */
export function resultLabel(state: string): ResultLabel {
  switch (state) {
    case "moved_expected":
      return { label: "Moved as expected", tone: "good", glyph: "↑" };
    case "moved_against":
      return { label: "Moved against the call", tone: "bad", glyph: "↓" };
    case "no_change":
      return { label: "No price change", tone: "flat", glyph: "→" };
    case "unavailable":
      return { label: "Unavailable", tone: "pending", glyph: "–" };
    case "closed_before_horizon":
      return { label: "Closed before horizon", tone: "pending", glyph: "×" };
    case "invalid":
      return { label: "Invalid", tone: "pending", glyph: "–" };
    case "pending":
    default:
      return { label: "Pending", tone: "pending", glyph: "·" };
  }
}

/** Dynamic prospective-cohort copy for the selected cadence (prompt section 9). The exact wording
 * follows the real cadence, so a manually created six-hour cohort is never called weekly. */
export function cadenceCopy(cadence: string | null | undefined): string {
  const map: Record<string, string> = {
    "6h":
      "This is a six-hourly cohort: real signals permanently recorded at a six-hourly cut-off. " +
      "Outcomes are measured from the actual freeze time.",
    daily:
      "This is a daily cohort: real signals permanently recorded at a daily cut-off. Outcomes are " +
      "measured from the actual freeze time.",
    weekly:
      "This is a weekly cohort, frozen by the weekly scheduled job: real signals permanently " +
      "recorded at the weekly cut-off. Outcomes are measured from the actual freeze time.",
  };
  return (
    map[cadence ?? ""] ??
    "Prospective cohorts contain real signals permanently recorded at a six-hourly, daily or " +
      "weekly cut-off. Outcomes are measured from the actual freeze time."
  );
}

/** The concise "did the market move as expected?" sentence (prompt section 6). Leads with the full
 * count and never with a hit rate that would hide the flat markets. */
export function headlineSentence(c: ReplayCounts): string {
  const noun = c.total === 1 ? "directional call" : "directional calls";
  const parts = [
    `${c.moved_expected} moved as expected`,
    `${c.moved_against} moved against the call`,
    `${c.no_change} did not change`,
  ];
  let sentence = `Of ${c.total} ${noun}, ${parts[0]}, ${parts[1]} and ${parts[2]}.`;
  const tail: string[] = [];
  if (c.pending > 0) tail.push(`${c.pending} pending`);
  if (c.unavailable > 0) tail.push(`${c.unavailable} unavailable`);
  if (c.closed_before_horizon > 0) {
    tail.push(`${c.closed_before_horizon} closed before the horizon`);
  }
  if (tail.length) sentence += ` ${tail.join(" and ")} at this horizon.`;
  return sentence;
}

/** Explicit label for the hit rate among ONLY the markets that moved (prompt section 6). Returns
 * null when nothing moved, so a hit rate is never shown for an all-flat sample. */
export function hitRateAmongMovedText(c: ReplayCounts): string | null {
  if (c.moved <= 0 || c.hit_rate_among_moved == null) return null;
  const pct = Math.round(c.hit_rate_among_moved * 100);
  return `Hit rate among markets that moved: ${pct}% (${c.moved_expected} of ${c.moved})`;
}

export function movementCoverageText(c: ReplayCounts): string {
  if (c.total <= 0) return "No directional calls in this set.";
  const pct = c.movement_coverage == null ? 0 : Math.round(c.movement_coverage * 100);
  return `Movement coverage ${pct}% (${c.evaluated} of ${c.total} have a stored observation at this horizon).`;
}

/** "Showing 7 qualifying directional signals" style caption (prompt section 5). */
export function qualifyingCaption(shown: number, qualifying: number, scope: Scope): string {
  const noun = scope === "public" ? "public selections" : "directional signals";
  if (qualifying === 0) return `No qualifying ${noun} in this set.`;
  if (shown < qualifying) {
    return `Showing the top ${shown} of ${qualifying} qualifying ${noun} by frozen rank.`;
  }
  return `Showing ${qualifying} qualifying ${noun}.`;
}

/**
 * Normalise a legacy `replay` query value. The public product is prospective-only now, so every
 * removed mode (reconstructed, synthetic, historical, demo, prospective) maps to the single
 * prospective view rather than displaying a removed mode (prompt section 1).
 */
export function normaliseReplayParam(_raw: string | null | undefined): "prospective" {
  return "prospective";
}

/** The default cohort is the newest real prospective cohort (prompt section 2). */
export function defaultCohortId(list: ReplayCohortList | null | undefined): number | null {
  return list?.default_cohort_id ?? null;
}

/** Distinct cadences that actually have real cohorts, newest-cohort id each (prompt section 2). */
export function availableCadences(list: ReplayCohortList | null | undefined) {
  return list?.cadences ?? [];
}

export function cohortById(
  list: ReplayCohortList | null | undefined,
  id: number | null,
): ReplayCohort | undefined {
  if (id == null) return undefined;
  return list?.cohorts.find((c) => c.id === id);
}

/** Newest cohort for a cadence (cohorts arrive newest-first from the API). */
export function newestCohortForCadence(
  list: ReplayCohortList | null | undefined,
  cadence: string,
): ReplayCohort | undefined {
  return list?.cohorts.find((c) => c.cadence === cadence);
}

/** Human freeze-timing summary (prompt section 10). Plain language; lateness stated once, not
 * overemphasised. Times are formatted by the caller; this returns the structured pieces. */
export function latenessPhrase(minutes: number, late: boolean): string {
  if (!late || minutes <= 0) return "on time";
  const m = Math.round(minutes);
  return `${m} minute${m === 1 ? "" : "s"} late`;
}
