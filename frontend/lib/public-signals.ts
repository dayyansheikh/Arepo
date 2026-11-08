// Public signal-engine view: types for GET /api/public/signals (schema arepo-public-signals-v1) and
// the small pure helpers the /signals/live page uses. The backend allow-lists every field; this
// file only formats them. Signal strength is forecast quality of the 2h direction, never a
// probability, and nothing here renders res_7d, hit rates, cents, profit or liquidity splits.
import { API_BASE, ApiError } from "./api";

export const PUBLIC_NOTICE =
  "Research only. Signal strength, not a probability. Not advice, not a profit claim.";

export type Confidence = "strong" | "moderate" | "weak";

export interface PublicMarketRow {
  market_id: number | null;
  title: string | null;
  signal_strength: number;
  confidence: Confidence;
}

export interface PublicRecord {
  days: number | null;
  n: number | null;
  auc?: number | null;
  brier: number | null;
  log_loss: number | null;
  cal_slope: number | null;
  cal_intercept: number | null;
}

export interface PublicBand {
  band: Confidence;
  n: number | null;
  events: number | null;
  status: "ok" | "unavailable";
  days?: number | null;
  log_loss?: number | null;
  brier?: number | null;
  cal_slope?: number | null;
  cal_intercept?: number | null;
}

export interface PublicLeaderboardRow extends Partial<PublicRecord> {
  model_id: string;
  family: string;
  role: "champion" | "challenger";
  hidden_until?: string;
  provisional?: boolean;
}

export interface PublicFeed {
  origin_utc: string | null;
  stale: boolean;
  top_up: PublicMarketRow[];
  top_down: PublicMarketRow[];
  track_record: PublicRecord | null;
  days_scored: number | null;
  bands: PublicBand[];
}

export interface PublicSignals {
  schema: string;
  status: "ok" | "stale" | "unavailable" | "champion_hidden" | "no_feed";
  server_time: string;
  snapshot_received_at: string | null;
  champion: { model_id: string; family: string } | null;
  feed: PublicFeed | null;
  leaderboard: PublicLeaderboardRow[];
}

/** Resolves to the payload, or "disabled" when the endpoint is off (404). Other failures throw. */
export async function getPublicSignals(signal?: AbortSignal): Promise<PublicSignals | "disabled"> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/public/signals`, { cache: "no-store", signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("Unable to reach the Arepo API", 0);
  }
  if (res.status === 404) return "disabled";
  if (!res.ok) throw new ApiError(`Request failed with status ${res.status}`, res.status);
  return (await res.json()) as PublicSignals;
}

export type PageState = "live" | "stale" | "partial" | "unavailable";

/** Which view to render. "partial" = champion hidden or no feed: leaderboard only. */
export function pageState(d: PublicSignals): PageState {
  if (d.status === "unavailable") return "unavailable";
  if (d.status === "champion_hidden" || d.status === "no_feed" || !d.feed) return "partial";
  return d.status === "stale" || d.feed.stale ? "stale" : "live";
}

/** UTC text such as "2026-11-08 12:00 UTC"; null if missing or unparseable. */
export function formatUtc(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return null;
  return `${t.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

/** Snapshot time for the badge: the feed origin, falling back to when the snapshot was received. */
export function snapshotTime(d: PublicSignals): string | null {
  return formatUtc(d.feed?.origin_utc) ?? formatUtc(d.snapshot_received_at);
}

/** Signed strength to 3 decimals, e.g. "+0.312" / "-0.104"; never a percentage. */
export function formatStrength(s: number | null | undefined): string {
  if (s === null || s === undefined || !Number.isFinite(s)) return "–";
  const t = s.toFixed(3);
  return s > 0 ? `+${t}` : t;
}

export function formatScore(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "–";
  return v.toFixed(digits);
}

/** Embargoed rows show only this text, never a number from the row. */
export function embargoText(row: PublicLeaderboardRow): string | null {
  if (row.hidden_until === undefined) return null;
  const until = row.hidden_until;
  const t = /^\d{4}-\d{2}-\d{2}/.test(until) ? until.slice(0, 10) : until;
  return `hidden until ${t}`;
}

/** A band shows scores only when its status is ok. */
export function bandIsAvailable(b: PublicBand): boolean {
  return b.status === "ok";
}

export function bandNote(b: PublicBand): string {
  return bandIsAvailable(b) ? "" : "unavailable";
}
