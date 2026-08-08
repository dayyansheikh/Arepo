// Presentation helpers for Opportunity Board cards. These turn the backend's numeric scores
// into the plain-English interpretation the product leads with, so a reader never sees a bare
// number without being told what it means for their next step.

export interface Band {
  label: string;
  tone: string; // tailwind text colour class
  meaning: string;
}

// Research Priority is a 0-100 ranking of how urgently a market is worth investigating relative
// to others right now. It is NOT expected return or probability of profit.
export function priorityBand(score: number): Band {
  if (score >= 60)
    return {
      label: "High",
      tone: "text-arepo-accentActive",
      meaning: "Worth investigating first, ahead of most other markets right now.",
    };
  if (score >= 35)
    return {
      label: "Medium",
      tone: "text-arepo-ink",
      meaning: "Worth a look when you have time; several stronger candidates may exist.",
    };
  return {
    label: "Low",
    tone: "text-arepo-muted",
    meaning: "A weak lead. Read it, but do not prioritise it over higher-scoring markets.",
  };
}

// Confidence is a pure data-quality measure (history length, spread, depth), independent of how
// large the anomaly is.
export function confidenceBand(confidence: number): Band {
  const pct = Math.round(confidence * 100);
  if (confidence >= 0.75)
    return { label: "High", tone: "text-arepo-pos", meaning: `Rich data (${pct}%).` };
  if (confidence >= 0.45)
    return { label: "Limited", tone: "text-arepo-ink2", meaning: `Partial data (${pct}%).` };
  return { label: "Low", tone: "text-arepo-warnText", meaning: `Thin data (${pct}%).` };
}

// Plain "why it matters" per evidence family, shown in a tag's popover so the reader learns the
// point of a tag without leaving the market page.
export const FAMILY_WHY: Record<string, string> = {
  price: "Price behaviour that stands out from this market's own recent history.",
  trade_flow: "The pattern of recent trades (size, direction, clustering) looks unusual.",
  order_book: "The resting buy/sell orders are lopsided or unusually thin.",
  wallet_concentration: "A small number of wallets account for a large share of recent flow.",
  timing: "The timing of recent trades relative to the market's close stands out.",
};

export const FAMILY_LABEL: Record<string, string> = {
  price: "price behaviour",
  trade_flow: "trade flow",
  order_book: "order book",
  wallet_concentration: "wallet concentration",
  timing: "trade timing",
};

// The directional call wording now lives in lib/directional.ts (directionLabel) so every surface —
// Signal Lab, Opportunities, Market Detail and Replay — describes the same signal identically.
