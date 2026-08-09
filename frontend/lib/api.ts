import type {
  AccountUser,
  AlertDelivery,
  AlertPreferences,
  AlertPreferencesUpdate,
  BacktestResponse,
  CohortDetail,
  CohortWeek,
  DataMode,
  DataStatus,
  DigestDetail,
  DigestList,
  HistoricalScreen,
  MarketDetailResponse,
  MarketFacets,
  MarketsResponse,
  MetaResponse,
  MarketSearchResponse,
  SavedMarket,
  BoardView,
  OpportunityBoard,
  OverviewResponse,
  ProvenanceInfo,
  ReplayScenarioResponse,
  SignalsResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  notFound: boolean;
  /**
   * True for the failure classes that indicate the API is momentarily unavailable rather than
   * genuinely broken: a network-level failure (status 0) or a gateway status (502/503/504). On a
   * free host (Render Free) the first request after idle can hit this while the service cold-starts;
   * the UI treats it as a restrained "Connecting to Arepo data…" state, not an error (spec §13).
   */
  coldStart: boolean;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.notFound = status === 404;
    this.coldStart = status === 0 || status === 502 || status === 503 || status === 504;
  }
}


function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function apiFetch<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
  opts: { signal?: AbortSignal } = {},
): Promise<T> {
  const url = `${API_BASE}${path}${buildQuery(params)}`;
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store", signal: opts.signal });
  } catch (err) {
    // A caller-initiated abort (unmount/navigation) is not a connection error — re-throw it so the
    // poller can ignore it silently rather than surfacing a spurious "disconnected" state.
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    const message = err instanceof Error ? err.message : "Network request failed";
    // status 0 marks this as a cold-start-class failure (ApiError.coldStart); the useAsync layer
    // decides how to present/retry it (spec §13). The shared status poller has its own backoff and
    // is intentionally NOT retried here, so its request accounting is unchanged.
    throw new ApiError(`Unable to reach the Arepo API: ${message}`, 0);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = normalizeDetail(body.detail);
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new ApiError(detail || `Request failed with status ${res.status}`, res.status);
  }

  return (await res.json()) as T;
}

/** FastAPI `detail` may be a string or an array of validation objects — render it readably. */
function normalizeDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        d && typeof d === "object" && "msg" in d
          ? String((d as { msg: unknown }).msg)
          : String(d)
      )
      .join("; ");
  }
  return "Request failed";
}

export function getMeta(): Promise<MetaResponse> {
  return apiFetch<MetaResponse>("/api/meta");
}

export function getStatus(mode: DataMode, signal?: AbortSignal): Promise<DataStatus> {
  return apiFetch<DataStatus>("/api/status", { mode }, { signal });
}

export function getOverview(mode: DataMode): Promise<OverviewResponse> {
  return apiFetch<OverviewResponse>("/api/overview", { mode });
}

export interface GetMarketsParams {
  search?: string;
  category?: string;
  status?: string;
  sort?: "volume" | "volume_24hr" | "liquidity" | "end_date";
  limit?: number;
  offset?: number;
  mode: DataMode;
}

export function getMarkets(params: GetMarketsParams): Promise<MarketsResponse> {
  return apiFetch<MarketsResponse>("/api/markets", { ...params });
}

export function getMarket(id: string, mode: DataMode, range?: string): Promise<MarketDetailResponse> {
  return apiFetch<MarketDetailResponse>(`/api/markets/${encodeURIComponent(id)}`, { mode, range });
}

/** Distinct category, sport, competition and status values that actually
 * occur in the current mode's data, for building filter dropdowns without
 * inventing options the data doesn't have. */
export function getFacets(mode: DataMode): Promise<MarketFacets> {
  return apiFetch<MarketFacets>("/api/markets/facets", { mode });
}

export function getSignals(mode: DataMode, limit?: number): Promise<SignalsResponse> {
  return apiFetch<SignalsResponse>("/api/signals", { mode, limit });
}

export interface GetBacktestParams {
  strength_threshold?: number;
  move_threshold?: number;
  horizon?: number;
}

