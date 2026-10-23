// Pure helpers for the Lab "Signal engine" section (snapshot key `signal_engine`, schema
// `se-dash-v1`). Everything is parsed defensively: a missing, malformed or partial block never
// throws, and an embargoed row (a model under an active live test) never yields a number.
// Vocabulary: signal strength / forecast quality only; no probability of profit, no edge claim.

import type {
  SeInputAlert,
  SeAttribution,
  SeEmbargoToken,
  SeFamilyGain,
  SeModel,
  SePromotion,
  SePromotionCandidate,
  SePromotionStatus,
  SeRow,
  SignalEngineBlock,
} from "./types";

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

/**
 * Client-side embargo rule (defence in depth; the host already strips numbers). A date counts as an
 * active embargo when it is in the future or cannot be parsed (fail closed). The row's own date and
 * the model list's date are both checked, so a row that carries numbers but no date of its own is
 * still hidden while its model is under a live test.
 */
export function activeUntil(until: unknown, nowMs: number): string | null {
  const u = str(until);
  if (!u) return null;
  const t = Date.parse(u);
  return Number.isNaN(t) || t > nowMs ? u : null;
}

/** model_id -> embargoed_until from the model list. */
export function modelEmbargoes(se: SignalEngineBlock): Map<string, string> {
  const m = new Map<string, string>();
  for (const x of arr<SeModel>(se.models)) {
    const id = str(x.model_id);
    const u = str(x.embargoed_until);
    if (id && u) m.set(id, u);
  }
  return m;
}

/** The active embargo date for a row (its own, else its model's), or null when it may show numbers. */
export function rowEmbargo(
  row: { model_id?: unknown; embargoed_until?: unknown } | null | undefined,
  nowMs: number,
  models?: Map<string, string>,
): string | null {
  if (!row || !isObj(row)) return null;
  const id = str(row.model_id);
  return activeUntil(row.embargoed_until, nowMs) ?? (id && models ? activeUntil(models.get(id), nowMs) : null);
}

export function isEmbargoed(
  row: { model_id?: unknown; embargoed_until?: unknown } | null | undefined,
  nowMs: number,
  models?: Map<string, string>,
): boolean {
  return rowEmbargo(row, nowMs, models) !== null;
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
      gainVsMid: number | null;
      gainVsMidLo: number | null;
      gainVsMidHi: number | null;
    };

