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

/** Host-side 48 h tally of queue attempts (events themselves stay in `queue.recent`). */
export interface QueueTally {
  window_h?: number;
  since?: string;
  attempts?: number;
  outcomes?: Record<string, number>;
  distinct_jobs?: number;
  runtime_h?: number;
  first_at?: string | null;
  last_at?: string | null;
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
  activity?: { queue?: QueueTally };
  /** Champion/challenger signal engine (schema `se-dash-v1`); optional, see lib/lab/signal-engine.ts. */
  signal_engine?: SignalEngineBlock | null;
}

// ---- signal engine (`se-dash-v1`, built by backend/astrolabe/signal_engine/dashboard.py) -----
// Every field is optional: the block is parsed defensively in lib/lab/signal-engine.ts.

/** One leaderboard row. An embargoed row carries only `model_id` + `embargoed_until`. */
export interface SeRow {
  model_id?: string;
  role?: string;
  target?: string;
  window_days?: number;
  n?: number;
  log_loss?: number | null;
  brier?: number | null;
  cal_slope?: number | null;
  cal_intercept?: number | null;
  auc?: number | null;
  coverage?: number | null;
  days?: number;
  /** Mean paired log-loss gain over the champion (nats; positive = better than the champion). */
  gain?: number | null;
  gain_lo?: number | null;
  gain_hi?: number | null;
  days_positive?: number;
  n_days?: number;
  n_clusters?: number;
  embargoed_until?: string | null;
}

export interface SeModel {
  model_id?: string;
  family?: string;
  learner?: string;
  status?: string;
  embargoed_until?: string | null;
  embargo_tests?: string[] | null;
}

export interface SeFamilyGain {
  date?: string;
  model_id?: string;
  family?: string;
  gain?: number | null;
  lo?: number | null;
  hi?: number | null;
}

export interface SePromotion {
  event?: string;
  at?: string;
  champion?: string;
  previous?: string;
  rule?: string;
  evidence?: { gain?: { mean?: number | null; lo?: number | null; hi?: number | null } | null; level?: number; K?: number };
}

export interface SignalEngineBlock {
  schema?: string;
  generated_at?: string;
  engine_version?: string;
  primary_target?: string;
  champion?: { model_id?: string; spec_sha256?: string; family?: string };
  models?: SeModel[];
  note?: string;
  last_refit?: { at?: string; models?: number; targets_ok?: number };
  last_prediction?: { capture_id?: string; at?: string; models?: number };
  prospective?: { generated_at?: string; days_scored?: number; status?: string; rows?: SeRow[] };
  family_gains?: SeFamilyGain[];
  development?: { label?: string; generated_at?: string; test_days?: number | null; rows?: SeRow[] };
  promotions?: SePromotion[];
  /** Set by the host: the engine's dashboard is more than 2 days old. */
  stale?: boolean;
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

/** One headless Claude autopilot session (`claude -p --output-format json`), sanitised on the Mac. */
export interface ClaudeSession {
  started_at?: string | null;
  ended_at?: string | null;
  runtime_s?: number;
  outcome?: string | null;
  test?: boolean;
  note?: string;
  cost_usd?: number;
  turns?: number;
  duration_ms?: number;
  duration_api_ms?: number;
  subtype?: string;
  terminal_reason?: string;
  stop_reason?: string;
  is_error?: boolean;
  /** Text of the closing `AUTOPILOT_DONE <summary>` line. */
  done?: string;
  /** The session's result text (without the DONE line), truncated on the Mac. */
  summary?: string;
  summary_truncated?: boolean;
  log_state?: "ok" | "partial" | "empty" | "missing" | "unreadable" | string;
}

export interface ClaudeInstance {
  name?: string;
  home?: string;
  paused?: boolean;
  pause_reason?: string | null;
  session_alive?: boolean;
  started_at?: string | null;
  last_outcome?: string | null;
  last_finished_at?: string | null;
  next_allowed?: string | null;
  sessions_total?: number;
  /** Newest first. */
  sessions?: ClaudeSession[];
  error?: string;
}

export interface CommitItem {
  at?: string | null;
  sha?: string;
  subject?: string;
}

export interface ClaudeActivity {
  generated_at?: string;
  instances?: ClaudeInstance[];
  commits?: CommitItem[];
  branch?: string;
  trimmed?: string;
  error?: string;
}

export interface MacPayload {
  schema?: string;
  source?: "mac";
  generated_at?: string;
  autopilot?: AutopilotBlock;
  activity?: ClaudeActivity;
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
