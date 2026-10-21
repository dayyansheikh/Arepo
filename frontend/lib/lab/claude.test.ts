import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  claudeInstances,
  commitFeed,
  costLabel,
  durationLabel,
  instanceState,
  parseInline,
  parseMarkdownLite,
  relLabel,
  timelineBars,
  timelineTicks,
  windowStats,
} from "./claude";
import { buildActivityFixture, buildLabFixture } from "./fixture";
import { parsePayload } from "./model";
import type { ClaudeInstance, MacPayload } from "./types";

const NOW = Date.parse("2026-10-21T12:00:00Z");
const H = 3_600_000;
const at = (hAgo: number) => new Date(NOW - hAgo * H).toISOString();

describe("claudeInstances", () => {
  it("uses activity.instances and drops junk sessions", () => {
    const mac = {
      activity: { instances: [{ name: "signal", sessions: [null, { outcome: "ok" }] }, null] },
    } as unknown as MacPayload;
    const list = claudeInstances(mac);
    expect(list).toHaveLength(1);
    expect(list[0].sessions).toEqual([{ outcome: "ok" }]);
  });

  it("falls back to the legacy autopilot block, newest first, with derived start times", () => {
    const list = claudeInstances({
      autopilot: {
        paused: false,
        session_alive: false,
        recent: [
          { at: at(10), outcome: "ok", runtime_s: 3600 },
          { at: at(2), outcome: "timeout" },
          { at: "garbage", outcome: "error" },
        ],
      },
    });
    expect(list).toHaveLength(1);
    expect(list[0].name).toBe("main");
    expect(list[0].sessions!.map((s) => s.outcome)).toEqual(["timeout", "ok"]);
    expect(list[0].sessions![1].started_at).toBe(at(11));
    expect(list[0].sessions![0].started_at).toBeNull();
  });

  it("tolerates a missing or empty payload", () => {
    expect(claudeInstances(null)).toEqual([]);
    expect(claudeInstances({})).toEqual([]);
    expect(claudeInstances({ activity: { instances: [] } })).toEqual([]);
  });
});

describe("instanceState", () => {
  it("orders paused > running > waiting > idle", () => {
    expect(instanceState({ paused: true, pause_reason: "manual pause" }, NOW)).toMatchObject({ key: "paused", detail: "manual pause" });
    const pausedLive = instanceState({ paused: true, session_alive: true, started_at: at(1) }, NOW);
    expect(pausedLive.key).toBe("paused");
    expect(pausedLive.detail).toContain("still running (for 1 h)");
    expect(instanceState({ session_alive: true, started_at: at(2.5) }, NOW)).toMatchObject({ key: "running", detail: "Session running for 2 h 30 min" });
    const w = instanceState({ next_allowed: at(-3) }, NOW);
    expect(w.key).toBe("waiting");
    expect(w.detail).toContain("in 3 h");
    expect(instanceState({ next_allowed: at(1) }, NOW).key).toBe("idle");
    expect(instanceState({ error: "OSError" }, NOW).key).toBe("error");
  });
});

describe("timeline", () => {
  const inst: ClaudeInstance = {
    name: "experiments",
    session_alive: true,
    started_at: at(1),
    sessions: [
      { started_at: at(5), ended_at: at(3), outcome: "ok", cost_usd: 10 },
      { ended_at: at(20), runtime_s: 7200, outcome: "usage_limit", cost_usd: 5.5 },
      { started_at: at(60), ended_at: at(47), outcome: "timeout" }, // straddles the window start
      { started_at: at(80), ended_at: at(70), outcome: "error" }, // entirely before the window
      { outcome: "interrupted" }, // no times: not drawable
    ],
  };

  it("positions bars inside the 48 h window and adds the live session", () => {
    const bars = timelineBars(inst, NOW);
    expect(bars.map((b) => b.outcome)).toEqual(["timeout", "usage_limit", "ok", "running"]);
    const clipped = bars[0];
    expect(clipped.leftPct).toBe(0);
    expect(clipped.widthPct).toBeCloseTo((1 / 48) * 100, 5);
    const ok = bars[2];
    expect(ok.leftPct).toBeCloseTo((43 / 48) * 100, 5);
    expect(ok.widthPct).toBeCloseTo((2 / 48) * 100, 5);
    const live = bars[3];
    expect(live.running).toBe(true);
    expect(live.leftPct + live.widthPct).toBeCloseTo(100, 5);
    for (const b of bars) expect(b.leftPct + b.widthPct).toBeLessThanOrEqual(100.0001);
  });

  it("summarises the window", () => {
    const st = windowStats(inst, NOW);
    expect(st.sessions).toBe(4);
    expect(st.byOutcome).toEqual({ timeout: 1, usage_limit: 1, ok: 1, running: 1 });
    expect(st.hours).toBeCloseTo(1 + 2 + 2 + 1, 5);
    expect(st.costUsd).toBeCloseTo(15.5, 5);
    expect(windowStats({ sessions: [] }, NOW)).toEqual({ sessions: 0, hours: 0, byOutcome: {}, costUsd: null });
  });

  it("ticks sit on whole 12 h boundaries inside the window", () => {
    const ticks = timelineTicks(NOW);
    expect(ticks.length).toBe(5); // 48 h ago (0 %), 36, 24, 12 h ago and now (100 %)
    for (const t of ticks) {
      expect(t.t % (12 * H)).toBe(0);
      expect(t.pct).toBeGreaterThanOrEqual(0);
      expect(t.pct).toBeLessThanOrEqual(100);
    }
  });
});

