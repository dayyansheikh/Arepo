// Core API types for Astrolabe. Mirrors the backend contract exactly.

export type DataMode = "live" | "cached" | "replay";

export interface SourceHealth {
  name: string;
  state: string;
  last_success: string | null;
  last_error: string | null;
  latency_ms: number | null;
}

export interface DataStatus {
  mode: DataMode;
  rest: SourceHealth;
  websocket: SourceHealth;
  last_update: string | null;
  data_age_seconds: number | null;
  degradation_reason: string | null;
  generated_at: string;
}

export interface MetaResponse {
  app: string;
  environment: string;
  default_mode: DataMode;
  modes: string[];
  disclaimer: string;
}

export interface MarketCard {
  id: string;
  question: string;
  slug: string;
  category: string | null;
  sport: string | null;
  competition: string | null;
  status: string;
  tags: string[];
  volume: number | null;
  volume_24hr: number | null;
  liquidity: number | null;
  end_date: string | null;
  top_probability: number | null;
  top_outcome: string | null;
  spread: number | null;
  abs_movement: number | null;
  signal_strength: number | null;
}

export interface OutcomeView {
  name: string;
  token_id: string;
  implied_probability: number | null;
  implied_probability_normalized: number | null;
  best_bid: number | null;
  best_ask: number | null;
  midpoint: number | null;
  spread: number | null;
  relative_spread: number | null;
  book_imbalance: number | null;
  near_mid_depth: number | null;
  volume: number | null;
  rolling_volatility: number | null;
  recent_movement: number | null;
  zscore: number | null;
  signal_strength: number | null;
  data_quality: "good" | "limited" | "poor";
  confidence: number;
}

export interface PricePoint {
  t: string;
  p: number;
}

export interface SignalComponent {
  name: string;
  raw_value: number | null;
  normalized_value: number | null;
  weight: number | null;
  explanation: string;
}

export interface Signal {
  kind: string;
  token_id: string;
  market_id: string;
  market_question?: string | null;
  outcome_name?: string | null;
  value: number | null;
  strength: number;
  direction: "up" | "down" | null;
  detected: string;
  method: string;
  why_it_matters: string;
  limitations: string;
  components: SignalComponent[];
  data_quality: "good" | "limited" | "poor";
  confidence: number;
  window: string | null;
  computed_at: string;
}

export interface MarketDetail {
  id: string;
  question: string;
  slug: string;
  description: string | null;
  category: string | null;
  status: string;
  tags: string[];
  volume: number | null;
  volume_24hr: number | null;
  liquidity: number | null;
  tick_size: number | null;
  end_date: string | null;
  outcomes: OutcomeView[];
  price_history: Record<string, PricePoint[]>;
  signals: Signal[];
  limitations: string;
  data_source: string;
  chart_range: string;
  available_ranges: string[];
}

export interface OverviewResponse {
  top_movers: MarketCard[];
  most_active: MarketCard[];
  highest_volume: MarketCard[];
  widest_spreads: MarketCard[];
  recent_signals: Signal[];
  status: DataStatus;
}

export interface MarketsResponse {
  markets: MarketCard[];
  total: number;
  limit: number;
  offset: number;
  status: DataStatus;
}

/** Distinct, sorted filter values built dynamically from real normalised
 * market data. Arrays are empty when that dimension isn't present in the
 * current mode's data; `statuses` may include a lowercase "unknown" entry
 * that callers should omit from user-facing Status controls. */
export interface MarketFacets {
  categories: string[];
  sports: string[];
  competitions: string[];
  statuses: string[];
}

export interface MarketDetailResponse {
  market: MarketDetail;
  status: DataStatus;
}

export interface SignalsResponse {
  signals: Signal[];
  status: DataStatus;
}

export interface BacktestEvent {
  market_id: string;
  token_id: string;
  frame: string;
  strength: number;
  zscore: number | null;
  direction: "up" | "down" | null;
  entry_price: number | null;
  forward_price: number | null;
  forward_move: number | null;
  followed_through: boolean | null;
}

