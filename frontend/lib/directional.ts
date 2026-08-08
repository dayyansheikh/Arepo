// The ONE directional-view gate, used identically by Market Detail (ModelView) and Signal Lab so
// the three surfaces agree (spec §4, §13). Mirrors the backend rule (opportunity/hypothesis.py +
// scoring._price_family): a directional view needs a resolved direction AND genuine evidence,
// which is either at least moderate composite strength OR a materially present price-behaviour
// feature (the price evidence family).
import type { Signal } from "./types";

export const STRENGTH_MODERATE = 0.4;
export const STRENGTH_STRONG = 0.7;
const PRICE_FEATURES = new Set(["unusual_return", "movement_abnormality", "volatility_regime"]);
const PRICE_CONTEXT_FLOOR = 0.05;

export function priceFamilyFires(sig: Signal): boolean {
  return sig.components.some(
    (c) =>
      PRICE_FEATURES.has(c.name) &&
      c.normalized_value !== null &&
      c.normalized_value > PRICE_CONTEXT_FLOOR,
  );
}

export function strengthWord(s: number): "early" | "moderate" | "strong" {
  if (s >= STRENGTH_STRONG) return "strong";
  if (s >= STRENGTH_MODERATE) return "moderate";
  return "early";
}

// ---------------------------------------------------------------------------------------
// One canonical way to describe Arepo's directional call, used identically by every surface
// (Signal Lab, Opportunities, Market Detail, Replay) so the same signal is never worded two ways.
// The call is ALWAYS "<arrow> <Upward|Downward> on <outcome>" — never a bare "YES ↑"/"NO ↓", which
// wrongly conflated the repricing direction with the outcome name. `outcome` is the real selected
// outcome (e.g. "Yes", "No", a team); direction is which way that outcome has been repricing.
export type DirectionTone = "up" | "down" | "none";

export interface DirectionLabel {
  text: string;
  glyph: string;
  tone: DirectionTone;
}

// Tone -> colour class, one map used by every surface: upward green, downward red, flat/none grey.
// Apply to the direction label only, never the whole card. (The label always carries the outcome
// and a tooltip stating up/down is not "good/bad", so the colour is a directional cue, not a verdict.)
export const DIRECTION_TONE_CLASS: Record<DirectionTone, string> = {
  up: "text-arepo-pos",
  down: "text-arepo-neg",
  none: "text-arepo-muted",
};

export function directionLabel(
  direction: string | null | undefined,
  outcome?: string | null,
): DirectionLabel {
  const name = outcome && outcome.trim() ? outcome : "this outcome";
  if (direction === "up") return { text: `Upward on ${name}`, glyph: "↑", tone: "up" };
  if (direction === "down") return { text: `Downward on ${name}`, glyph: "↓", tone: "down" };
  return { text: "No clear direction", glyph: "→", tone: "none" };
}

export interface DirectionalVerdict {
  qualifies: boolean;
  reason: string;
}

/** Does this signal qualify for a directional model view, and why / why not?
 *
 * This mirrors the backend `has_directional_view` (opportunity/hypothesis.py) EXACTLY: a resolved
 * direction AND either at least one independent evidence family firing OR at least moderate
 * composite strength. It uses the server-computed `n_families` so Signal Lab, Market Detail and
 * the Opportunity Board apply one identical gate (spec §4, §13, §17). When `n_families` is absent
 * (older payloads) it falls back to detecting the price family locally so nothing regresses. */
export function directionalVerdict(sig: Signal): DirectionalVerdict {
  const hasDirection = sig.direction === "up" || sig.direction === "down";
  if (!hasDirection) {
    return { qualifies: false, reason: "no resolved up/down direction (the market is flat)" };
  }
  if (sig.strength >= STRENGTH_MODERATE) {
    return { qualifies: true, reason: `${strengthWord(sig.strength)} composite strength` };
  }
  const families = sig.n_families ?? (priceFamilyFires(sig) ? 1 : 0);
  if (families >= 1) {
    return {
      qualifies: true,
      reason:
        families === 1
          ? "one independent evidence family is present"
          : `${families} independent evidence families agree`,
    };
  }
  return {
    qualifies: false,
    reason: "the signal is too weak and no evidence family is materially present",
  };
}
