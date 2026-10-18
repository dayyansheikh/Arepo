import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  actionForResult,
  loadLabDashboard,
  postLabCommand,
  SIGNIN_REDIRECT,
} from "./api";
import { fixtureAllowed } from "./fixture-guard";
import { buildLabFixture } from "./fixture";
import {
  buildPipeline,
  countdownLabel,
  daysUntil,
  EMPTY_FILTER,
  facetCounts,
  filterExperiments,
  hideEffect,
  latestCommand,
  parsePayload,
  placeCandidates,
  rankCandidates,
  stageTrail,
  timeProgress,
  snapshotFreshness,
  verdictMeta,
} from "./model";
import type { Experiment, HostPayload, LabCommand } from "./types";

function res(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("dashboard loading", () => {
  it("sends the session cookie and maps 401 to the sign-in redirect", async () => {
    const fetchImpl = vi.fn(async () => res(401, { detail: "Unauthorized" }));
    const result = await loadLabDashboard(fetchImpl);
    expect(result).toEqual({ kind: "unauthorized" });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/api\/lab\/dashboard$/);
    expect(init.credentials).toBe("include");
    expect(init.cache).toBe("no-store");
    expect(actionForResult(result)).toEqual({ type: "redirect", to: "/signin?next=/lab" });
    expect(SIGNIN_REDIRECT).toBe("/signin?next=/lab");
  });

  it("maps 404 (signed in, not the owner) to not-found", async () => {
    const result = await loadLabDashboard(async () => res(404, { detail: "Not Found" }));
    expect(result).toEqual({ kind: "not_found" });
    expect(actionForResult(result)).toEqual({ type: "not_found" });
  });

  it("returns data on 200 and a calm error on network failure", async () => {
    const ok = await loadLabDashboard(async () => res(200, { host: null, mac: null, commands: [] }));
    expect(ok).toEqual({ kind: "ok", data: { host: null, mac: null, commands: [] } });
    const down = await loadLabDashboard(async () => {
      throw new TypeError("fetch failed");
    });
    expect(down.kind).toBe("error");
    const action = actionForResult(down);
    expect(action.type).toBe("error");
  });

  it("posts commands as JSON with credentials and explains 429", async () => {
    const fetchImpl = vi.fn(async () =>
      res(201, { id: 9, target: "queue", action: "pause", status: "pending" }),
    );
    const out = await postLabCommand("queue", "pause", fetchImpl);
    expect(out.ok).toBe(true);
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(String(init.body))).toEqual({ target: "queue", action: "pause" });
    const limited = await postLabCommand("autopilot", "resume", async () => res(429, {}));
    expect(limited).toMatchObject({ ok: false, status: 429 });
  });
});

