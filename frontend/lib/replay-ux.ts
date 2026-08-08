/**
 * Pure logic for the redesigned, results-first Replay page (FINAL REPLAY UX OVERRIDE).
 *
 * React-free so it is unit-testable in the node vitest runner. It decides the horizon tabs, the
 * closing pills, the scope segments, which cohort to show automatically, and the plain pending copy
 * (with "Expected from HH:MM"), so the page component only renders. No evaluation truth is derived
 * here; the server owns that.
 */
import type { ReplayCohort, ReplayCohortList, ReplayCounts } from "@/lib/api";

// The one-click horizon tabs. "close" = freeze-to-close, "resolved" = final resolution.
export type HorizonTab = "1h" | "6h" | "24h" | "7d" | "close" | "resolved";
export const HORIZON_TABS: { id: HorizonTab; label: string }[] = [
  { id: "1h", label: "1h" },
  { id: "6h", label: "6h" },
  { id: "24h", label: "24h" },
  { id: "7d", label: "7d" },
  { id: "close", label: "To close" },
  { id: "resolved", label: "Resolved" },
];

// Repricing horizons only (the ones with a due time and an available-horizons flag).
export const HORIZON_HOURS: Record<string, number> = { "1h": 1, "6h": 6, "24h": 24, "7d": 168 };

export type ClosingPill = "all" | "6h" | "24h" | "7d" | "30d";
export const CLOSING_PILLS: { id: ClosingPill; label: string }[] = [
  { id: "all", label: "All" },
  { id: "6h", label: "≤6h" },
  { id: "24h", label: "Today" },
  { id: "7d", label: "This week" },
  { id: "30d", label: "This month" },
];

// Simple three-way scope. "research" maps to the directional API scope but reveals the public vs
// shadow comparison panels.
export type ScopeTab = "public" | "directional" | "research";
export const SCOPE_TABS: { id: ScopeTab; label: string }[] = [
  { id: "public", label: "Opportunities" },
  { id: "directional", label: "All signals" },
  { id: "research", label: "Research comparison" },
];

export const SCOPE_HELP: Record<ScopeTab, string> = {
  public: "The public signals Arepo ranked highest.",
  directional: "Every directional signal Arepo recorded.",
  research: "Compares public Opportunities with the directional signals that were not selected.",
};

/** The API scope param for a scope tab (research compares within the full directional set). */
export function apiScope(tab: ScopeTab): "public" | "directional" {
  return tab === "public" ? "public" : "directional";
}

/** The API horizon param for a horizon tab. close/resolved fetch a repricing horizon but render
 * their own panel from the (horizon-independent) freeze-to-close / resolution data. */
export function apiHorizon(tab: HorizonTab): string {
  return tab === "close" || tab === "resolved" ? "6h" : tab;
}

export function isRepricing(tab: HorizonTab): boolean {
  return tab === "1h" || tab === "6h" || tab === "24h" || tab === "7d";
}

function _isoToDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** When a repricing horizon becomes due for a cohort (evaluation origin + horizon hours). */
export function dueAt(cohort: ReplayCohort | undefined, tab: HorizonTab): Date | null {
  if (!cohort || !isRepricing(tab)) return null;
  const origin = _isoToDate(cohort.evaluation_origin_at ?? cohort.frozen_at);
  if (!origin) return null;
  return new Date(origin.getTime() + HORIZON_HOURS[tab] * 3600 * 1000);
}

export type HorizonAvailability = "evaluable" | "due_uncollected" | "not_due" | "no_data";

/** Whether a horizon tab has evaluable results for a cohort, is due but uncollected, or not due. */
export function horizonAvailability(
  cohort: ReplayCohort | undefined,
  tab: HorizonTab,
  now: Date,
): HorizonAvailability {
  if (!cohort) return "no_data";
  if (tab === "resolved") return cohort.resolution_available ? "evaluable" : "not_due";
  if (tab === "close") return "evaluable"; // freeze-to-close is always inspectable (may be pending)
  if (cohort.available_horizons?.[tab]) return "evaluable";
  const due = dueAt(cohort, tab);
  if (due && now >= due) return "due_uncollected";
  return "not_due";
}