export function getBacktest(params: GetBacktestParams): Promise<BacktestResponse> {
  return apiFetch<BacktestResponse>("/api/replay/backtest", { ...params });
}

export function getReplayScenario(): Promise<ReplayScenarioResponse> {
  return apiFetch<ReplayScenarioResponse>("/api/replay/scenario");
}

// -- Prospective cohort evaluation ------------------------------------------------------

export function getCohortWeeks(): Promise<CohortWeek[]> {
  return apiFetch<CohortWeek[]>("/api/cohorts/weeks");
}

export function getCohortProvenance(): Promise<ProvenanceInfo> {
  return apiFetch<ProvenanceInfo>("/api/cohorts/provenance");
}

export function getCohort(isoYear: number, isoWeek: number): Promise<CohortDetail> {
  return apiFetch<CohortDetail>(`/api/cohorts/${isoYear}/${isoWeek}`);
}

// -- Opportunity Board + search ---------------------------------------------------------

export function getOpportunityBoard(
  mode: DataMode,
  view: BoardView = "directional",
  top = 30,
): Promise<OpportunityBoard> {
  return apiFetch<OpportunityBoard>("/api/opportunity/board", { mode, top, view });
}

export function searchMarkets(
  q: string,
  activeOnly = true,
  limit = 20,
  offset = 0
): Promise<MarketSearchResponse> {
  return apiFetch<MarketSearchResponse>("/api/markets/search", {
    q,
    active_only: activeOnly ? "true" : "false",
    limit,
    offset,
  });
}

// -- Historical reconstructed retrospective ---------------------------------------------

export function getHistoricalScreen(
  days = 7,
  limit = 24,
  topN = 15
): Promise<HistoricalScreen> {
  return apiFetch<HistoricalScreen>("/api/historical/screen", {
    days,
    limit,
    top_n: topN,
  });
}

export interface ReplayDataStatus {
  microstructure_snapshots_stored: number;
  last_collection_at: string | null;
  collector_recent: boolean;
  seconds_since_last_collection: number | null;
  snapshot_interval_seconds: number;
  weekly_cohorts_total: number;
  prospective_cohorts: number;
  oldest_cutoff: string | null;
  newest_cutoff: string | null;
  note: string;
}

export function getReplayDataStatus(): Promise<ReplayDataStatus> {
  return apiFetch<ReplayDataStatus>("/api/replay/data-status");
}

export interface ResearchStatus {
  generated_at?: string;
  model_version: string;
  cohort_counts_by_cadence: Record<string, number>;
  total_frozen_markets: number;
  roles?: Record<string, number>;
  directional_signals: number;
  public_selections: number;
  shadow_signals: number;
  observations: number;
  abstentions: number;
  horizon_coverage: Record<string, { evaluable: number; pending: number }>;
  resolved_markets: number;
  oldest_cohort: string | null;
  newest_cohort: string | null;
  last_successful_freeze: string | null;
  degraded_cohorts?: number;
  late_cohorts: number;
  excessively_late_cohorts_excluded: number;
  latest_run: {
    scheduled_for: string | null;
    frozen_at: string | null;
    evaluation_origin_at: string | null;
    lateness_seconds: number;
    late: boolean;
    excessively_late: boolean;
    excluded_markets?: number;
    universe_size: number;
    degraded: boolean;
  } | null;
  incomplete_cohorts?: number;
  microstructure_snapshots: number;
  last_microstructure_collection?: string | null;
  collector_recent: boolean;
  calibration: { available: boolean; resolved_sample: number; minimum_required: number; message: string };
  edge: {
    edge_supported: boolean;
    message: string;
    criteria: Record<string, boolean>;
    evaluable_sample_24h: number;
    arepo_momentum_agreement_24h?: number | null;
    model_limitation_note?: string;
  };
  note: string;
}

export function getResearchStatus(): Promise<ResearchStatus> {
  return apiFetch<ResearchStatus>("/api/research/status");
}

// -- Prospective Replay product ---------------------------------------------------------
// The public Replay surface is prospective-only: real cohorts genuinely frozen before later
// prices were known. These endpoints serve the cohort selectors and the per-cohort result set.

