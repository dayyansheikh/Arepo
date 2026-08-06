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

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.notFound = status === 404;
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

async function apiFetch<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const url = `${API_BASE}${path}${buildQuery(params)}`;
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
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

export function getStatus(mode: DataMode): Promise<DataStatus> {
  return apiFetch<DataStatus>("/api/status", { mode });
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
  model_version: string;
  cohort_counts_by_cadence: Record<string, number>;
  total_frozen_markets: number;
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
  late_cohorts: number;
  excessively_late_cohorts_excluded: number;
  latest_run: {
    scheduled_for: string | null;
    frozen_at: string | null;
    evaluation_origin_at: string | null;
    lateness_seconds: number;
    late: boolean;
    excessively_late: boolean;
    universe_size: number;
    degraded: boolean;
  } | null;
  microstructure_snapshots: number;
  collector_recent: boolean;
  calibration: { available: boolean; resolved_sample: number; minimum_required: number; message: string };
  edge: {
    edge_supported: boolean;
    message: string;
    criteria: Record<string, boolean>;
    evaluable_sample_24h: number;
  };
  note: string;
}

export function getResearchStatus(): Promise<ResearchStatus> {
  return apiFetch<ResearchStatus>("/api/research/status");
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

export function registerAccount(email: string, password: string): Promise<AccountUser> {
  return accountFetch<AccountUser>("/api/auth/register", {
    method: "POST",
    json: { email, password },
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

export function deleteAccount(): Promise<void> {
  return accountFetch<void>("/api/account", { method: "DELETE" });
}