function _hhmm(d: Date): string {
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** The concise tooltip for a not-yet-evaluable horizon tab. */
export function horizonTooltip(cohort: ReplayCohort | undefined, tab: HorizonTab): string {
  if (tab === "resolved") return "Available once a market resolves.";
  const due = dueAt(cohort, tab);
  return due ? `Available after ${_hhmm(due)}.` : "Not yet available.";
}

/** Pick the newest real cohort that actually has evaluable results for this horizon; if none, the
 * newest cohort overall (so the page shows a clean pending state, not an empty one). */
export function pickCohortForHorizon(
  list: ReplayCohortList | null | undefined,
  tab: HorizonTab,
  now: Date,
): { cohort: ReplayCohort | undefined; evaluated: boolean } {
  const cohorts = list?.cohorts ?? [];
  if (cohorts.length === 0) return { cohort: undefined, evaluated: false };
  const evaluated = cohorts.find((c) => horizonAvailability(c, tab, now) === "evaluable");
  if (evaluated) return { cohort: evaluated, evaluated: true };
  return { cohort: cohorts[0], evaluated: false };
}

/** "Frozen 6 Aug, 17:02 · 1,382 markets" - the one subtle cohort line. */
export function cohortSummaryLine(cohort: ReplayCohort | undefined): string {
  if (!cohort) return "";
  const frozen = _isoToDate(cohort.frozen_at);
  const when = frozen ? _hhmm(frozen) : "unknown time";
  return `Frozen ${when} · ${cohort.universe_size.toLocaleString("en-GB")} markets`;
}

// Prospective cohorts freeze on fixed 6-hourly UTC boundaries (00/06/12/18). The next boundary after
// `now` is fully deterministic, so we can show when the next research cohort is due without a fetch.
// (Kept in sync with backend research_freeze_cadences="6h".)
export const FREEZE_CADENCE_HOURS = 6;

/** The next 6-hourly UTC freeze boundary strictly after `now`. */
export function nextFreezeAt(now: Date, cadenceHours: number = FREEZE_CADENCE_HOURS): Date {
  const next = new Date(now.getTime());
  next.setUTCMinutes(0, 0, 0);
  const nextHour = (Math.floor(now.getUTCHours() / cadenceHours) + 1) * cadenceHours;
  next.setUTCHours(nextHour); // nextHour === 24 rolls cleanly to 00:00 the following day
  return next;
}

/** "Next freeze ~18:00 UTC" (adds "tomorrow" when it crosses a day boundary). The freeze rides on the
 * next scan, so it lands a few minutes after the boundary — hence the ~. */
export function nextFreezeLine(now: Date, cadenceHours: number = FREEZE_CADENCE_HOURS): string {
  const next = nextFreezeAt(now, cadenceHours);
  const hh = String(next.getUTCHours()).padStart(2, "0");
  const mm = String(next.getUTCMinutes()).padStart(2, "0");
  const sameDay =
    next.getUTCFullYear() === now.getUTCFullYear() &&
    next.getUTCMonth() === now.getUTCMonth() &&
    next.getUTCDate() === now.getUTCDate();
  return `Next freeze ~${hh}:${mm} UTC${sameDay ? "" : " tomorrow"}`;
}

export function resultTitle(tab: HorizonTab): string {
  switch (tab) {
    case "1h":
      return "1-hour performance";
    case "6h":
      return "6-hour performance";
    case "24h":
      return "24-hour performance";
    case "7d":
      return "7-day performance";
    case "close":
      return "Freeze-to-close performance";
    case "resolved":
      return "Final resolution";
  }
}

/** The plain pending state copy (prompt §9): never six zero-cards. */
export function pendingMessage(
  cohort: ReplayCohort | undefined,
  tab: HorizonTab,
  total: number,
): { title: string; detail: string } {
  const due = dueAt(cohort, tab);
  const now = new Date();
  const label = HORIZON_TABS.find((h) => h.id === tab)?.label ?? tab;
  if (due && now < due) {
    return {
      title: `${resultTitle(tab)} is still being collected`,
      detail: `${total} signals pending. Expected from ${_hhmm(due)}.`,
    };
  }
  return {
    title: `${label} results are being collected`,
    detail: `${total} signals pending.`,
  };
}

/** "58% of markets that moved went in Arepo's recorded direction." */
export function hitRateSentence(c: ReplayCounts): string | null {
  if (c.moved <= 0 || c.hit_rate_among_moved == null) return null;
  const pct = Math.round(c.hit_rate_among_moved * 100);
  return `${pct}% of markets that moved went in Arepo's recorded direction.`;
}
