// Types for the private owner-only Lab dashboard (docs/lab/LAB_DASHBOARD_SPEC.md, schema
// `arepo-lab-v1`). Every field except schema/source/generated_at is optional: the UI must
// tolerate any of them being absent, so everything here is typed as possibly missing.

export const STAGES = [
  "idea",
  "designed",
  "screened",
  "replicated",
  "live_test",
  "cost_check",
  "confirmed",
] as const;
export type Stage = (typeof STAGES)[number];

export type Verdict =
  | "not_detected"
  | "not_testable"
  | "replicated"
  | "advanced"
  | "failed_costs"
  | "pending";

export interface FunnelStage {
  stage: Stage | string;
  label?: string;
  count?: number;
  /** e.g. "hypotheses" (idea/designed) or "registry entries" (screened onward). */
  unit?: string;
  help?: string;
}

export interface Experiment {
  id: string;
  title?: string;
  plain?: string;
  batch?: string;
  family?: string;
  stage?: Stage | string;
  status?: string;
  verdict?: Verdict | string | null;
  effect?: { label?: string; note?: string } | null;
  next?: string | null;
  next_date?: string | null;
  candidate?: boolean;
  /** Stages actually passed through, in order. */
  reached?: string[];
  /** Per-stage result; a stage absent here has not been attempted. */
  stage_results?: Record<string, StageResult | string>;
}

export type StageResult = "pass" | "fail" | "pending";

export interface LiveTest {
  id: string;
  title?: string;
  collected?: number;
  target?: number | null;
  unit?: string;
  analysis_after?: string | null;
  /** Optional collection start, used for time progress when there is no count target. */
  started_at?: string | null;
  outcomes_collected?: number | null;
}

export interface FeatureWeight {
  feature: string;
  family?: string;
  /** Drop-one log-loss change in nats (family level); may be negative. */
  weight: number;
  /** false: from a different run, not comparable with the others. */
  comparable?: boolean;
}

export interface Contrast {
  label: string;
  value: number;
  lo?: number | null;
  hi?: number | null;
  unit?: string;
  replicated?: boolean;
}

export interface MlBlock {
  status?: "parked" | "running" | "done" | "waiting" | string;
  status_note?: string;
  learned?: string[];
  feature_weights?: FeatureWeight[];
  feature_weights_note?: string;
  contrasts?: Contrast[];
}

export interface QueueJob {
  id?: string;
  title?: string;
  started_at?: string;
  lane?: string;
  at?: string;
  outcome?: string;
  runtime_s?: number;
  /** Identical consecutive outcomes collapsed into this one entry. */
  repeats?: number;
  status?: string;
  not_before?: string | null;
}

export interface QueueBlock {
  updated_at?: string;
  paused?: boolean;
  counts?: Record<string, number>;
  running?: QueueJob[];
  recent?: QueueJob[];
  upcoming?: QueueJob[];
}

export interface InfraBlock {
  disk_free_gb?: number;
  disk_total_gb?: number;
  mem_available_mb?: number;
  mem_total_mb?: number;
  collector_last_ok?: string;
  collector_ok?: boolean;
  data_gb?: number;
  data_cap_gb?: number;
  second_server?: { status?: string; attempts?: number; last_try?: string };
  history?: Array<{ t: string; disk_free_gb?: number; mem_available_mb?: number }>;
}

export interface HostPayload {
  schema?: string;
  source?: "host";
  generated_at?: string;
  headline?: {
    confirmed_edges?: number;
    tests_run?: number;
    hypotheses?: number;
    batches?: number;
    live_tests?: number;
    jobs_done?: number;
  };
  funnel?: FunnelStage[];
  experiments?: Experiment[];
  live_tests?: LiveTest[];
  ml?: MlBlock;
  tests_over_time?: Array<{ date: string; cumulative: number }>;
  queue?: QueueBlock;
  infra?: InfraBlock;
}

export interface AutopilotBlock {
  paused?: boolean;
  pause_reason?: string | null;
  session_alive?: boolean;
  started_at?: string;
  last_outcome?: string;
  next_allowed?: string | null;
  recent?: Array<{ at?: string; outcome?: string; runtime_s?: number }>;
}

export interface MacPayload {
  schema?: string;
  source?: "mac";
  generated_at?: string;
  autopilot?: AutopilotBlock;
}

export interface SnapshotEnvelope<P> {
  received_at?: string;
  payload?: P | string | null;
}

export type CommandTarget = "queue" | "autopilot";
export type CommandAction = "pause" | "resume";
export type CommandStatus = "pending" | "delivered" | "done" | "failed" | "expired";

export interface LabCommand {
  id: number;
  target: CommandTarget | string;
  action: CommandAction | string;
  status: CommandStatus | string;
  created_at?: string;
  delivered_at?: string | null;
  finished_at?: string | null;
  result?: string | null;
}

export interface LabDashboardResponse {
  host?: SnapshotEnvelope<HostPayload> | null;
  mac?: SnapshotEnvelope<MacPayload> | null;
  commands?: LabCommand[];
  server_time?: string;
}