export interface ReplayCohort {
  id: number;
  cadence: string;
  cadence_label: string;
  cadence_description: string;
  scheduled_for: string | null;
  frozen_at: string | null;
  evaluation_origin_at: string | null;
  lateness_seconds: number;
  lateness_minutes: number;
  late: boolean;
  excessively_late: boolean;
  degraded: boolean;
  universe_size: number;
  directional_count: number;
  public_selection_count: number;
  shadow_count: number;
  observation_count: number;
  abstention_count: number;
  excluded_markets: number;
  available_horizons: Record<string, boolean>;
  resolution_available: boolean;
  model_version: string;
}

export interface ReplayCadence {
  cadence: string;
  label: string;
  description: string;
  count: number;
  newest_cohort_id: number;
}

export interface ReplayCohortList {
  generated_at: string;
  model_version: string;
  cohorts: ReplayCohort[];
  cadences: ReplayCadence[];
  default_cohort_id: number | null;
  has_prospective: boolean;
  first_freeze: string | null;
  latest_freeze: string | null;
  note: string;
}

export interface ReplayCounts {
  total: number;
  moved_expected: number;
  moved_against: number;
  no_change: number;
  pending: number;
  unavailable: number;
  invalid: number;
  moved: number;
  evaluated: number;
  movement_coverage: number | null;
  hit_rate_among_moved: number | null;
}

export interface ReplayExecutable {
  available: boolean;
  move: number | null;
  round_trip_cost: number | null;
  unavailable_reason: string | null;
}

export interface ReplayRow {
  rank: number | null;
  market_id: string;
  condition_id: string | null;
  token_id: string;
  market_question: string;
  outcome_name: string;
  role: string;
  direction: string | null;
  frozen_midpoint: number | null;
  horizon_midpoint: number | null;
  movement_pp: number | null;
  midpoint_move: number | null;
  executable: ReplayExecutable;
  time_remaining_hours: number | null;
  result_state: string;
  resolution: { resolved: boolean; resolved_outcome: string | null; correct: boolean | null };
  freeze_to_close?: {
    state: string;
    freeze_midpoint: number | null;
    preclose_midpoint: number | null;
    movement: number | null;
    result: string | null;
    closed?: boolean;
  };
  evolution?: {
    available: boolean;
    label?: string;
    later_strength?: number | null;
    strength_change?: number | null;
    later_direction?: string | null;
    direction_reversed?: boolean;
  };
  strength: number;
  confidence: number;
  research_priority: number;
}

export interface ReplayResolution {
  resolved_correct: number;
  resolved_incorrect: number;
  unresolved: number;
  total: number;
}

export interface ReplayResult {
  found: boolean;
  cohort: ReplayCohort;
  horizon: string;
  horizon_evaluable: boolean;
  available_horizons: Record<string, boolean>;
  resolution_available: boolean;
  scope: string;
  closing: string;
  closing_max_hours: number | null;
  qualifying: number;
  shown: number;
  rows: ReplayRow[];
  headline: ReplayCounts;
  public: ReplayCounts;
  shadow: ReplayCounts;
  combined: ReplayCounts;
  role_counts: Record<string, number>;
  resolution: ReplayResolution;
  freeze_to_close?: {
    moved_expected: number;
    moved_against: number;
    no_change: number;
    closed_final: number;
    pending: number;
  };
  denominators?: {
    observations: number;
    unique_markets: number;
    unique_events: number;
    repeated_markets: number;
  };
  selection_policy?: string | null;
  public_selection_limit?: number | null;
  note: string;
}

// -- Complete-scan Signal Lab ------------------------------------------------------------
// The complete short-horizon universe: full pagination discovers every active market, the 30-day
// eligibility gate + buckets run server-side, every eligible market is analysed and ranked, and the
// public top ten is only a display subset over the preserved full universe.

export interface ScanBucketCount {
  bucket: string;
  label: string;
  eligible?: number;
  directional?: number;
  public_top_ten?: number;
  shadow_directional?: number;
}

export interface Freshness {
  state: "fresh" | "refresh_delayed" | "out_of_date";
  age_seconds: number;
  updated_phrase: string;
  warn: boolean;
  tooltip: string;
}

