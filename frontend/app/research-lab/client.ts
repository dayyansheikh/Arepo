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

export interface LabMetric {
  name: string;
  metric: string;
  value: number;
  ci: [number, number] | null;
  n: number | string | null;
  baseline: number | string | null;
  verdict: number | string | null;
}

export type ExperimentResult =
  | { status: "no_result_file_defined" }
  | { status: "pending" | "unavailable"; reason?: string }
  | {
      status: "available";
      fields: Record<string, string | number>;
      metrics: LabMetric[];
    };

export interface LabExperiment {
  id: string;
  status: "registered" | "complete" | "unknown";
  status_raw: string;
  question: string;
  result_summary: string;
  result: ExperimentResult;
}

export type Experiments =
  | { status: "unavailable"; reason?: string }
  | { status: "available"; experiments: LabExperiment[]; source: string };

export interface LabTrial {
  trial_id: string | null;
  utc: string | null;
  dataset: string | null;
  kind: string | null;
  label: string | null;
  preset: string | null;
  run_id: string | null;
  status: string | null;
  n_models_summarised: number | null;
}

export type Trials =
  | { status: "unavailable"; reason?: string }
  | { status: "available"; total: number; malformed_lines: number; trials: LabTrial[] };

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export const getLatestForecasts = () =>
  getJson<LatestForecasts>("/api/research-lab/forecasts/latest?top=25");
export const getForecastScores = () => getJson<Scores>("/api/research-lab/forecasts/scores");
export const getExperiments = () => getJson<Experiments>("/api/research-lab/experiments");
export const getTrials = () => getJson<Trials>("/api/research-lab/trials?limit=5");
