// Pure presentation logic for the Lab dashboard. No React, no fetch: everything here is unit
// tested (lib/lab/model.test.ts). Research-integrity rules from docs/lab/LAB_DASHBOARD_SPEC.md
// are enforced here, not left to individual components:
//   - "how close to an edge" is the funnel stage reached, never a probability or profit;
//   - live prospective tests never expose an interim effect (hideEffect);
//   - not_detected / not_testable / failed_costs keep distinct labels and tones.

import {
  STAGES,
  type CommandTarget,
  type Experiment,
  type FunnelStage,
  type HostPayload,
  type LabCommand,
  type SnapshotEnvelope,
  type Stage,
} from "./types";

export const STAGE_META: Record<Stage, { label: string; help: string }> = {
  idea: { label: "Ideas", help: "Every hypothesis written down." },
  designed: { label: "Designed", help: "Turned into a pre-registered test with a stated minimum effect." },
  screened: { label: "Screened", help: "Run once on historical data." },
  replicated: { label: "Replicated", help: "Held up again on data it had never seen." },
  live_test: { label: "Live test", help: "Collecting fresh predictions forward in time, analysed only on a fixed date." },
  cost_check: { label: "Cost check", help: "Real, but is it still there after trading costs?" },
  confirmed: { label: "Confirmed", help: "Passed every gate, including costs, prospectively." },
};

export function stageIndex(stage: string | null | undefined): number {
  return stage ? (STAGES as readonly string[]).indexOf(stage) : -1;
}

export function isStage(stage: string | null | undefined): stage is Stage {
  return stageIndex(stage) >= 0;
}

/** Snapshot payloads are stored as JSON text server-side; accept an object or a JSON string. */
export function parsePayload<P>(env: SnapshotEnvelope<P> | null | undefined): P | null {
  const raw = env?.payload;
  if (raw == null) return null;
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw) as unknown;
      return parsed && typeof parsed === "object" ? (parsed as P) : null;
    } catch {
      return null;
    }
  }
  return typeof raw === "object" ? raw : null;
}

// ---------------------------------------------------------------------------------------------
// Edge pipeline

export interface PipelineStage {
  stage: Stage;
  label: string;
  help: string;
  /** null when the snapshot did not report this stage: shown as "–", never invented. */
  count: number | null;
  unit: string | null;
  candidates: Experiment[];
}

/** Candidates (experiment.candidate === true) grouped by the stage they have reached. */
export function placeCandidates(experiments: Experiment[] | undefined): Record<Stage, Experiment[]> {
  const out = Object.fromEntries(STAGES.map((s) => [s, [] as Experiment[]])) as Record<
    Stage,
    Experiment[]
  >;
  for (const exp of experiments ?? []) {
    if (!exp || exp.candidate !== true || !isStage(exp.stage)) continue;
    out[exp.stage].push(exp);
  }
  return out;
}

export function buildPipeline(host: HostPayload | null): PipelineStage[] {
  const byStage = new Map<string, FunnelStage>();
  for (const f of host?.funnel ?? []) if (f && typeof f.stage === "string") byStage.set(f.stage, f);
  const placed = placeCandidates(host?.experiments);
  return STAGES.map((stage) => {
    const f = byStage.get(stage);
    let count = typeof f?.count === "number" ? f.count : null;
    // The headline confirmed-edge count is authoritative for the last stage.
    if (stage === "confirmed" && typeof host?.headline?.confirmed_edges === "number") {
      count = host.headline.confirmed_edges;
    }
    return {
      stage,
      label: f?.label || STAGE_META[stage].label,
      help: f?.help || STAGE_META[stage].help,
      count,
      unit: f?.unit || null,
      candidates: placed[stage],
    };
  });
}

// ---------------------------------------------------------------------------------------------
// Verdicts and effects

export type Tone = "pos" | "warn" | "neg" | "neutral" | "accent" | "muted";

export const VERDICT_META: Record<string, { label: string; tone: Tone; help: string }> = {
  not_detected: {
    label: "Not detected",
    tone: "muted",
    help: "Tested properly; any effect is smaller than the test could detect.",
  },
  not_testable: {
    label: "Not testable",
    tone: "neutral",
    help: "Could not be tested: not enough data or the event is too rare.",
  },
  failed_costs: {
    label: "Fails costs",
    tone: "warn",
    help: "The effect is real but smaller than realistic trading costs.",
  },
  replicated: { label: "Replicated", tone: "pos", help: "Held up on data it had not seen." },
  advanced: { label: "Advanced", tone: "accent", help: "Moved on to the next stage." },
  pending: { label: "Pending", tone: "neutral", help: "No verdict yet." },
};