export interface ScanStatus {
  has_scan: boolean;
  note?: string;
  generated_at?: string;
  seconds_since_scan?: number;
  freshness?: Freshness;
  scan_id?: string;
  started_at?: string;
  status?: string;
  pagination_complete?: boolean;
  pagination_reason?: string | null;
  pages_fetched?: number;
  raw_discovered?: number;
  unique_markets?: number;
  eligible_30d?: number;
  analysed?: number;
  directional?: number;
  funnel?: Record<string, unknown>;
  buckets?: ScanBucketCount[];
  selection_policy?: string;
  public_selection_limit?: number;
  model_version?: string;
}

export interface Opportunities {
  has_scan: boolean;
  scan_id?: string;
  window?: string;
  window_label?: string;
  selection_policy?: string;
  public_selection_limit?: number;
  freshness?: Freshness;
  shown?: number;
  total_directional?: number;
  eligible_markets?: number;
  rows: ScanSignalRow[];
  denominator?: string | null;
}

export interface ScanTrajectory {
  label: string;
  strength_change_prev: number | null;
  change_1h: number | null;
  consecutive_same_direction: number;
  first_detected: string | null;
  scans: number;
}

export interface ScanSignalRow {
  market_id: string;
  condition_id: string | null;
  event_id: string | null;
  token_id: string;
  market_question: string;
  outcome_name: string;
  bucket: string | null;
  bucket_label: string | null;
  close_time: string | null;
  time_remaining_hours: number | null;
  direction: string | null;
  signal_classification: string;
  strength: number;
  confidence: number;
  research_priority: number;
  rank_in_bucket: number | null;
  overall_rank_30d: number | null;
  public_top_ten: boolean;
  shadow_directional: boolean;
  n_families: number;
  evidence_families: string[];
  data_quality: string;
  trajectory: ScanTrajectory;
}

export interface ScanSignals {
  has_scan: boolean;
  scan_id?: string;
  bucket?: string | null;
  bucket_label?: string | null;
  scope?: string;
  eligible_in_bucket?: number;
  directional_in_bucket?: number;
  total_matching: number;
  shown?: number;
  rows: ScanSignalRow[];
  coverage_caption?: string;
}

export function getScanStatus(): Promise<ScanStatus> {
  return apiFetch<ScanStatus>("/api/scan/status");
}

export function getScanSignals(
  bucket: string,
  scope: string,
  limit = 10,
): Promise<ScanSignals> {
  return apiFetch<ScanSignals>("/api/scan/signals", { bucket, scope, limit });
}

export function getOpportunities(window = "all", limit = 20): Promise<Opportunities> {
  return apiFetch<Opportunities>("/api/scan/opportunities", { window, limit });
}

export interface MarketHistorySnapshot {
  captured_at: string;
  scan_id: string;
  strength: number;
  direction: string | null;
  research_priority: number;
  rank_in_bucket: number | null;
  bucket: string | null;
  midpoint: number | null;
  time_remaining_hours: number | null;
}

export interface MarketHistory {
  market_id: string;
  has_history: boolean;
  market_question?: string;
  outcome_name?: string;
  snapshots: MarketHistorySnapshot[];
  trajectory: (ScanTrajectory & {
    change_15m?: number | null;
    change_6h?: number | null;
    last_updated?: string | null;
    rank_change?: number | null;
    research_priority_change?: number | null;
    direction_reversed?: boolean;
  }) | null;
}

export function getMarketSignalHistory(marketId: string): Promise<MarketHistory> {
  return apiFetch<MarketHistory>(`/api/scan/market/${encodeURIComponent(marketId)}/history`);
}

export function getReplayCohorts(): Promise<ReplayCohortList> {
  return apiFetch<ReplayCohortList>("/api/research/replay/cohorts");
}

export function getReplayCohortResults(
  cohortId: number,
  horizon: string,
  scope: string,
  closing: string,
): Promise<ReplayResult> {
  return apiFetch<ReplayResult>(`/api/research/replay/cohort/${cohortId}`, {
    horizon,
    scope,
    closing,
  });
}

