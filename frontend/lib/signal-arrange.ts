// Pure sort + directional-status filter for Signal Lab (spec §6). Kept pure so the ordering and
// filtering are unit-testable without a DOM. Direction status uses the shared directional gate.
import type { Signal } from "./types";
import { directionalVerdict } from "./directional";

export type SignalStatus = "all" | "directional" | "observational";
export type SignalSort =
  | "strength-desc"
  | "strength-asc"
  | "confidence-desc"
  | "confidence-asc"
  | "recent";

function signalTime(s: Signal): number {
  return new Date(s.detected ?? s.computed_at ?? 0).getTime();
}

export function arrangeSignals(
  signals: Signal[],
  status: SignalStatus,
  sort: SignalSort,
): Signal[] {
  let out = [...signals];
  if (status === "directional") out = out.filter((s) => directionalVerdict(s).qualifies);
  else if (status === "observational") out = out.filter((s) => !directionalVerdict(s).qualifies);

  switch (sort) {
    case "strength-asc":
      out.sort((a, b) => a.strength - b.strength);
      break;
    case "confidence-desc":
      out.sort(
        (a, b) =>
          (b.reliability_confidence ?? b.confidence) - (a.reliability_confidence ?? a.confidence),
      );
      break;
    case "confidence-asc":
      out.sort(
        (a, b) =>
          (a.reliability_confidence ?? a.confidence) - (b.reliability_confidence ?? b.confidence),
      );
      break;
    case "recent":
      out.sort((a, b) => signalTime(b) - signalTime(a));
      break;
    default:
      out.sort((a, b) => b.strength - a.strength);
  }
  return out;
}
