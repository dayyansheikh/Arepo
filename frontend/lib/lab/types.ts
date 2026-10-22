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
  embargoed_until?: string | null;
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

/** One challenger's status under the promotion rule. Every number may be null. */
export interface SePromotionCandidate {
  model_id?: string;
  pass?: boolean;
  /** False when the model may never be promoted (dated register on the host); absent reads as eligible. */
  eligible?: boolean;
  ineligible_since?: string | null;
  days?: number | null;
  age_days?: number | null;
  days_to_min?: number | null;
  checks?: Record<string, boolean | null>;
  gain?: number | null;
  lo_event?: number | null;
  lo_twoway?: number | null;
  se_event?: number | null;
  se_day?: number | null;
  n_days?: number | null;
  embargoed_until?: string | null;
}

export interface SePromotionStatus {
  rule?: string;
  at?: string;
  K?: number | null;
  level?: number | null;
  min_days?: number | null;
  promote?: string | null;
  reason?: string | null;
  label?: string;
  candidates?: SePromotionCandidate[];
}

/** Family attribution of one LightGBM fit: development diagnostic (mean |SHAP|), never a score. */
export interface SeAttribution {
  model_id?: string;
  fit_time?: string;
  target?: string;
  method?: string;
  block?: unknown;
  rows?: number;
  /** Family -> mean |SHAP|. Families under an active embargo are absent here and named in `hidden`. */
  families?: Record<string, unknown>;
  hidden?: string[];
  label?: string;
  embargoed_until?: string | null;
}

export interface SeEmbargoToken {
  token?: string;
  until?: string;
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
  /** Promotion-rule status (se-promotion-v2); optional, parsed defensively. */
  promotion?: SePromotionStatus | null;
  attribution?: SeAttribution[];
  embargo_tokens?: SeEmbargoToken[];
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
  /** First sentences of the result text, sent when there is no DONE line (older sessions). */
  plain?: string;
  /** The session's result text (without the DONE line), truncated on the Mac. */
  summary?: string;
  summary_truncated?: boolean;
  log_state?: "ok" | "partial" | "empty" | "missing" | "unreadable" | string;
}

export interface ClaudeInstance {
  name?: string;
  /** Command target on the Mac: the instance's home directory name ("autopilot", "autopilot-signal"). */
  key?: string;
  /** A launchd job exists for it, so "Start a session now" can work. */
  startable?: boolean;
  /** Latest assistant text of the running session (sanitised, ≤ 300 chars). */
  current?: { text?: string | null; at?: string | null } | null;
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

/** API-equivalent Claude cost of the whole project, computed on the Mac from transcripts. */
export interface CostsBlock {
  generated_at?: string;
  basis?: string;
  pricing_source?: string;
  total_usd?: number;
  last_7d_usd?: number;
  today_usd?: number;
  messages?: number;
  tokens?: { input?: number; output?: number; cache_write?: number; cache_read?: number };
  first_at?: string | null;
  last_at?: string | null;
  by_day?: Array<{ date: string; usd: number }>;
  by_model?: Array<{ model: string; label?: string; usd: number; messages?: number }>;
  by_source?: Array<{
    key: string;
    label?: string;
    kind?: "interactive" | "autopilot" | "other_headless" | string;
    usd: number;
    main_usd?: number;
    subagent_usd?: number;
    sessions?: number;
    messages?: number;
  }>;
  unknown_models?: Array<{ model: string; messages?: number; tokens?: number }>;
  assumptions?: string[];
  infra?: Array<{ name: string; gbp_month?: number; note?: string }>;
  infra_note?: string;
  error?: string;
}

export interface MacPayload {
  schema?: string;
  source?: "mac";
  generated_at?: string;
  autopilot?: AutopilotBlock;
  activity?: ClaudeActivity;
  costs?: CostsBlock;
}

export interface SnapshotEnvelope<P> {
  received_at?: string;
  payload?: P | string | null;
}

export type CommandTarget = "queue" | "autopilot";
/** Any command target, including further autopilot instances ("autopilot-signal"). */
export type AnyCommandTarget = CommandTarget | `autopilot-${string}`;
export type CommandAction = "pause" | "resume" | "start";
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

export type MessageStatus = "pending" | "fetched" | "delivered" | "read" | "failed" | "cancelled";

/** Owner → Claude message (stored server-side, written to the instance's INBOX.md by the Mac). */
export interface LabMessage {
  id: number;
  target: string;
  body: string;
  status: MessageStatus | string;
  created_at?: string | null;
  fetched_at?: string | null;
  delivered_at?: string | null;
  read_at?: string | null;
  finished_at?: string | null;
  result?: string | null;
}

export interface LabDashboardResponse {
  host?: SnapshotEnvelope<HostPayload> | null;
  mac?: SnapshotEnvelope<MacPayload> | null;
  commands?: LabCommand[];
  messages?: LabMessage[];
  limits?: { message_max_chars?: number; messages_per_day?: number; messages_last_24h?: number };
  server_time?: string;
}
