import { describe, expect, it } from "vitest";
import { digestEvaluationLabel, initialsForUser } from "./account";

describe("initialsForUser", () => {
  it("uses first and last names", () => {
    expect(initialsForUser({ first_name: "Dayyan", last_name: "Sheikh", email: "d@x.test" }))
      .toBe("DS");
  });

  it("has stable legacy-user fallbacks", () => {
    expect(initialsForUser({ first_name: "Ada", last_name: null, email: "a@x.test" })).toBe("AD");
    expect(initialsForUser({ first_name: null, last_name: null, email: "legacy@x.test" })).toBe("L");
    expect(initialsForUser({ first_name: null, last_name: null, email: "" })).toBe("A");
  });
});

it("keeps prospective outcome states restrained and truthful", () => {
  expect(digestEvaluationLabel({
    horizon: "6h", state: "pending", unavailable_reason: null, resolved: false,
    resolved_outcome: null, resolution_correct: null,
  })).toBe("Pending");
  expect(digestEvaluationLabel({
    horizon: "6h", state: "closed_before_horizon", unavailable_reason: "closed before horizon",
    resolved: false, resolved_outcome: null, resolution_correct: null,
  })).toBe("Closed before horizon");
});
