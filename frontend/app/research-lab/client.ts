// Fetch helpers for the research-lab surface. Same base-URL rule as lib/api.ts: production uses the
// first-party /api proxy, local development talks to the configured backend.
const API_BASE =
  process.env.NODE_ENV === "production"
    ? ""
    : process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export interface LabModel {
  model_id: string;
  spec: { feature: string; coef: number; target: string; form: string };
  registered_commit: string;
  experimental: boolean;
  validation_status: string;
}

export interface LabRow {
  market_id: string;
  mid: number | null;
  spread: number | null;
  chg_1h: number | null;
  dmid_hat: number;
  direction: "up" | "down" | null;
}

export type LatestForecasts =
  | { status: "unavailable"; reason?: string }
  | {
      status: "available";
      model: LabModel;
      capture: {
        capture_id: string;
        origin_receipt_min_utc: string;
        origin_receipt_max_utc: string;
      };
      n_eligible: number;
      top: LabRow[];
      top_note?: string;
      created_utc: string;
    };

export type Scores =
  | { status: "unavailable"; reason?: string }
  | { status: "available"; experiment: string; results: Record<string, unknown> };

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export const getLatestForecasts = () =>
  getJson<LatestForecasts>("/api/research-lab/forecasts/latest?top=25");
export const getForecastScores = () => getJson<Scores>("/api/research-lab/forecasts/scores");
