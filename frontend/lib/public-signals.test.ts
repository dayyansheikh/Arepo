import { describe, expect, it } from "vitest";
import {
  bandIsAvailable,
  embargoText,
  formatScore,
  formatStrength,
  formatUtc,
  pageState,
  snapshotTime,
  type PublicSignals,
} from "./public-signals";

const base: PublicSignals = {
  schema: "arepo-public-signals-v1",
  status: "ok",
  server_time: "2026-11-08T12:30:00+00:00",
  snapshot_received_at: "2026-11-08T12:05:00+00:00",
  champion: { model_id: "m1", family: "lr" },
  feed: {
    origin_utc: "2026-11-08T12:00:00+00:00",
    stale: false,
    top_up: [],
    top_down: [],
    track_record: null,
    days_scored: 3,
    bands: [],
  },
  leaderboard: [],
};

describe("pageState", () => {
  it("is live for a fresh ok feed", () => expect(pageState(base)).toBe("live"));
  it("is stale when the API says so, by status or by the feed flag", () => {
    expect(pageState({ ...base, status: "stale" })).toBe("stale");
    expect(pageState({ ...base, feed: { ...base.feed!, stale: true } })).toBe("stale");
  });
  it("is partial without a feed or with a hidden champion", () => {
    expect(pageState({ ...base, status: "no_feed", feed: null })).toBe("partial");
    expect(pageState({ ...base, status: "champion_hidden", feed: null })).toBe("partial");
  });
  it("is unavailable when there is no snapshot", () =>
    expect(pageState({ ...base, status: "unavailable", feed: null })).toBe("unavailable"));
});

describe("time and number formatting", () => {
  it("renders UTC text", () => expect(formatUtc("2026-11-08T12:00:00+00:00")).toBe("2026-11-08 12:00 UTC"));
  it("returns null for bad input", () => {
    expect(formatUtc(null)).toBeNull();
    expect(formatUtc("nope")).toBeNull();
  });
  it("falls back to the received time", () =>
    expect(snapshotTime({ ...base, feed: null })).toBe("2026-11-08 12:05 UTC"));
  it("signs strength to 3 decimals with no percent", () => {
    expect(formatStrength(0.3123)).toBe("+0.312");
    expect(formatStrength(-0.104)).toBe("-0.104");
    expect(formatStrength(null)).toBe("–");
    expect(formatStrength(0.3)).not.toContain("%");
  });
  it("formats scores", () => {
    expect(formatScore(0.69315)).toBe("0.693");
    expect(formatScore(undefined)).toBe("–");
  });
});

describe("embargo and bands", () => {
  it("shows only the date for an embargoed row", () => {
    expect(embargoText({ model_id: "x", family: "f", role: "challenger", hidden_until: "2026-12-01" })).toBe(
      "hidden until 2026-12-01",
    );
    expect(embargoText({ model_id: "x", family: "f", role: "challenger", days: 5 })).toBeNull();
  });
  it("treats only status ok as available", () => {
    expect(bandIsAvailable({ band: "weak", n: 1, events: 1, status: "ok" })).toBe(true);
    expect(bandIsAvailable({ band: "weak", n: 1, events: 1, status: "unavailable" })).toBe(false);
  });
});