// -- Accounts ---------------------------------------------------------------------------
// These endpoints use the auth cookie, so every request must send credentials. fastapi-users
// login expects form-encoded data; everything else is JSON.

async function accountFetch<T>(
  path: string,
  init: RequestInit & { json?: unknown; form?: Record<string, string> } = {},
): Promise<T> {
  const { json, form, headers, ...rest } = init;
  const opts: RequestInit = {
    ...rest,
    credentials: "include",
    cache: "no-store",
    headers: { ...(headers ?? {}) },
  };
  if (json !== undefined) {
    opts.headers = { ...opts.headers, "Content-Type": "application/json" };
    opts.body = JSON.stringify(json);
  } else if (form !== undefined) {
    opts.headers = { ...opts.headers, "Content-Type": "application/x-www-form-urlencoded" };
    opts.body = new URLSearchParams(form).toString();
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, opts);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network request failed";
    throw new ApiError(`Unable to reach the Arepo API: ${message}`, 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = normalizeDetail(body.detail);
    } catch {
      // not JSON
    }
    throw new ApiError(detail || `Request failed with status ${res.status}`, res.status);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export function registerAccount(
  firstName: string,
  lastName: string,
  email: string,
  password: string,
): Promise<AccountUser> {
  return accountFetch<AccountUser>("/api/auth/register", {
    method: "POST",
    json: { first_name: firstName, last_name: lastName, email, password },
  });
}

export function loginAccount(email: string, password: string): Promise<void> {
  return accountFetch<void>("/api/auth/login", {
    method: "POST",
    form: { username: email, password },
  });
}

export function logoutAccount(): Promise<void> {
  return accountFetch<void>("/api/auth/logout", { method: "POST" });
}

export function verifyEmail(token: string): Promise<AccountUser> {
  return accountFetch<AccountUser>("/api/auth/verify", { method: "POST", json: { token } });
}

export function requestVerifyToken(email: string): Promise<void> {
  return accountFetch<void>("/api/auth/request-verify-token", {
    method: "POST",
    json: { email },
  });
}

export function forgotPassword(email: string): Promise<void> {
  return accountFetch<void>("/api/auth/forgot-password", { method: "POST", json: { email } });
}

export function resetPassword(token: string, password: string): Promise<void> {
  return accountFetch<void>("/api/auth/reset-password", {
    method: "POST",
    json: { token, password },
  });
}

export function getMe(): Promise<AccountUser> {
  return accountFetch<AccountUser>("/api/users/me");
}

export function getPreferences(): Promise<AlertPreferences> {
  return accountFetch<AlertPreferences>("/api/account/preferences");
}

export function updatePreferences(changes: AlertPreferencesUpdate): Promise<AlertPreferences> {
  return accountFetch<AlertPreferences>("/api/account/preferences", {
    method: "PATCH",
    json: changes,
  });
}

export function getSavedMarkets(): Promise<SavedMarket[]> {
  return accountFetch<SavedMarket[]>("/api/account/saved");
}

export function saveMarket(market_id: string, question: string): Promise<SavedMarket> {
  return accountFetch<SavedMarket>("/api/account/saved", {
    method: "POST",
    json: { market_id, question },
  });
}

export function unsaveMarket(market_id: string): Promise<void> {
  return accountFetch<void>(`/api/account/saved/${encodeURIComponent(market_id)}`, {
    method: "DELETE",
  });
}

export function getAlertHistory(): Promise<AlertDelivery[]> {
  return accountFetch<AlertDelivery[]>("/api/account/alerts");
}

export function getDigestHistory(limit = 20, offset = 0): Promise<DigestList> {
  return accountFetch<DigestList>(`/api/account/digests?limit=${limit}&offset=${offset}`);
}

export function getDigestDetail(id: number): Promise<DigestDetail> {
  return accountFetch<DigestDetail>(`/api/account/digests/${id}`);
}

export function unsubscribeDigest(token: string): Promise<{ ok: boolean }> {
  return accountFetch<{ ok: boolean }>("/api/account/digest/unsubscribe", {
    method: "POST",
    json: { token },
  });
}

export function deleteAccount(): Promise<void> {
  return accountFetch<void>("/api/account", { method: "DELETE" });
}
