import { describe, expect, it } from "vitest";
import { safeNextPath } from "./safe-next";

describe("safeNextPath", () => {
  it("accepts same-site paths", () => {
    expect(safeNextPath("/lab")).toBe("/lab");
    expect(safeNextPath("/account?tab=preferences")).toBe("/account?tab=preferences");
  });
  it("rejects open-redirect shapes", () => {
    for (const bad of ["https://evil.com", "//evil.com", "/\\evil.com", "javascript:alert(1)", "lab", "/a\nb"]) {
      expect(safeNextPath(bad)).toBe("/account");
    }
    expect(safeNextPath(null)).toBe("/account");
  });
});
