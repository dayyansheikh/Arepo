import { describe, expect, it } from "vitest";
import { applyParams, nextSearch, readParam } from "./url-state";

describe("URL filter state (spec §10)", () => {
  it("round-trips a value: set then read restores it", () => {
    const s = nextSearch("", "category", "Politics");
    expect(readParam(s, "category")).toBe("Politics");
  });

  it("round-trips the full category label used by Opportunities and Replay", () => {
    const s = nextSearch("", "category", "Geopolitics / War", "All");
    expect(readParam(s, "category", "All")).toBe("Geopolitics / War");
    expect(s).toContain("Geopolitics+%2F+War");
  });

  it("setting the default (or empty) removes the key, keeping URLs clean", () => {
    let s = nextSearch("", "view", "strongest", "directional");
    expect(readParam(s, "view", "directional")).toBe("strongest");
    s = nextSearch(s, "view", "directional", "directional"); // back to default
    expect(s).toBe("");
    expect(readParam(s, "view", "directional")).toBe("directional");
  });

  it("independent filters do not clobber each other", () => {
    let s = nextSearch("", "category", "Sports");
    s = nextSearch(s, "status", "open");
    s = nextSearch(s, "sort", "ending", "volume");
    expect(readParam(s, "category")).toBe("Sports");
    expect(readParam(s, "status")).toBe("open");
    expect(readParam(s, "sort", "volume")).toBe("ending");
  });

  it("restores the exact state from a shared/copied URL query string", () => {
    // Simulate a link a user copied and reopened.
    const shared = "category=Crypto&close=24h&strength=high&q=fed";
    expect(readParam(shared, "category")).toBe("Crypto");
    expect(readParam(shared, "close", "any")).toBe("24h");
    expect(readParam(shared, "strength", "any")).toBe("high");
    expect(readParam(shared, "q")).toBe("fed");
  });

  it("Back/Forward: two URL snapshots read back independently", () => {
    const before = nextSearch("", "close", "7d", "any"); // user picked 7d
    const after = nextSearch(before, "close", "24h", "any"); // then 24h
    // Pressing Back returns to `before`; the value there is still 7d.
    expect(readParam(before, "close", "any")).toBe("7d");
    expect(readParam(after, "close", "any")).toBe("24h");
  });

  it("clearing all filters via applyParams empties the query", () => {
    const s = "category=Sports&status=open&q=abc";
    const cleared = applyParams(s, [
      ["category", ""],
      ["status", ""],
      ["q", ""],
    ]);
    expect(cleared).toBe("");
  });
});
