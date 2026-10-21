// Pure helpers for the Lab "Signal engine" section (snapshot key `signal_engine`, schema
// `se-dash-v1`). Everything is parsed defensively: a missing, malformed or partial block never
// throws, and an embargoed row (a model under an active live test) never yields a number.
// Vocabulary: signal strength / forecast quality only; no probability of profit, no edge claim.

import type { SeFamilyGain, SeModel, SePromotion, SeRow, SignalEngineBlock } from "./types";

export const SE_SCHEMA = "se-dash-v1";
/** Leaderboard window shown in the prospective table (DESIGN_V1 section 14). */
export const SE_WINDOW_DAYS = 14;

const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const str = (v: unknown): string | undefined => (typeof v === "string" && v ? v : undefined);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const arr = <T>(v: unknown): T[] => (Array.isArray(v) ? (v.filter(isObj) as T[]) : []);

/** The block, or null when absent / not an object / a different schema. */
export function parseSignalEngine(raw: unknown): SignalEngineBlock | null {
  if (!isObj(raw) || raw.schema !== SE_SCHEMA) return null;
  return raw as SignalEngineBlock;
}

/** A row is embargoed whenever it names an embargo date; the host already strips its numbers. */
export function isEmbargoed(row: SeRow | SeFamilyGain | null | undefined): boolean {
  return !!row && isObj(row) && !!str((row as SeRow).embargoed_until);
}

export type SeCells =
  | { kind: "embargoed"; modelId: string; until: string }
  | {
      kind: "scored";
      modelId: string;
      role: string;
      target: string;
      n: number | null;
      logLoss: number | null;
      brier: number | null;
      calSlope: number | null;
      calIntercept: number | null;
      auc: number | null;
      coverage: number | null;
      gain: number | null;
      gainLo: number | null;
      gainHi: number | null;
      daysPositive: number | null;
      nDays: number | null;
    };

/** Display cells for one row. Embargoed rows return only the id and date, never a number. */
export function rowCells(row: SeRow): SeCells {
  const modelId = str(row.model_id) ?? "unknown model";
  if (isEmbargoed(row)) return { kind: "embargoed", modelId, until: String(row.embargoed_until) };
  return {
    kind: "scored",
    modelId,
    role: str(row.role) ?? "",
    target: str(row.target) ?? "",
    n: num(row.n),
    logLoss: num(row.log_loss),
    brier: num(row.brier),
    calSlope: num(row.cal_slope),
    calIntercept: num(row.cal_intercept),
    auc: num(row.auc),
    coverage: num(row.coverage),
    gain: num(row.gain),
    gainLo: num(row.gain_lo),
    gainHi: num(row.gain_hi),
    daysPositive: num(row.days_positive),
    nDays: num(row.n_days),
  };
}

/** Sort by target, then champion first, then gain (best first); embargoed rows last. */
export function sortRows(rows: SeCells[], primaryTarget?: string): SeCells[] {
  const tRank = (t: string) => (t === primaryTarget ? "" : t);
  return [...rows].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "embargoed" ? 1 : -1;
    if (a.kind === "embargoed" || b.kind === "embargoed") return a.modelId.localeCompare(b.modelId);
    const t = tRank(a.target).localeCompare(tRank(b.target));
    if (t) return t;
    if ((a.role === "champion") !== (b.role === "champion")) return a.role === "champion" ? -1 : 1;
    return (b.gain ?? -Infinity) - (a.gain ?? -Infinity);
  });
}

export function prospectiveRows(se: SignalEngineBlock): SeCells[] {
  const rows = arr<SeRow>(se.prospective?.rows).filter(
    (r) => isEmbargoed(r) || r.window_days === undefined || r.window_days === SE_WINDOW_DAYS,
  );
  return sortRows(rows.map(rowCells), str(se.primary_target));
}

export function developmentRows(se: SignalEngineBlock): SeCells[] {
  return sortRows(arr<SeRow>(se.development?.rows).map(rowCells), str(se.primary_target));
}

export type SeStatus = "bootstrapping" | "scoring";

/** Bootstrapping unless the engine says it is scoring and there is at least one scored row. */
export function engineStatus(se: SignalEngineBlock): SeStatus {
  const scored = prospectiveRows(se).some((r) => r.kind === "scored");
  return se.prospective?.status === "scoring" && scored ? "scoring" : "bootstrapping";
}