/** Display cells for one row. Embargoed rows return only the id and date, never a number. */
export function rowCells(row: SeRow, nowMs: number, models?: Map<string, string>): SeCells {
  const modelId = str(row.model_id) ?? "unknown model";
  const until = rowEmbargo(row, nowMs, models);
  if (until) return { kind: "embargoed", modelId, until };
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
    gainVsMid: num(row.gain_vs_mid),
    gainVsMidLo: num(row.gain_vs_mid_lo),
    gainVsMidHi: num(row.gain_vs_mid_hi),
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

export function prospectiveRows(se: SignalEngineBlock, nowMs: number): SeCells[] {
  const models = modelEmbargoes(se);
  const rows = arr<SeRow>(se.prospective?.rows).filter(
    (r) => isEmbargoed(r, nowMs, models) || r.window_days === undefined || r.window_days === SE_WINDOW_DAYS,
  );
  return sortRows(
    rows.map((r) => rowCells(r, nowMs, models)),
    str(se.primary_target),
  );
}

export function developmentRows(se: SignalEngineBlock, nowMs: number): SeCells[] {
  const models = modelEmbargoes(se);
  return sortRows(
    arr<SeRow>(se.development?.rows).map((r) => rowCells(r, nowMs, models)),
    str(se.primary_target),
  );
}

export type SeStatus = "bootstrapping" | "scoring";

/** Bootstrapping unless the engine says it is scoring and there is at least one scored row. */
export function engineStatus(se: SignalEngineBlock, nowMs: number): SeStatus {
  const scored = prospectiveRows(se, nowMs).some((r) => r.kind === "scored");
  return se.prospective?.status === "scoring" && scored ? "scoring" : "bootstrapping";
}

export interface InputsView {
  status: "ok" | "alert";
  at?: string;
  captureId?: string;
  nAlerts: number;
  /** Plain-English alert lines (at most `INPUT_LINES`). */
  lines: string[];
}

export const INPUT_LINES = 6;

/** One monitor alert as a plain-English line; unknown rules fall back to "family column: rule". */
export function inputAlertLine(a: SeInputAlert): string {
  const fam = str(a.family) ?? "input";
  const where = str(a.column) ? `${fam} ${a.column}` : fam;
  const latest = num(a.latest);
  const median = num(a.median);
  switch (a.rule) {
    case "capture_gap": {
      const n = num(a.missing_slots) ?? 0;
      return `${n} missed capture${n === 1 ? "" : "s"} in the last day (first ${fmtUtc(str(a.first_missing_utc))})`;
    }
    case "universe":
      return `Eligible markets ${latest ?? DASH} against a usual ${median !== null ? Math.round(median) : DASH}`;
    case "missing":
      return `${where}: table not written`;
    case "absent":
      return `${where}: empty (usually ${fmtPct(median)} filled)`;
    case "drop":
      return `${where}: ${fmtPct(latest)} filled (usually ${fmtPct(median)})`;
    case "all_zero":
      return `${where}: all zero (usually ${fmtPct(median)} non-zero)`;
    default:
      return `${where}: ${str(a.rule) ?? "alert"}`;
  }
}

/** The input monitor's view, or null when the block has none or an unknown status. */
export function inputsView(se: SignalEngineBlock): InputsView | null {
  const h = se.inputs;
  if (!isObj(h) || (h.status !== "ok" && h.status !== "alert")) return null;
  const alerts = arr<SeInputAlert>(h.alerts);
  const nAlerts = num(h.n_alerts) ?? alerts.length;
  return {
    status: h.status === "alert" || nAlerts > 0 ? "alert" : "ok",
    at: str(h.at),
    captureId: str(h.capture_id),
    nAlerts,
    lines: alerts.slice(0, INPUT_LINES).map(inputAlertLine),
  };
}

export function familyOf(se: SignalEngineBlock): Map<string, string> {
  const m = new Map<string, string>();
  for (const x of arr<SeModel>(se.models)) {
    const id = str(x.model_id);
    if (id && str(x.family)) m.set(id, x.family as string);
  }
  return m;
}

export interface GainSeries {
  key: string;
  label: string;
  points: Array<{ date: string; gain: number; lo: number | null; hi: number | null }>;
}

/** One series per challenger (labelled by family), dropping embargoed models and non-finite gains. */
export function familySeries(se: SignalEngineBlock, nowMs: number): GainSeries[] {
  const models = modelEmbargoes(se);
  const byKey = new Map<string, GainSeries>();
  for (const g of arr<SeFamilyGain>(se.family_gains)) {
    const id = str(g.model_id);
    const date = str(g.date);
    const gain = num(g.gain);
    if (!id || !date || gain === null || isEmbargoed(g, nowMs, models)) continue;
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
    .filter((p) => str(p.champion) && (p.event === undefined || p.event === "promotion"))
    .sort((a, b) => (str(b.at) ?? "").localeCompare(str(a.at) ?? ""));
}

export const PROMOTION_CHECKS: Array<[string, string]> = [
  ["c1_days", "14 days"],
  ["c2_ci", "lower bounds above zero"],
  ["c3_days_positive", "share of positive days"],
  ["c4_calibration", "calibration"],
  ["c5_secondary", "secondary targets"],
  ["c6_coverage", "coverage"],
  ["c7_cooldown", "cool-down"],
];

export interface PromotionCandidateView {
  modelId: string;
  pass: boolean;
  eligible: boolean;
  ineligibleSince: string | null;
  days: number | null;
  daysToMin: number | null;
  gain: number | null;
  loEvent: number | null;
  loTwoway: number | null;
  /** se_day^2 / (se_event^2 + se_day^2), or null when either is missing / the total is zero. */
  dayShare: number | null;
  passed: number;
  total: number;
  failed: string[];
}

export interface PromotionView {
  rule: string;
  at: string | null;
  k: number | null;
  level: number | null;
  promote: string | null;
  reason: string | null;
  candidates: PromotionCandidateView[];
}

/** Share of the combined uncertainty that comes from day-level shocks; null when not computable. */
export function dayShare(seEvent: number | null, seDay: number | null): number | null {
  if (seEvent === null || seDay === null) return null;
  const tot = seEvent * seEvent + seDay * seDay;
  return tot > 0 ? (seDay * seDay) / tot : null;
}

/**
 * Promotion-rule status card. Candidates whose model is under an active embargo (own date or the
 * model list's) are dropped, and `promote` is withheld when it names an embargoed model.
 */
export function promotionView(se: SignalEngineBlock, nowMs: number): PromotionView | null {
  const p = se.promotion as SePromotionStatus | null | undefined;
  if (!isObj(p)) return null;
  const models = modelEmbargoes(se);
  const candidates: PromotionCandidateView[] = [];
  for (const c of arr<SePromotionCandidate>(p.candidates)) {
    const modelId = str(c.model_id);
    if (!modelId || isEmbargoed(c, nowMs, models)) continue;
    const checks = isObj(c.checks) ? c.checks : {};
    const failed = PROMOTION_CHECKS.filter(([k]) => checks[k] !== true).map(([, label]) => label);
    candidates.push({
      modelId,
      pass: c.pass === true && c.eligible !== false,
      eligible: c.eligible !== false,
      ineligibleSince: str(c.ineligible_since) ?? null,
      days: num(c.days),
      daysToMin: num(c.days_to_min),
      gain: num(c.gain),
      loEvent: num(c.lo_event),
      loTwoway: num(c.lo_twoway),
      dayShare: dayShare(num(c.se_event), num(c.se_day)),
      passed: PROMOTION_CHECKS.length - failed.length,
      total: PROMOTION_CHECKS.length,
      failed,
    });
  }
  const promote = str(p.promote);
  return {
    rule: str(p.rule) ?? "promotion rule",
    at: str(p.at) ?? null,
    k: num(p.K),
    level: num(p.level),
    promote: promote && !isEmbargoed({ model_id: promote }, nowMs, models) ? promote : null,
    reason: str(p.reason) ?? null,
    candidates,
  };
}

export interface AttributionView {
  modelId: string;
  target: string;
  fitTime: string | null;
  rows: number | null;
  label: string;
  /** Visible families, largest first; `share` is of the visible total only, so hidden families leak nothing. */
  families: Array<{ family: string; value: number; share: number }>;
  /** Families withheld under an active live-test embargo: names only, never a value. */
  hidden: string[];
}

/**
 * Family attribution (development diagnostic of the newest primary-target LightGBM fit, never a score).
 * Re-applies the embargo client-side: entries of embargoed models are dropped, and any family named by an
 * active embargo token moves to `hidden` without its value.
 */
export function attributionViews(se: SignalEngineBlock, nowMs: number): AttributionView[] {
  const models = modelEmbargoes(se);
  const tokens = new Set<string>();
  for (const e of arr<SeEmbargoToken>(se.embargo_tokens)) {
    const t = str(e.token);
    // A token with a missing or unparseable date counts as active (fail closed).
    if (t && (activeUntil(e.until, nowMs) !== null || !str(e.until))) tokens.add(t);
  }
  const out: AttributionView[] = [];
  for (const a of arr<SeAttribution>(se.attribution)) {
    const modelId = str(a.model_id);
    if (!modelId || isEmbargoed(a, nowMs, models)) continue;
    const hidden = new Set<string>(Array.isArray(a.hidden) ? a.hidden.filter((h): h is string => !!str(h)) : []);
    const visible: Array<{ family: string; value: number }> = [];
    for (const [family, v] of Object.entries(isObj(a.families) ? a.families : {})) {
      if (tokens.has(family)) hidden.add(family);
      else if (typeof v === "number" && Number.isFinite(v) && v >= 0) visible.push({ family, value: v });
    }
    const total = visible.reduce((s, f) => s + f.value, 0);
    out.push({
      modelId,
      target: str(a.target) ?? "",
      fitTime: str(a.fit_time) ?? null,
      rows: num(a.rows),
      label: str(a.label) ?? "Development diagnostic (mean |SHAP| on the fit's validation block), not a score",
      families: visible
        .map((f) => ({ ...f, share: total > 0 ? f.value / total : 0 }))
        .sort((x, y) => y.value - x.value || x.family.localeCompare(y.family)),
      hidden: Array.from(hidden).sort(),
    });
  }
  return out.sort((x, y) => x.modelId.localeCompare(y.modelId));
}

// ---- champion signal feed (`se-feed-v1`) --------------------------------------------------------

export const SE_FEED_SCHEMA = "se-feed-v1";
const POLYMARKET_PREFIX = "https://polymarket.com/";

export interface SeFeedRowView {
  marketId: string;
  title: string | null;
  url: string | null;
  category: string;
  mid: number | null;
  spread: number | null;
  hoursToEnd: number | null;
  s2h: number | null;
  s6h: number | null;
  s24h: number | null;
}

export interface SeFeedHorizon {
  eligible: number | null;
  absGe025: number | null;
}

export interface SeFeedTrackRow {
  target: string;
  n: number | null;
  days: number | null;
  logLoss: number | null;
  auc: number | null;
  calSlope: number | null;
}

export interface SeFeedView {
  modelId: string;
  captureId: string | null;
  originUtc: string | null;
  predictionWrittenUtc: string | null;
  stale: boolean;
  label: string;
  titlesError: string | null;
  spreadMax: number | null;
  midRange: [number, number] | null;
  poolMarkets: number | null;
  poolNote: string | null;
  dir2h: SeFeedHorizon;
  up: SeFeedRowView[];
  down: SeFeedRowView[];
  track: { label: string; daysScored: number | null; rows: SeFeedTrackRow[] } | null;
}

const FEED_LABEL =
  "Signal strength = the champion's forecast of up minus down over the horizon. Forecast quality only, not advice.";

function feedRows(v: unknown): SeFeedRowView[] {
  const out: SeFeedRowView[] = [];
  for (const r of Array.isArray(v) ? v : []) {
    if (!isObj(r)) continue;
    const id = typeof r.market_id === "number" && Number.isFinite(r.market_id) ? String(r.market_id) : str(r.market_id);
    if (!id) continue;
    const url = str(r.url);
    out.push({
      marketId: id,
      title: str(r.title) ?? null,
      url: url && url.startsWith(POLYMARKET_PREFIX) ? url : null,
      category: str(r.category) ?? "",
      mid: num(r.mid),
      spread: num(r.spread),
      hoursToEnd: num(r.hours_to_end),
      s2h: num(r.s_2h),
      s6h: num(r.s_6h),
      s24h: num(r.s_24h),
    });
  }
  return out;
}

/**
 * Champion-only per-market signal feed. Null unless the schema matches, the feed was produced by the
 * block's current champion, and that champion is not under an active live-test embargo (fail closed).
 * Never throws.
 */
export function parseSeFeed(se: SignalEngineBlock | null | undefined, nowMs: number): SeFeedView | null {
  try {
    if (!se || typeof se !== "object" || Array.isArray(se)) return null;
    const f = se.feed;
    if (!isObj(f) || f.schema !== SE_FEED_SCHEMA) return null;
    const champ = str(se.champion?.model_id);
    const feedChamp = isObj(f.champion) ? str(f.champion.model_id) : undefined;
    if (!champ || !feedChamp || champ !== feedChamp) return null;
    if (isEmbargoed({ model_id: champ }, nowMs, modelEmbargoes(se))) return null;
    const pool = isObj(f.pool) ? f.pool : {};
    const mr = Array.isArray(pool.mid_range) ? pool.mid_range.map(num) : [];
    const sum = isObj(f.summary) && isObj(f.summary.dir_2h) ? f.summary.dir_2h : {};
    const tr = isObj(f.track_record) ? f.track_record : null;
    return {
      modelId: champ,
      captureId: str(f.capture_id) ?? null,
      originUtc: str(f.origin_utc) ?? null,
      predictionWrittenUtc: str(f.prediction_written_utc) ?? null,
      stale: f.stale === true,
      label: str(f.label) ?? FEED_LABEL,
      titlesError: str(f.titles_error) ?? null,
      spreadMax: num(pool.spread_max),
      midRange: mr.length === 2 && mr[0] !== null && mr[1] !== null ? [mr[0], mr[1]] : null,
      poolMarkets: num(pool.markets),
      poolNote: str(pool.note) ?? null,
      dir2h: { eligible: num(sum.eligible), absGe025: num(sum.abs_ge_0_25) },
      up: feedRows(f.top_up),
      down: feedRows(f.top_down),
      track: tr
        ? {
            label: str(tr.label) ?? "",
            daysScored: num(tr.days_scored),
            rows: (Array.isArray(tr.rows) ? tr.rows : []).filter(isObj).map((r) => ({
              target: str(r.target) ?? "",
              n: num(r.n),
              days: num(r.days),
              logLoss: num(r.log_loss),
              auc: num(r.auc),
              calSlope: num(r.cal_slope),
            })),
          }
        : null,
    };
  } catch {
    return null;
  }
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

/** Price or spread as cents, e.g. 0.105 -> "10.5c". */
export function fmtCents(v: number | null | undefined): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return DASH;
  return `${(v * 100).toFixed(1).replace(/\.0$/, "")}c`;
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