// dataset_meta is backend-defined and open-ended; kept as unknown to avoid
// leaking `any` while still allowing safe narrowing where consumed.
export interface BacktestResponse {
  strength_threshold: number;
  move_threshold: number;
  horizon: string;
  zscore_window: number;
  min_history: number;
  sample_size: number;
  evaluated: number;
  missing_observations: number;
  hit_rate: number | null;
  false_positive_rate: number | null;
  avg_forward_move_directional: number | null;
  avg_abs_forward_move: number | null;
  events: BacktestEvent[];
  assumptions: string[];
  limitations: string[];
  dataset_meta: unknown;
}

export interface ReplayScenarioResponse {
  meta: unknown;
  markets: MarketCard[];
}

// -- Prospective cohort evaluation ------------------------------------------------------

export interface CohortWeek {
  iso_year: number;
  iso_week: number;
  label: string;
  week_start: string;
  cutoff_at: string;
  frozen: boolean;
  frozen_at: string | null;
  provenance_class: "prospective" | "reconstructed" | "synthetic";
  actual_size: number;
  target_size: number;
}

export interface ForwardObservation {
  horizon: string;
  observed_at: string;
  price: number | null;
}

export interface ResolutionOut {
  resolved: boolean;
  resolved_outcome: string | null;
  resolved_token_id: string | null;
  resolved_at: string | null;
  source: string | null;
}

export interface EntryEvaluation {
  movement_horizon: string | null;
  raw_prob_movement: number | null;
  movement_correct: boolean | null;
  resolved: boolean;
  resolution_correct: boolean | null;
  pending: boolean;
  hypothetical_value: number | null;
}

export interface CohortEntry {
  rank: number;
  market_id: string;
  token_id: string;
  condition_id: string | null;
  event_id: string | null;
  market_question: string;
  outcome_name: string;
  direction: "up" | "down" | null;
  signal_timestamp: string;
  expected_close: string | null;
  strength: number;
  confidence: number;
  data_quality: string;
  value: number | null;
  entry_price: number | null;
  best_bid: number | null;
  best_ask: number | null;
  midpoint: number | null;
  spread: number | null;
  volume: number | null;
  near_mid_depth: number | null;
  lookback_size: number | null;
  component_scores: Array<{
    name: string;
    raw_value: number | null;
    normalized_value: number | null;
    weight: number | null;
  }>;
  forward: ForwardObservation[];
  resolution: ResolutionOut | null;
  evaluation: EntryEvaluation | null;
}

export interface CohortSummary {
  week: CohortWeek;
  calculation_version: string;
  note: string | null;
  selected: number;
  moved_expected: number;
  moved_against: number;
  movement_pending: number;
  movement_horizon: string;
  resolved_correct: number;
  resolved_incorrect: number;
  unresolved: number;
  plain_summary: string;
}

export interface PortfolioPosition {
  rank: number;
  market_question: string;
  outcome_name: string;
  status: "completed" | "open" | "pending";
  entry_price: number | null;
  fill: number | null;
  exit_price: number | null;
  value: number;
  pnl: number;
}

export interface PortfolioSummary {
  stake_per_signal: number;
  fee_rate: number;
  spread_assumption: string;
  total_allocated: number;
  realised_value: number;
  unrealised_value: number;
  pending_value: number;
  completed_return: number;
  completed_positions: number;
  pending_positions: number;
  positions: PortfolioPosition[];
}

export interface CohortDetail {
  summary: CohortSummary;
  entries: CohortEntry[];
  portfolio: PortfolioSummary;
}

export interface ProvenanceInfo {
  calculation_version: string;
  first_prospective_week: string | null;
  prospective_weeks: number;
  reconstructed_weeks: number;
  synthetic_weeks: number;
  note: string;
}

// -- Historical reconstructed retrospective ---------------------------------------------

