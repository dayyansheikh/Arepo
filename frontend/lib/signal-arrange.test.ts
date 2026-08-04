import { describe, expect, it } from "vitest";
import { arrangeSignals } from "./signal-arrange";
import type { Signal } from "./types";

function sig(over: Partial<Signal>): Signal {
  return {
    kind: "composite_anomaly",
    token_id: "t",
    market_id: "m",
    value: null,
    strength: 0.5,
    direction: "up",
    detected: "2026-08-01T00:00:00Z",
    method: "",
    why_it_matters: "",
    limitations: "",
    components: [{ name: "unusual_return", raw_value: 1, normalized_value: 0.5, weight: 1 }],
    data_quality: "good",
    confidence: 0.5,
    window: null,
    computed_at: "2026-08-01T00:00:00Z",
    ...over,
  } as Signal;
}

describe("Signal Lab arrange (spec §6)", () => {
  const a = sig({ token_id: "a", strength: 0.8, confidence: 0.4, detected: "2026-08-03T00:00:00Z" });
  const b = sig({ token_id: "b", strength: 0.3, confidence: 0.9, detected: "2026-08-01T00:00:00Z" });
  const flat = sig({ token_id: "f", strength: 0.1, direction: null, components: [] }); // observational

  it("sorts by strength high to low (default)", () => {
    const r = arrangeSignals([b, a], "all", "strength-desc");
    expect(r.map((s) => s.token_id)).toEqual(["a", "b"]);
  });

  it("sorts by strength low to high", () => {
    const r = arrangeSignals([a, b], "all", "strength-asc");
    expect(r.map((s) => s.token_id)).toEqual(["b", "a"]);
  });

  it("sorts by confidence high to low", () => {
    const r = arrangeSignals([a, b], "all", "confidence-desc");
    expect(r.map((s) => s.token_id)).toEqual(["b", "a"]);
  });

  it("sorts by most recent", () => {
    const r = arrangeSignals([b, a], "all", "recent");
    expect(r[0].token_id).toBe("a"); // more recent detected
  });

  it("filters to directional views only", () => {
    const r = arrangeSignals([a, b, flat], "directional", "strength-desc");
    expect(r.every((s) => s.direction === "up" || s.direction === "down")).toBe(true);
    expect(r.map((s) => s.token_id)).not.toContain("f");
  });

  it("filters to observational or inconclusive only", () => {
    const r = arrangeSignals([a, b, flat], "observational", "strength-desc");
    expect(r.map((s) => s.token_id)).toContain("f");
    expect(r.map((s) => s.token_id)).not.toContain("a");
  });

  it("does not mutate the input array", () => {
    const input = [b, a];
    arrangeSignals(input, "all", "strength-desc");
    expect(input.map((s) => s.token_id)).toEqual(["b", "a"]);
  });
});