export function familyOf(se: SignalEngineBlock): Map<string, string> {
  const m = new Map<string, string>();
  for (const x of arr<SeModel>(se.models)) {
    const id = str(x.model_id);
    if (id && str(x.family)) m.set(id, x.family as string);
  }
  return m;
}

/** Models currently embargoed according to the model list (defence in depth for the chart). */
function embargoedModels(se: SignalEngineBlock, nowMs: number): Set<string> {
  const out = new Set<string>();
  for (const x of arr<SeModel>(se.models)) {
    const id = str(x.model_id);
    const t = str(x.embargoed_until) ? Date.parse(x.embargoed_until as string) : NaN;
    if (id && (Number.isNaN(t) ? !!str(x.embargoed_until) : t > nowMs)) out.add(id);
  }
  return out;
}

export interface GainSeries {
  key: string;
  label: string;
  points: Array<{ date: string; gain: number; lo: number | null; hi: number | null }>;
}

/** One series per challenger (labelled by family), dropping embargoed models and non-finite gains. */
export function familySeries(se: SignalEngineBlock, nowMs: number): GainSeries[] {
  const blocked = embargoedModels(se, nowMs);
  const byKey = new Map<string, GainSeries>();
  for (const g of arr<SeFamilyGain>(se.family_gains)) {
    const id = str(g.model_id);
    const date = str(g.date);
    const gain = num(g.gain);
    if (!id || !date || gain === null || blocked.has(id) || isEmbargoed(g)) continue;
    let s = byKey.get(id);
    if (!s) {
      s = { key: id, label: str(g.family) ?? id, points: [] };
      byKey.set(id, s);
    }
    s.points.push({ date, gain, lo: num(g.lo), hi: num(g.hi) });
  }
  const list = Array.from(byKey.values());
  const counts = new Map<string, number>();
  for (const s of list) counts.set(s.label, (counts.get(s.label) ?? 0) + 1);
  for (const s of list) {
    if ((counts.get(s.label) ?? 0) > 1) s.label = `${s.label} (${s.key})`;
    s.points.sort((a, b) => a.date.localeCompare(b.date));
  }
  return list.sort((a, b) => a.label.localeCompare(b.label));
}

export function promotions(se: SignalEngineBlock): SePromotion[] {
  return arr<SePromotion>(se.promotions)
    .filter((p) => str(p.champion))
    .sort((a, b) => (str(b.at) ?? "").localeCompare(str(a.at) ?? ""));
}

// ---- formatting --------------------------------------------------------------------------------

const DASH = "–";

export function fmtFixed(v: number | null | undefined, dp: number): string {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(dp) : DASH;
}

/** Signed with a true minus sign, e.g. "+0.0031" / "−0.0012". */
export function fmtSigned(v: number | null | undefined, dp = 4): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return DASH;
  const s = Math.abs(v).toFixed(dp);
  if (Number(s) === 0) return s;
  return `${v > 0 ? "+" : "−"}${s}`;
}

export function fmtPct(v: number | null | undefined): string {
  return typeof v === "number" && Number.isFinite(v) ? `${Math.round(v * 100)}%` : DASH;
}

/** "+0.0031 [−0.0004, +0.0066]" or "–" when there is no gain (e.g. the champion itself). */
export function fmtGain(gain: number | null, lo: number | null, hi: number | null): string {
  if (gain === null) return DASH;
  if (lo === null || hi === null) return fmtSigned(gain);
  return `${fmtSigned(gain)} [${fmtSigned(lo)}, ${fmtSigned(hi)}]`;
}

export function fmtDaysPositive(pos: number | null, n: number | null): string {
  return pos === null || n === null || n <= 0 ? DASH : `${pos}/${n}`;
}

/** "21 Oct 2026, 14:05 UTC" or the date only when no time is present. */
export function fmtUtc(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const t = Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(t)) return DASH;
  const d = new Date(t);
  const date = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  if (iso.length === 10) return date;
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" });
  return `${date}, ${time} UTC`;
}

export function embargoLabel(until: string): string {
  const d = fmtUtc(until.slice(0, 10));
  return `embargoed until ${d === DASH ? until.slice(0, 40) : d} (live test)`;
}
