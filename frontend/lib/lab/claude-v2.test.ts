import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { cancelLabMessage, postLabMessage } from "./api";
import {
  claudeInstances,
  cleanReason,
  costDays,
  digest,
  failureKind,
  failuresSentence,
  firstSentences,
  groupLabel,
  instanceTargets,
  latestFor,
  logEntries,
  messageProgress,
  rightNow,
  sessionRows,
  sessionSummary,
  sourceLabel,
  startState,
  usdLabel,
} from "./claude";
import { buildLabFixture } from "./fixture";
import { parsePayload } from "./model";
import type { ClaudeInstance, ClaudeSession, LabCommand, MacPayload } from "./types";

const NOW = Date.parse("2026-10-21T12:00:00Z");
const H = 3_600_000;
const at = (hAgo: number) => new Date(NOW - hAgo * H).toISOString();
const NET = "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)";

function res(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("plain-English summaries", () => {
  it("prefers the AUTOPILOT_DONE line, then the Mac's plain line, then first sentences", () => {
    expect(sessionSummary({ done: "Shipped CB18.", plain: "x", summary: "y" })).toBe("Shipped CB18.");
    expect(sessionSummary({ plain: "Plain line." })).toBe("Plain line.");
    expect(sessionSummary({ summary: "## Summary\n**Shipped** the census. It ran `q1` overnight. More." })).toBe(
      "Shipped the census. It ran q1 overnight.",
    );
    expect(sessionSummary({ summary: "**Results**\n- Two checks passed." })).toBe("Two checks passed.");
    expect(sessionSummary({ summary: "## Only a heading" })).toBe("Only a heading");
    expect(sessionSummary({})).toBeNull();
    expect(firstSentences("word ".repeat(200))!.length).toBeLessThanOrEqual(280);
  });
});

describe("failed-run grouping", () => {
  it("classifies network, usage-limit, auth, error and interrupted sessions; DONE always wins", () => {
    expect(failureKind({ outcome: "ok", summary: NET })).toBe("network");
    expect(failureKind({ outcome: "error", summary: NET })).toBe("network");
    expect(failureKind({ outcome: "usage_limit", summary: "You've hit your session limit · resets 11pm" })).toBe("usage_limit");
    expect(failureKind({ outcome: "ok", summary: "You've hit your weekly limit" })).toBe("usage_limit");
    expect(failureKind({ outcome: "auth_error" })).toBe("auth");
    expect(failureKind({ outcome: "error", summary: "boom" })).toBe("error");
    expect(failureKind({ outcome: "interrupted" })).toBe("interrupted");
    expect(failureKind({ outcome: "ok", done: "Did real work despite an API Error earlier", summary: NET })).toBeNull();
    expect(failureKind({ outcome: "timeout" })).toBeNull();
    expect(failureKind({ outcome: "ok", summary: "Finished the census." })).toBeNull();
  });

  it("folds consecutive failures of one kind into one expandable group with a time span", () => {
    const sessions: ClaudeSession[] = [
      { outcome: "ok", done: "Newest real work", ended_at: at(1), started_at: at(2) },
      ...Array.from({ length: 8 }, (_, i) => ({ outcome: "error", summary: NET, started_at: at(3 + i * 0.5 + 0.02), ended_at: at(3 + i * 0.5) })),
      { outcome: "usage_limit", summary: "You've hit your session limit", ended_at: at(8), started_at: at(9) },
      { outcome: "ok", done: "Older real work", ended_at: at(10), started_at: at(11) },
    ];
    const inst: ClaudeInstance = { name: "experiments", sessions };
    const entries = logEntries(sessionRows([inst]));
    expect(entries.map((e) => e.kind)).toEqual(["session", "group", "group", "session"]);
    const g = entries[1];
    if (g.kind !== "group") throw new Error("expected group");
    expect(g.rows).toHaveLength(8);
    expect(g.failure).toBe("network");
    const label = groupLabel(g);
    expect(label).toMatch(/^8 sessions failed: couldn't reach the API \(/);
    expect(label).toMatch(/\d\d:\d\d–\d\d:\d\d\)$/);
    const u = entries[2];
    if (u.kind !== "group") throw new Error("expected group");
    expect(groupLabel(u)).toMatch(/^1 session stopped at the usage limit/);
  });

  it("does not merge failures across instances or across a meaningful session", () => {
    const a: ClaudeInstance = { name: "a", sessions: [{ outcome: "error", summary: NET, ended_at: at(1) }, { outcome: "error", summary: NET, ended_at: at(3) }] };
    const b: ClaudeInstance = { name: "b", sessions: [{ outcome: "error", summary: NET, ended_at: at(2) }] };
    const entries = logEntries(sessionRows([a, b]));
    expect(entries.map((e) => (e.kind === "group" ? `${e.instance}:${e.rows.length}` : "s"))).toEqual(["a:1", "b:1", "a:1"]);
  });
});

describe("right now", () => {
  it("speaks plain English for working, paused, waiting and idle instances", () => {
    const working = rightNow(
      { name: "experiments", session_alive: true, started_at: at(1.2), current: { text: "Applying review fixes.", at: at(0.1) } },
      NOW,
    );
    expect(working.title).toBe("Experiments autopilot");
    expect(working.status).toBe("working for 1 h 12 min");
    expect(working.said).toBe("Applying review fixes.");
    expect(working.saidLabel).toBe("now saying");
    const paused = rightNow({ name: "signal", paused: true, pause_reason: "2026-10-20T23:43:20Z paused until v1 is merged" }, NOW);
    expect(paused.status).toBe("paused (paused until v1 is merged)");
    const waiting = rightNow({ name: "signal", next_allowed: at(-1) }, NOW);
    expect(waiting.status).toMatch(/^waiting for the usage reset at \d\d:\d\d \(in 1 h\)$/);
    const idle = rightNow(
      { name: "x", sessions: [{ outcome: "error", summary: NET, ended_at: at(1) }, { outcome: "ok", done: "Real summary", ended_at: at(2) }] },
      NOW,
    );
    expect(idle.key).toBe("idle");
    expect(idle.said).toBe("Real summary");
    expect(cleanReason("2026-10-20T23:43:20Z manual pause")).toBe("manual pause");
    expect(rightNow({ name: "x", paused: true, pause_reason: "2026-10-20T23:43:20Z manual pause" }, NOW).status).toBe("paused by hand");
  });

  it("start now is only offered when the instance is idle and has a launchd job", () => {
    expect(startState({ key: "autopilot", startable: true }, NOW).ok).toBe(true);
    expect(startState({ key: "autopilot", startable: true, paused: true }, NOW)).toMatchObject({ ok: false, why: "Paused: resume it first." });
    expect(startState({ key: "autopilot", startable: true, session_alive: true }, NOW).ok).toBe(false);
    expect(startState({ key: "autopilot", startable: true, next_allowed: at(-1) }, NOW).why).toMatch(/^Usage limit/);
    expect(startState({ key: "autopilot", startable: false }, NOW).ok).toBe(false);
    expect(startState({ startable: true }, NOW).ok).toBe(false);
  });
});

describe("digest", () => {
  it("counts sessions in the window, lists only meaningful summaries and tallies failures", () => {
    const inst: ClaudeInstance = {
      name: "experiments",
      sessions: [
        { outcome: "ok", done: "A", ended_at: at(1), runtime_s: 3600, cost_usd: 10 },
        { outcome: "error", summary: NET, ended_at: at(2), runtime_s: 60 },
        { outcome: "usage_limit", summary: "You've hit your session limit", ended_at: at(3), runtime_s: 1800 },
        { outcome: "ok", plain: "B", ended_at: at(30) },
      ],
    };
    const d = digest([inst], [{ at: at(1), subject: "c" }, { at: at(40), subject: "old" }], NOW, NOW - 24 * H);
    expect(d).toMatchObject({ sessions: 3, meaningful: 1, failed: 2, commits: 1, costUsd: 10 });
    expect(d.items.map((i) => i.text)).toEqual(["A"]);
    expect(d.hours).toBeCloseTo(1 + 60 / 3600 + 0.5);
    expect(failuresSentence(d.failures)).toBe("1 couldn't reach the API, 1 hit the usage limit");
    expect(digest([inst], [], NOW, NOW - 7 * 24 * H).items.map((i) => i.text)).toEqual(["A", "B"]);
  });
});

describe("costs", () => {
  it("zero-fills the last 30 UTC days and labels sources", () => {
    const days = costDays({ by_day: [{ date: "2026-10-21", usd: 5 }, { date: "2026-10-01", usd: 2 }, { date: "2026-08-01", usd: 9 }] }, NOW);
    expect(days).toHaveLength(30);
    expect(days[29]).toEqual({ date: "2026-10-21", usd: 5 });
    expect(days.find((d) => d.date === "2026-10-01")!.usd).toBe(2);
    expect(days.reduce((s, d) => s + d.usd, 0)).toBe(7);
    expect(usdLabel(2240.73)).toBe("$2,241");
    expect(usdLabel(12.3)).toBe("$12.30");
    expect(usdLabel(undefined)).toBe("–");
    expect(sourceLabel({ key: "interactive", kind: "interactive" })).toBe("Interactive (you + Claude)");
    expect(sourceLabel({ key: "experiments", label: "experiments autopilot", kind: "autopilot" })).toBe("Experiments autopilot");
    expect(sourceLabel({ key: "other_headless" })).toBe("Other headless runs");
  });
});

describe("messages and per-instance controls", () => {
  it("maps message status to Sent → Delivered → Read", () => {
    expect(messageProgress({ status: "pending" }).reached).toBe(0);
    expect(messageProgress({ status: "fetched" }).reached).toBe(0);
    expect(messageProgress({ status: "delivered" }).reached).toBe(1);
    expect(messageProgress({ status: "read" }).reached).toBe(2);
    expect(messageProgress({ status: "failed" }).bad).toBe("failed");
    expect(messageProgress({ status: "cancelled" }).bad).toBe("cancelled");
  });

  it("targets every reported instance by key and falls back to the experiments instance", () => {
    expect(instanceTargets([{ name: "experiments", key: "autopilot" }, { name: "signal", key: "autopilot-signal" }, { name: "bad", key: "../x" }]).map((t) => [t.key, t.title])).toEqual([
      ["autopilot", "Experiments autopilot"],
      ["autopilot-signal", "Signal autopilot"],
    ]);
    expect(instanceTargets([{ name: "main" }])[0].key).toBe("autopilot");
    const cmds = [
      { id: 1, target: "autopilot-signal", action: "pause", status: "done" },
      { id: 3, target: "autopilot", action: "start", status: "pending" },
      { id: 2, target: "autopilot-signal", action: "resume", status: "delivered" },
    ] as LabCommand[];
    expect(latestFor(cmds, "autopilot-signal")!.id).toBe(2);
    expect(latestFor(cmds, "queue")).toBeNull();
  });

  it("posts messages and cancels with the owner's cookie, explaining limits", async () => {
    const fetchImpl = vi.fn(async () => res(201, { id: 4, target: "autopilot", body: "hi", status: "pending" }));
    const out = await postLabMessage("autopilot", "hi", fetchImpl);
    expect(out).toMatchObject({ ok: true, message: { id: 4 } });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/api\/lab\/messages$/);
    expect(init.credentials).toBe("include");
    expect(JSON.parse(String(init.body))).toEqual({ target: "autopilot", body: "hi" });
    expect(await postLabMessage("autopilot", "hi", async () => res(429, {}))).toMatchObject({ ok: false, status: 429, message: expect.stringMatching(/20 a day/) });
    const locked = await postLabMessage("autopilot", "hi", async () => res(403, { detail: { code: "hardware_key_required", keys: 1 } }));
    expect(locked).toMatchObject({ ok: false, status: 403 });
    const cancelFetch = vi.fn(async () => res(200, { id: 4, status: "cancelled" }));
    expect(await cancelLabMessage(4, cancelFetch)).toMatchObject({ ok: true });
    expect((cancelFetch.mock.calls[0] as unknown as [string])[0]).toMatch(/\/api\/lab\/messages\/4\/cancel$/);
    expect(await cancelLabMessage(4, async () => res(409, { detail: "message is fetched" }))).toMatchObject({ ok: false, message: expect.stringMatching(/Too late/) });
  });
});

describe("fixture and safety (v2)", () => {
  it("the fixture carries costs, messages, a running session's progress and a run of failures", () => {
    const fx = buildLabFixture(NOW);
    const mac = parsePayload<MacPayload>(fx.mac)!;
    expect(mac.costs!.total_usd).toBeGreaterThan(0);
    expect(fx.messages!.length).toBeGreaterThan(0);
    const [exp] = claudeInstances(mac);
    expect(exp.current?.text).toBeTruthy();
    const groups = logEntries(sessionRows([exp])).filter((e) => e.kind === "group");
    expect(groups.some((g) => g.kind === "group" && g.rows.length >= 8)).toBe(true);
  });

  it("no v2 component renders HTML from snapshot or message text", () => {
    for (const f of ["ClaudeBoard.tsx", "ClaudeCosts.tsx", "ClaudeControls.tsx"]) {
      const src = readFileSync(resolve(__dirname, "../../components/lab", f), "utf8");
      expect(src).not.toMatch(/dangerouslySetInnerHTML|innerHTML/);
    }
  });
});