describe("fixture guard", () => {
  it("never allows the fixture in a production build", () => {
    expect(fixtureAllowed("production", "?fixture=1")).toBe(false);
    expect(fixtureAllowed("production", "fixture=1&x=2")).toBe(false);
  });

  it("requires an explicit ?fixture=1 outside production", () => {
    expect(fixtureAllowed("development", "?fixture=1")).toBe(true);
    expect(fixtureAllowed("development", "")).toBe(false);
    expect(fixtureAllowed("development", "?fixture=true")).toBe(false);
    expect(fixtureAllowed(undefined, null)).toBe(false);
  });

  it("keeps the fixture import behind a literal NODE_ENV check so production drops it", () => {
    const src = readFileSync(resolve(__dirname, "use-lab-dashboard.ts"), "utf8");
    const guard = src.indexOf('if (process.env.NODE_ENV !== "production")');
    const importAt = src.indexOf('import("./fixture")');
    expect(guard).toBeGreaterThan(-1);
    expect(importAt).toBeGreaterThan(guard);
    // The fixture module is only ever imported dynamically from that guarded branch.
    expect(src.match(/["']\.\/fixture["']/g)?.length).toBe(1);
  });

  it("fixture shows the honest zero", () => {
    const fx = buildLabFixture(Date.parse("2026-10-18T12:00:00Z"));
    const host = parsePayload<HostPayload>(fx.host);
    expect(host?.headline?.confirmed_edges).toBe(0);
  });
});

describe("freshness", () => {
  const server = "2026-10-18T12:00:00Z";
  const fetched = Date.parse("2026-10-18T09:00:00Z"); // client clock deliberately wrong

  it("measures age on the server clock plus time since fetch", () => {
    const f = snapshotFreshness("2026-10-18T11:50:00Z", server, fetched, fetched + 60_000);
    expect(f.state).toBe("fresh");
    expect(f.ageSeconds).toBe(660);
  });

  it("goes stale after 30 minutes, including while the tab waits", () => {
    expect(snapshotFreshness("2026-10-18T11:20:00Z", server, fetched, fetched).state).toBe("stale");
    expect(
      snapshotFreshness("2026-10-18T11:50:00Z", server, fetched, fetched + 21 * 60_000).state,
    ).toBe("stale");
  });

  it("reports a missing snapshot as missing, not fresh", () => {
    expect(snapshotFreshness(undefined, server, fetched, fetched).state).toBe("missing");
    expect(snapshotFreshness("not a date", server, fetched, fetched).state).toBe("missing");
  });
});

const EXPS: Experiment[] = [
  { id: "E009", title: "Kalshi lead", stage: "live_test", status: "collecting", verdict: "pending", candidate: true, batch: "E", family: "cross_venue" },
  { id: "CB7-O", title: "Order flow", stage: "cost_check", verdict: "failed_costs", candidate: true, batch: "CB7", family: "flow", effect: { label: "+0.36c" } },
  { id: "C-TTE", title: "Near-close model gain", stage: "replicated", verdict: "replicated", candidate: true, batch: "CB9", family: "time" },
  { id: "CB9-V", title: "Volatility regime", stage: "screened", verdict: "not_detected", batch: "CB9", plain: "Calm to volatile switches" },
  { id: "CB10-S", title: "Sports line moves", stage: "screened", verdict: "not_testable", batch: "CB10" },
  { id: "CB12-N", title: "Novelty", stage: "idea", verdict: null, batch: "CB12" },
  { id: "X1", title: "Odd stage", stage: "mystery", candidate: true },
];

describe("pipeline placement", () => {
  it("puts each candidate in the stage it reached and ignores unknown stages", () => {
    const placed = placeCandidates(EXPS);
    expect(placed.live_test.map((e) => e.id)).toEqual(["E009"]);
    expect(placed.cost_check.map((e) => e.id)).toEqual(["CB7-O"]);
    expect(placed.replicated.map((e) => e.id)).toEqual(["C-TTE"]);
    expect(placed.screened).toEqual([]);
    expect(Object.values(placed).flat().some((e) => e.id === "X1")).toBe(false);
  });

  it("builds 7 stages, keeps unknown counts unknown and uses the headline confirmed count", () => {
    const stages = buildPipeline({
      headline: { confirmed_edges: 0 },
      funnel: [
        { stage: "idea", count: 117 },
        { stage: "screened", count: 41 },
      ],
      experiments: EXPS,
    });
    expect(stages).toHaveLength(7);
    expect(stages.map((s) => s.count)).toEqual([117, null, 41, null, null, null, 0]);
    expect(stages[4].candidates[0].id).toBe("E009");
    expect(stages[0].label).toBe("Ideas");
  });

  it("tolerates a completely absent snapshot", () => {
    const stages = buildPipeline(null);
    expect(stages.every((s) => s.count === null && s.candidates.length === 0)).toBe(true);
  });

  it("keeps non-monotone counts and units exactly as reported", () => {
    const stages = buildPipeline({
      funnel: [
        { stage: "screened", count: 26, unit: "registry entries" },
        { stage: "replicated", count: 6 },
        { stage: "live_test", count: 6 },
        { stage: "cost_check", count: 6 },
      ],
    });
    expect(stages.slice(2, 6).map((s) => s.count)).toEqual([26, 6, 6, 6]);
    expect(stages[2].unit).toBe("registry entries");
    expect(stages[3].unit).toBeNull();
  });
});

describe("stage trail and candidate ranking", () => {
  it("uses stage_results when present, marking a failed gate", () => {
    const trail = stageTrail({
      id: "CB7-O",
      stage: "cost_check",
      reached: ["idea", "designed", "screened", "replicated", "cost_check"],
      stage_results: { idea: "pass", designed: "pass", screened: "pass", replicated: "pass", cost_check: "fail" },
    });
    expect(trail.map((t) => t.mark)).toEqual(["pass", "pass", "pass", "pass", "none", "fail", "none"]);
  });

  it("infers a trail from stage and verdict when results are absent", () => {
    expect(stageTrail(EXPS[0]).map((t) => t.mark)).toEqual(["pass", "pass", "pass", "pass", "pending", "none", "none"]);
    expect(stageTrail(EXPS[1])[5].mark).toBe("fail");
  });

  it("ranks failed candidates after live ones even when they reached a later stage", () => {
    expect(rankCandidates(EXPS).map((e) => e.id)).toEqual(["E009", "C-TTE", "X1", "CB7-O"]);
  });

  it("measures time progress towards an analysis date", () => {
    const now = Date.parse("2026-10-18T00:00:00Z");
    expect(timeProgress("2026-10-08", "2026-10-28", now)).toBeCloseTo(0.5);
    expect(timeProgress(null, "2026-10-28", now)).toBeNull();
  });
});

describe("experiment filters", () => {
  it("filters by stage, verdict, batch and multi-word search", () => {
    expect(filterExperiments(EXPS, { ...EMPTY_FILTER, stages: ["screened"] }).map((e) => e.id)).toEqual([
      "CB9-V",
      "CB10-S",
    ]);
    expect(filterExperiments(EXPS, { ...EMPTY_FILTER, verdicts: ["none"] }).map((e) => e.id)).toEqual([
      "CB12-N",
      "X1",
    ]);
    expect(filterExperiments(EXPS, { ...EMPTY_FILTER, batches: ["CB9"], query: "calm" }).map((e) => e.id)).toEqual([
      "CB9-V",
    ]);
    expect(filterExperiments(EXPS, { ...EMPTY_FILTER, query: "kalshi lead" }).map((e) => e.id)).toEqual(["E009"]);
    expect(filterExperiments(undefined, EMPTY_FILTER)).toEqual([]);
  });

  it("counts facets in a fixed order", () => {
    const f = facetCounts(EXPS, (e) => e.stage, ["idea", "screened", "replicated"]);
    expect(f[0]).toEqual({ value: "idea", count: 1 });
    expect(f[1]).toEqual({ value: "screened", count: 2 });
  });

  it("keeps not-detected, not-testable and fails-costs visibly distinct", () => {
    const labels = ["not_detected", "not_testable", "failed_costs"].map((v) => verdictMeta(v));
    expect(new Set(labels.map((l) => l.label)).size).toBe(3);
    expect(new Set(labels.map((l) => l.tone)).size).toBe(3);
  });

  it("never exposes an interim effect for a live prospective test", () => {
    expect(hideEffect(EXPS[0])).toBe(true);
    expect(hideEffect(EXPS[1])).toBe(false);
  });
});

describe("dates and commands", () => {
  const now = Date.parse("2026-10-18T15:00:00Z");
  it("counts down calendar days", () => {
    expect(daysUntil("2026-11-03", now)).toBe(16);
    expect(countdownLabel(daysUntil("2026-10-19", now))).toBe("tomorrow");
    expect(countdownLabel(daysUntil("2026-10-01", now))).toBe("due");
    expect(daysUntil(null, now)).toBeNull();
  });

  it("finds the newest command per target", () => {
    const cmds: LabCommand[] = [
      { id: 1, target: "queue", action: "pause", status: "done", created_at: "2026-10-18T10:00:00Z" },
      { id: 3, target: "queue", action: "resume", status: "pending", created_at: "2026-10-18T12:00:00Z" },
      { id: 2, target: "autopilot", action: "pause", status: "delivered", created_at: "2026-10-18T11:00:00Z" },
    ];
    expect(latestCommand(cmds, "queue")?.id).toBe(3);
    expect(latestCommand(cmds, "autopilot")?.id).toBe(2);
    expect(latestCommand(undefined, "queue")).toBeNull();
  });

  it("parses payloads stored as JSON text", () => {
    expect(parsePayload({ payload: '{"source":"host"}' })).toEqual({ source: "host" });
    expect(parsePayload({ payload: "{bad" })).toBeNull();
    expect(parsePayload(null)).toBeNull();
  });
});
