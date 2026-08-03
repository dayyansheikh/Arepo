// Maps raw backend identifiers (SignalKind values, composite-anomaly component
// names, window strings) to the friendly, plain-English labels the product
// shows by default. Raw identifiers are technical detail: they may still
// appear, clearly separated, behind a "Show technical detail" disclosure, but
// never as the first thing a reader sees. See spec section 12 (Signal Lab).

import { titleCase } from "./format";

/** Friendly surface title for each SignalKind value (e.g. "composite_anomaly"). */
export const SIGNAL_KIND_LABELS: Record<string, string> = {
  composite_anomaly: "Unusual market activity",
  movement_zscore: "Unusual price move",
  volatility_spike: "Volatility spike",
  book_imbalance: "Order-book imbalance",
  spread_widening: "Spread widening",
  depth_shift: "Depth shift",
};

/**
 * The technical term for a signal kind, shown only in expanded/technical
 * detail (never as the card's surface title). Returns null when a kind has
 * no separate technical term worth surfacing.
 */
export const SIGNAL_KIND_TECHNICAL_TERMS: Record<string, string> = {
  composite_anomaly: "Composite anomaly score",
};

/** Friendly names for the raw composite-anomaly component identifiers. */
export const COMPONENT_LABELS: Record<string, string> = {
  unusual_return: "Unusual price move",
  volume_acceleration: "Faster trading activity",
  book_imbalance: "Order-book imbalance",
  spread_change: "Spread change",
  depth_change: "Available depth change",
};

const COMPONENT_NAME_PATTERN = new RegExp(
  `\\b(${Object.keys(COMPONENT_LABELS).join("|")})\\b`,
  "g"
);

/** The surface (always-visible) title for a signal, e.g. "Unusual market activity". */
export function friendlySignalTitle(kind: string): string {
  return SIGNAL_KIND_LABELS[kind] ?? titleCase(kind);
}

/** The technical term for a signal kind, for expanded/technical detail only. */
export function technicalSignalTerm(kind: string): string | null {
  return SIGNAL_KIND_TECHNICAL_TERMS[kind] ?? null;
}

/** The friendly name for a raw component identifier, e.g. "unusual_return". */
export function friendlyComponentName(name: string): string {
  return COMPONENT_LABELS[name] ?? titleCase(name);
}

/**
 * Replaces any raw component identifiers embedded in free text (e.g. a
 * "components: unusual_return, book_imbalance" fragment) with their friendly
 * names, so raw identifiers never leak into surface copy by accident.
 */
export function replaceComponentNames(text: string): string {
  return text.replace(COMPONENT_NAME_PATTERN, (match) => COMPONENT_LABELS[match] ?? match);
}

const OBS_WINDOW_PATTERN = /^(\d+)\s*obs\.?$/i;

/**
 * Turns a raw window string ("145 obs" or "1h") into the surface "Lookback"
 * label: "Lookback: 145 observations" or "Lookback: 1h".
 */
export function formatLookback(window: string): string {
  const trimmed = window.trim();
  const match = trimmed.match(OBS_WINDOW_PATTERN);
  if (match) {
    const count = Number(match[1]);
    const unit = count === 1 ? "observation" : "observations";
    return `Lookback: ${count.toLocaleString()} ${unit}`;
  }
  return `Lookback: ${trimmed}`;
}
