import { describe, it, expect } from "vitest";
import { directionLabel, DIRECTION_TONE_CLASS } from "@/lib/directional";

describe("directionLabel — the one shared directional-call vocabulary", () => {
  it("names the real outcome and never fabricates YES/NO from direction", () => {
    expect(directionLabel("up", "Yes")).toEqual({
      text: "Upward on Yes",
      glyph: "↑",
      tone: "up",
    });
    // The old bug rendered direction=down as "NO ↓" regardless of the outcome. It must use the
    // actual outcome instead — here the selected outcome is "Yes" even though the direction is down.
    expect(directionLabel("down", "Yes")).toEqual({
      text: "Downward on Yes",
      glyph: "↓",
      tone: "down",
    });
    expect(directionLabel("down", "No").text).toBe("Downward on No");
  });

  it("falls back to a neutral phrase (no outcome word) when there is no clear direction", () => {
    expect(directionLabel(null, "No")).toEqual({
      text: "No clear direction",
      glyph: "→",
      tone: "none",
    });
    expect(directionLabel(undefined, null).tone).toBe("none");
  });

  it("uses a placeholder when the outcome is missing/blank rather than an empty word", () => {
    expect(directionLabel("up", null).text).toBe("Upward on this outcome");
    expect(directionLabel("up", "  ").text).toBe("Upward on this outcome");
  });

  it("maps tone to the green/red/grey colour classes used on every surface", () => {
    expect(DIRECTION_TONE_CLASS.up).toBe("text-arepo-pos");
    expect(DIRECTION_TONE_CLASS.down).toBe("text-arepo-neg");
    expect(DIRECTION_TONE_CLASS.none).toBe("text-arepo-muted");
  });
});
