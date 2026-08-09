import { describe, expect, it } from "vitest";
import { ALL_CATEGORY, CATEGORY_FILTERS, categoryTestId } from "@/lib/categories";

describe("shared category filters", () => {
  it("defaults to All and never exposes internal Other", () => {
    expect(CATEGORY_FILTERS[0]).toBe(ALL_CATEGORY);
    expect(CATEGORY_FILTERS).not.toContain("Other");
    expect(CATEGORY_FILTERS).toHaveLength(9);
  });

  it("creates stable accessible test ids for slash labels", () => {
    expect(categoryTestId("Geopolitics / War")).toBe("geopolitics-war");
  });
});