export function verdictMeta(verdict: string | null | undefined) {
  if (!verdict) return { label: "No verdict yet", tone: "neutral" as Tone, help: "Not analysed yet." };
  return (
    VERDICT_META[verdict] ?? { label: verdict.replace(/_/g, " "), tone: "neutral" as Tone, help: "" }
  );
}

export type TrailMark = "pass" | "fail" | "pending" | "none";

/**
 * Per-stage pass/fail trail for one experiment. Uses `stage_results` and `reached` when the
 * snapshot carries them; otherwise infers passes up to the current stage, which is "pending"
 * unless the verdict says it failed there. Stages are not a strict funnel, so this never claims
 * a pass that the data does not imply.
 */
export function stageTrail(exp: Experiment): Array<{ stage: Stage; mark: TrailMark }> {
  const results = exp.stage_results && typeof exp.stage_results === "object" ? exp.stage_results : null;
  const reached = new Set(Array.isArray(exp.reached) ? exp.reached : []);
  const idx = stageIndex(exp.stage);
  return STAGES.map((stage, i) => {
    const r = results?.[stage];
    if (r === "pass" || r === "fail" || r === "pending") return { stage, mark: r };
    if (results || reached.size) {
      if (stage === exp.stage) return { stage, mark: exp.verdict === "failed_costs" ? "fail" : "pending" };
      return { stage, mark: reached.has(stage) ? "pass" : "none" };
    }
    if (i < idx) return { stage, mark: "pass" };
    if (i === idx) return { stage, mark: exp.verdict === "failed_costs" ? "fail" : "pending" };
    return { stage, mark: "none" };
  });
}

/** True when the experiment failed a gate: it must never look "closest to an edge". */
export function hasFailed(exp: Experiment): boolean {
  return exp.verdict === "failed_costs" || stageTrail(exp).some((t) => t.mark === "fail");
}

/** Leading candidates: still-alive ones first (furthest stage first), failed ones last. */
export function rankCandidates(list: Experiment[] | undefined): Experiment[] {
  return (list ?? [])
    .filter((e) => e && e.candidate === true)
    .sort((a, b) => {
      const fa = hasFailed(a) ? 1 : 0;
      const fb = hasFailed(b) ? 1 : 0;
      if (fa !== fb) return fa - fb;
      return stageIndex(b.stage) - stageIndex(a.stage);
    });
}

/** Fraction of the way from start to end (0..1), or null when either date is unknown. */
export function timeProgress(
  start: string | null | undefined,
  end: string | null | undefined,
  nowMs: number,
): number | null {
  const parse = (d: string) => Date.parse(d.length === 10 ? `${d}T00:00:00Z` : d);
  const s = start ? parse(start) : NaN;
  const e = end ? parse(end) : NaN;
  if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return null;
  return Math.max(0, Math.min(1, (nowMs - s) / (e - s)));
}

/** Live prospective tests never show an interim effect before the registered analysis. */
export function hideEffect(exp: Experiment): boolean {
  return exp.stage === "live_test" || exp.status === "collecting";
}

// ---------------------------------------------------------------------------------------------
// Experiment explorer

export interface ExperimentFilter {
  stages: string[];
  verdicts: string[];
  batches: string[];
  query: string;
}

export const EMPTY_FILTER: ExperimentFilter = { stages: [], verdicts: [], batches: [], query: "" };

/** Key used for an absent verdict so it can still be filtered. */
export const NO_VERDICT = "none";

export function verdictKey(exp: Experiment): string {
  return exp.verdict ? String(exp.verdict) : NO_VERDICT;
}

export function filterExperiments(list: Experiment[] | undefined, f: ExperimentFilter): Experiment[] {
  const q = f.query.trim().toLowerCase();
  const terms = q ? q.split(/\s+/) : [];
  return (list ?? []).filter((e) => {
    if (!e) return false;
    if (f.stages.length && !f.stages.includes(String(e.stage ?? ""))) return false;
    if (f.verdicts.length && !f.verdicts.includes(verdictKey(e))) return false;
    if (f.batches.length && !f.batches.includes(String(e.batch ?? ""))) return false;
    if (terms.length) {
      const hay = [e.id, e.title, e.plain, e.family, e.batch].filter(Boolean).join(" ").toLowerCase();
      if (!terms.every((t) => hay.includes(t))) return false;
    }
    return true;
  });
}