describe("labels", () => {
  it("formats durations, relative times and costs", () => {
    expect(durationLabel(45)).toBe("45 s");
    expect(durationLabel(7323)).toBe("2 h 02 min");
    expect(durationLabel(3600)).toBe("1 h");
    expect(durationLabel(undefined)).toBe("–");
    expect(relLabel(NOW - 5 * 60_000, NOW)).toBe("5 min ago");
    expect(relLabel(NOW + 2 * H, NOW)).toBe("in 2 h");
    expect(relLabel(null, NOW)).toBe("–");
    expect(costLabel(73.656)).toBe("$73.66");
    expect(costLabel(1234.5)).toBe("$1,235");
    expect(costLabel(undefined)).toBeNull();
  });

  it("sorts commits newest first and drops empty rows", () => {
    const feed = commitFeed([
      { at: at(5), sha: "a", subject: "older" },
      { at: at(1), sha: "b", subject: "newer" },
      {} as never,
    ]);
    expect(feed.map((c) => c.sha)).toEqual(["b", "a"]);
    expect(commitFeed(undefined)).toEqual([]);
  });
});

describe("markdown-lite", () => {
  it("parses headings, lists, bold and code; leaves HTML as text", () => {
    const md = "# Title\n\nA **bold** and `code` <script>alert(1)</script>\nsame para\n\n- one\n- two\n  continued\n1. first\n2) second";
    const blocks = parseMarkdownLite(md);
    expect(blocks.map((b) => b.kind)).toEqual(["h", "p", "ul", "ol"]);
    const p = blocks[1];
    if (p.kind !== "p") throw new Error("expected p");
    expect(p.inlines).toEqual([
      { kind: "text", text: "A " },
      { kind: "strong", text: "bold" },
      { kind: "text", text: " and " },
      { kind: "code", text: "code" },
      { kind: "text", text: " <script>alert(1)</script> same para" },
    ]);
    const ul = blocks[2];
    if (ul.kind !== "ul") throw new Error("expected ul");
    expect(ul.items).toHaveLength(2);
    expect(ul.items[1].map((i) => i.text).join("")).toBe("two continued");
    expect(parseMarkdownLite("")).toEqual([]);
    expect(parseInline("no marks")).toEqual([{ kind: "text", text: "no marks" }]);
  });
});

describe("fixture and safety", () => {
  it("the fixture's mac payload carries a two-instance activity block", () => {
    const fx = buildLabFixture(NOW);
    const mac = parsePayload<MacPayload>(fx.mac);
    const list = claudeInstances(mac);
    expect(list.map((i) => i.name)).toEqual(["experiments", "signal"]);
    expect(buildActivityFixture(NOW).commits!.length).toBeGreaterThan(5);
    expect(instanceState(list[1], NOW).key).toBe("paused");
  });

  it("the board never renders HTML from snapshot text", () => {
    const src = readFileSync(resolve(__dirname, "../../components/lab/ClaudeBoard.tsx"), "utf8");
    expect(src).not.toMatch(/dangerouslySetInnerHTML/);
    expect(src).not.toMatch(/innerHTML/);
  });
});
