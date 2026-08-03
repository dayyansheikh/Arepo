import type {
  BacktestResponse,
  CohortDetail,
  CohortWeek,
  DataMode,
  DataStatus,
  MarketDetailResponse,
  MarketFacets,
  MarketsResponse,
  MetaResponse,
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

export function getMarket(id: string, mode: DataMode): Promise<MarketDetailResponse> {
  return apiFetch<MarketDetailResponse>(`/api/markets/${encodeURIComponent(id)}`, { mode });
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
