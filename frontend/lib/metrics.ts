// Single registry of the technical metrics Arepo surfaces. The MetricHelp
// tooltip and the Methodology page both read from this, so every term used in
// the product has a matching Methodology anchor (id) by construction. Copy is
// British English, plain first. Keep ids in sync with the anchored sections on
// /methodology.

export interface MetricDef {
  /** Anchor id on /methodology (also the tooltip's "Learn more" target). */
  id: string;
  /** Human label as shown in the UI. */
  term: string;
  /** One-sentence plain-English definition. */
  definition: string;
  /** One-sentence "how to read it". */
  interpretation: string;
}

export const METRICS = {
  "implied-probability": {
    id: "implied-probability",
    term: "Implied probability",
    definition:
      "The market price of an outcome, read as an approximate probability between 0 and 100%.",
    interpretation:
      "A price of 0.62 suggests the market collectively prices the outcome at roughly a 62% chance. It is a price, not a guarantee.",
  },
  "signal-strength": {
    id: "signal-strength",
    term: "Signal strength",
    definition:
      "A single 0 to 100 reading of how unusual a market's recent behaviour looks, blending price movement, spread and order-book imbalance.",
    interpretation:
      "Higher means more of these are lining up at once. It does not say which way the price will move, or that anything is wrong.",
  },
  confidence: {
    id: "confidence",
    term: "Confidence",
    definition:
      "How much to trust a reading: its data quality combined with how many independent lines of evidence agree. Shown as an estimate, capped below 100%.",
    interpretation:
      "Low confidence on a thin market means the numbers are more likely to be noisy, not that the market itself is untrustworthy. The Opportunity Board can read a little higher than Signal Lab for the same market because it also sees live trade flow, which adds an evidence family.",
  },
  "z-score": {
    id: "z-score",
    term: "Z-score",
    definition:
      "How many standard deviations the current value sits from its own recent rolling average.",
    interpretation:
      "Near zero is unremarkable; beyond about ±2 is worth a second look.",
  },
  "rolling-volatility": {
    id: "rolling-volatility",
    term: "Rolling volatility",
    definition:
      "The size of a market's recent price wobble, measured as the standard deviation of price over a rolling window.",
    interpretation:
      "Higher volatility means larger recent swings, so a given move is less surprising.",
  },
  spread: {
    id: "spread",
    term: "Spread",
    definition:
      "The gap between the best bid and the best ask, as a share of the midpoint price.",
    interpretation:
      "A narrow spread usually means a market is easy to trade in and out of; a wide one means the opposite.",
  },
  midpoint: {
    id: "midpoint",
    term: "Midpoint",
    definition: "The halfway price between the best bid and the best ask.",
    interpretation:
      "A neutral reference price when bid and ask disagree; used for spread and movement.",
  },
  "order-book-imbalance": {
    id: "order-book-imbalance",
    term: "Order-book imbalance",
    definition:
      "How lopsided the resting orders are between the bid side and the ask side, from −1 to +1.",
    interpretation:
      "Values near zero are balanced; a large magnitude means one side is much heavier right now.",
  },
  "near-mid-depth": {
    id: "near-mid-depth",
    term: "Near-mid depth",
    definition:
      "How much size is resting close to the midpoint price on the order book.",
    interpretation:
      "More near-mid depth means the market can absorb larger orders without the price moving much.",
  },
  "composite-anomaly": {
    id: "signal-strength",
    term: "Composite anomaly",
    definition:
      "The combined 0 to 100 signal that blends price-movement, spread and imbalance z-scores into one reading.",
    interpretation:
      "It flags unusual combinations for further reading. It is not proof of informed or insider activity.",
  },
  movement: {
    id: "movement",
    term: "Movement",
    definition:
      "How far the price has moved over a recent window, in probability points.",
    interpretation:
      "Read alongside volatility: a 3-point move is large in a calm market and small in a jumpy one.",
  },
  volume: {
    id: "volume",
    term: "Volume",
    definition: "The total value traded in a market.",
    interpretation:
      "Higher volume markets tend to have tighter, more informative prices.",
  },
  liquidity: {
    id: "liquidity",
    term: "Liquidity",
    definition:
      "An estimate of how much can be traded near the current price without moving it much, drawn from order-book depth.",
    interpretation:
      "Higher liquidity means a market can absorb larger orders with less price impact.",
  },
  "hit-rate": {
    id: "hit-rate",
    term: "Hit rate",
    definition:
      "In Replay, the share of fired signals that were followed by a real price move of the chosen size within the chosen horizon.",
    interpretation:
      "It measures directional follow-through only, not profit. A hit is not a profitable trade.",
  },
  "false-positive-rate": {
    id: "false-positive-rate",
    term: "False-positive rate",
    definition:
      "In Replay, the share of fired signals that were not followed by the required move within the horizon.",
    interpretation:
      "Lower is better, but a lower rate usually comes with fewer signals overall.",
  },
  "average-forward-move": {
    id: "average-forward-move",
    term: "Average forward move",
    definition:
      "The mean price change after a signal fires, over the evaluation horizon, in the signalled direction.",
    interpretation:
      "A small or negative average means signals were not, on average, followed by a meaningful move.",
  },
  threshold: {
    id: "threshold",
    term: "Threshold",
    definition:
      "The minimum signal strength at which a reading counts as a fired signal.",
    interpretation:
      "Raising it gives fewer, higher-confidence signals; lowering it surfaces more candidates with more false positives.",
  },
  "evaluation-horizon": {
    id: "evaluation-horizon",
    term: "Evaluation horizon",
    definition:
      "How far ahead, in frames, Replay looks to check whether a signal was followed by a move.",
    interpretation:
      "A longer horizon gives a move more time to appear but blurs cause and effect.",
  },
  "sample-size": {
    id: "sample-size",
    term: "Sample size",
    definition:
      "The number of signals evaluated in a Replay run.",
    interpretation:
      "Small samples make hit and false-positive rates noisy; read them as rough, not precise.",
  },
  "unusual-market-activity": {
    id: "signal-strength",
    term: "Unusual market activity",
    definition:
      "A screening signal that fires when a market's recent price, spread, volume and order-book behaviour look statistically unusual compared with its own history.",
    interpretation:
      "A higher score means more of these are lining up at once. It is a prompt to look closer, not proof of insider activity.",
  },
  "data-coverage": {
    id: "confidence",
    term: "Data coverage",
    definition:
      "How much clean history, spread and order-book depth a reading is based on.",
    interpretation:
      "Good means a solid base of observations. Limited or poor means less history or a thinner book, so read the numbers as more approximate.",
  },
  lookback: {
    id: "signal-strength",
    term: "Lookback",
    definition:
      "The recent window of observations, or span of time, that a reading is calculated over.",
    interpretation:
      "A longer lookback smooths out short-lived blips; a shorter one reacts faster but is noisier.",
  },
} as const satisfies Record<string, MetricDef>;

export type MetricId = keyof typeof METRICS;

/** Ordered list for building the Methodology page. */
export const METRIC_LIST: MetricDef[] = Object.values(METRICS);

export function methodologyAnchor(id: string): string {
  return `/methodology#${id}`;
}