export interface HistoricalForward {
  horizon: string;
  price: number | null;
  movement: number | null;
}

export interface HistoricalEntry {
  rank: number;
  market_id: string;
  token_id: string;
  market_question: string;
  outcome_name: string;
  direction: "up" | "down" | null;
  momentum_direction: "up" | "down" | null;
  strength: number;
  confidence: number;
  research_priority: number;
  data_quality: string;
  entry_price: number;
  close_at: string | null;
  time_remaining_hours: number | null;
  lookback_points: number;
  components: Array<{ name: string; normalized_value: number | null; weight: number | null }>;
  forward: HistoricalForward[];
  final_price: number | null;
  final_movement: number | null;
  direction_correct_24h: boolean | null;
}

export interface BaselineScore {
  name: string;
  evaluated: number;
  correct: number;
  incorrect: number;
  hit_rate: number | null;
  ci95: [number, number];
  verdict: string;
}

export interface BaselineComparison {
  sample_size: number;
  verdict: string;
  arepo: BaselineScore;
  baselines: Record<string, BaselineScore>;
}

export interface HistoricalScreen {
  provenance_class: string;
  as_of: string;
  top_n: number;
  universe_considered: number;
  eligible: number;
  selected: number;
  moved_expected_24h: number;
  moved_against_24h: number;
  pending_24h: number;
  candidates_total: number;
  had_price_data: number;
  directional: number;
  sample_verdict: string;
  baseline_comparison: BaselineComparison | null;
  entries: HistoricalEntry[];
  plain_summary: string;
  assumptions: string[];
  limitations: string[];
}

// -- Opportunity Board ------------------------------------------------------------------

export interface OpportunityTag {
  label: string;
  family: string;
  explanation: string;
  methodology_anchor: string;
  data_quality: string;
  timestamp: string;
}

export interface OpportunityCard {
  market_id: string;
  token_id: string;
  question: string;
  outcome: string | null;
  direction: "up" | "down" | null;
  directional: boolean;
  hypothesis: string;
  probability: number | null;
  research_priority: number;
  signal_strength: number;
  confidence: number;
  families: string[];
  n_families: number;
  high_priority: boolean;
  tags: OpportunityTag[];
  explanation: string;
  liquidity: number | null;
  liquidity_quality: string;
  relative_spread: number | null;
  time_remaining_hours: number | null;
  end_date: string | null;
  data_quality: string;
  data_mode: string;
}

export type BoardView = "directional" | "strongest" | "inconclusive" | "all";

export interface OpportunityBoard {
  generated_at: string;
  data_mode: string;
  calculation_version: string;
  count: number;
  universe_considered: number;
  screened_count: number;
  directional_count: number;
  view: BoardView;
  cards: OpportunityCard[];
  note: string;
}

// -- Full-universe market search --------------------------------------------------------

export interface MarketSearchResponse {
  query: string;
  expanded_terms: string[];
  markets: MarketCard[];
  total: number;
  limit: number;
  offset: number;
  provenance: string;
  note: string;
}

// -- Accounts ---------------------------------------------------------------------------

export interface AccountUser {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  auth_provider: string;
  consent_at: string | null;
}

export interface AlertPreferences {
  email_enabled: boolean;
  immediate_exceptional: boolean;
  daily_digest: boolean;
  weekly_summary: boolean;
  min_research_priority: number;
  min_confidence: number;
  categories: string[];
  short_term_only: boolean;
  max_hours_to_close: number | null;
  paused: boolean;
  unsubscribed: boolean;
  updated_at: string | null;
}

export type AlertPreferencesUpdate = Partial<Omit<AlertPreferences, "updated_at">>;

export interface SavedMarket {
  market_id: string;
  question: string;
  created_at: string;
}

export interface AlertDelivery {
  market_id: string;
  token_id: string;
  subject: string;
  status: string;
  detail: string;
  at: string;
}
