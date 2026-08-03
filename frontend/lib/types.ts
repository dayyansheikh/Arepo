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
  movement_1h: number | null;
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