/** Distinct values with counts, in first-seen order (or a fixed order when given). */
export function facetCounts(
  list: Experiment[] | undefined,
  key: (e: Experiment) => string | null | undefined,
  order?: readonly string[],
): Array<{ value: string; count: number }> {
  const counts = new Map<string, number>();
  for (const e of list ?? []) {
    const v = key(e);
    if (!v) continue;
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  const entries = Array.from(counts, ([value, count]) => ({ value, count }));
  if (order) {
    entries.sort((a, b) => {
      const ia = order.indexOf(a.value);
      const ib = order.indexOf(b.value);
      return (ia < 0 ? 999 : ia) - (ib < 0 ? 999 : ib);
    });
  }
  return entries;
}

/** Live (not failed) candidates first, then furthest stage, then id. */
export function sortExperiments(list: Experiment[]): Experiment[] {
  const lead = (e: Experiment) => (e.candidate && !hasFailed(e) ? 1 : 0);
  return [...list].sort((a, b) => {
    if (lead(a) !== lead(b)) return lead(b) - lead(a);
    const d = stageIndex(b.stage) - stageIndex(a.stage);
    if (d) return d;
    return String(a.id).localeCompare(String(b.id), undefined, { numeric: true });
  });
}

// ---------------------------------------------------------------------------------------------
// Freshness

export type FreshState = "missing" | "fresh" | "stale";

export interface Freshness {
  state: FreshState;
  ageSeconds: number | null;
}

/**
 * Age of a snapshot measured on the server's clock (server_time − received_at) plus the time the
 * browser has waited since that response arrived, so a wrong client clock cannot hide staleness.
 */
export function snapshotFreshness(
  receivedAt: string | null | undefined,
  serverTime: string | null | undefined,
  fetchedAtMs: number,
  nowMs: number,
  staleAfterSeconds = 30 * 60,
): Freshness {
  const rec = receivedAt ? Date.parse(receivedAt) : NaN;
  if (Number.isNaN(rec)) return { state: "missing", ageSeconds: null };
  const srv = serverTime ? Date.parse(serverTime) : NaN;
  const base = Number.isNaN(srv) ? fetchedAtMs : srv;
  const age = Math.max(0, (base - rec) / 1000 + Math.max(0, nowMs - fetchedAtMs) / 1000);
  return { state: age > staleAfterSeconds ? "stale" : "fresh", ageSeconds: age };
}

export function agoLabel(ageSeconds: number | null): string {
  if (ageSeconds == null) return "never";
  if (ageSeconds < 60) return "just now";
  const m = Math.floor(ageSeconds / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h} h ago`;
  return `${Math.floor(h / 24)} days ago`;
}

// ---------------------------------------------------------------------------------------------
// Dates

/** Whole calendar days from now until an ISO date (UTC midnight), negative if past. */
export function daysUntil(date: string | null | undefined, nowMs: number): number | null {
  if (!date) return null;
  const t = Date.parse(date.length === 10 ? `${date}T00:00:00Z` : date);
  if (Number.isNaN(t)) return null;
  const today = Date.UTC(
    new Date(nowMs).getUTCFullYear(),
    new Date(nowMs).getUTCMonth(),
    new Date(nowMs).getUTCDate(),
  );
  const d = new Date(t);
  const target = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  return Math.round((target - today) / 86_400_000);
}

export function countdownLabel(days: number | null): string | null {
  if (days == null) return null;
  if (days > 1) return `in ${days} days`;
  if (days === 1) return "tomorrow";
  if (days === 0) return "today";
  return "due";
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "–";
  const t = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(t)) return "–";
  return new Date(t).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

// ---------------------------------------------------------------------------------------------
// Commands

export const IN_FLIGHT = new Set(["pending", "delivered"]);

/** Newest command for a target (commands arrive newest first, but do not rely on it). */
export function latestCommand(commands: LabCommand[] | undefined, target: CommandTarget): LabCommand | null {
  let best: LabCommand | null = null;
  for (const c of commands ?? []) {
    if (!c || c.target !== target) continue;
    if (!best) {
      best = c;
      continue;
    }
    const tc = Date.parse(c.created_at ?? "");
    const tb = Date.parse(best.created_at ?? "");
    if ((Number.isNaN(tb) && !Number.isNaN(tc)) || tc > tb || (tc === tb && c.id > best.id)) best = c;
  }
  return best;
}

export const COMMAND_STEPS = ["pending", "delivered", "done"] as const;

export function commandStepLabel(status: string): string {
  return (
    {
      pending: "Waiting for the machine to pick it up",
      delivered: "Delivered; the machine is applying it",
      done: "Done",
      failed: "Failed",
      expired: "Expired (not picked up within 2 hours)",
    }[status] ?? status
  );
}

// ---------------------------------------------------------------------------------------------
// Job outcomes

export function outcomeTone(outcome: string | null | undefined): Tone {
  switch (outcome) {
    case "done":
    case "ok":
    case "success":
      return "pos";
    case "error":
    case "failed":
      return "neg";
    case "tempfail":
    case "timeout":
    case "usage_limit":
    case "retry":
      return "warn";
    default:
      return "muted";
  }
}
