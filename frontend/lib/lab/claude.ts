// Pure model for the Claude activity board (/lab/claude). Everything here tolerates absent or
// malformed fields: the Mac snapshot is optional, and older Mac clients send no `activity` block.

import type { Tone } from "./model";
import type { AutopilotBlock, ClaudeInstance, ClaudeSession, CommitItem, MacPayload } from "./types";

export const TIMELINE_HOURS = 48;

const MIN = 60_000;
const HOUR = 60 * MIN;

export function ms(iso: string | null | undefined): number | null {
  if (!iso || typeof iso !== "string") return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : t;
}

// ---------------------------------------------------------------------------------------------
// Outcomes

export const OUTCOME_META: Record<string, { label: string; tone: Tone; help: string }> = {
  running: { label: "Running", tone: "pos", help: "The session is working right now." },
  ok: { label: "Finished", tone: "neutral", help: "The session ended normally." },
  usage_limit: { label: "Usage limit", tone: "warn", help: "Stopped by the Claude subscription limit; resumes after the reset." },
  timeout: { label: "Timed out", tone: "warn", help: "Hit the wall-clock limit and was stopped." },
  interrupted: { label: "Interrupted", tone: "muted", help: "Ended without a record (sleep, crash or kill)." },
  error: { label: "Error", tone: "neg", help: "The session ended with an error." },
  auth_error: { label: "Login problem", tone: "neg", help: "Claude login failed; the autopilot paused itself." },
};

export function outcomeMeta(outcome: string | null | undefined) {
  return (
    OUTCOME_META[outcome ?? ""] ?? {
      label: outcome ? outcome.replace(/_/g, " ") : "Unknown",
      tone: "muted" as Tone,
      help: "Outcome not reported.",
    }
  );
}

// ---------------------------------------------------------------------------------------------
// Instances

/**
 * Instances from the Mac snapshot. Falls back to the legacy single-instance `autopilot` block
 * (sessions rebuilt from `recent`, newest first) when the Mac client predates the activity board.
 */
export function claudeInstances(mac: MacPayload | null | undefined): ClaudeInstance[] {
  const list = mac?.activity?.instances;
  if (Array.isArray(list) && list.length) {
    return list
      .filter((i): i is ClaudeInstance => !!i && typeof i === "object")
      .map((i) => ({ ...i, sessions: Array.isArray(i.sessions) ? i.sessions.filter((s) => !!s && typeof s === "object") : [] }));
  }
  const ap: AutopilotBlock | undefined = mac?.autopilot;
  if (!ap) return [];
  const sessions: ClaudeSession[] = [...(ap.recent ?? [])]
    .filter((r) => r && ms(r.at) != null)
    .sort((a, b) => (ms(b.at) ?? 0) - (ms(a.at) ?? 0))
    .map((r) => {
      const end = ms(r.at)!;
      const start = typeof r.runtime_s === "number" ? new Date(end - r.runtime_s * 1000).toISOString() : null;
      return { started_at: start, ended_at: r.at, outcome: r.outcome, runtime_s: r.runtime_s };
    });
  return [
    {
      name: "main",
      paused: ap.paused,
      pause_reason: ap.pause_reason,
      session_alive: ap.session_alive,
      started_at: ap.started_at,
      last_outcome: ap.last_outcome,
      next_allowed: ap.next_allowed,
      sessions,
    },
  ];
}

export interface InstanceState {
  key: "paused" | "running" | "waiting" | "idle" | "error";
  label: string;
  tone: Tone;
  detail: string;
}

export function instanceState(inst: ClaudeInstance, nowMs: number): InstanceState {
  if (inst.error) return { key: "error", label: "No data", tone: "muted", detail: "This instance could not be read on the Mac." };
  if (inst.paused) {
    const reason = inst.pause_reason?.trim() || "Paused by hand.";
    const t = ms(inst.started_at);
    const still = inst.session_alive
      ? ` No new sessions start; the current one is still running${t != null ? ` (for ${durationLabel((nowMs - t) / 1000)})` : ""}.`
      : "";
    return { key: "paused", label: "Paused", tone: "warn", detail: `${reason}${still}` };
  }
  if (inst.session_alive) {
    const t = ms(inst.started_at);
    return {
      key: "running",
      label: "Working",
      tone: "pos",
      detail: t != null ? `Session running for ${durationLabel((nowMs - t) / 1000)}` : "A session is running.",
    };
  }
  const next = ms(inst.next_allowed);
  if (next != null && next > nowMs) {
    return {
      key: "waiting",
      label: "Waiting for reset",
      tone: "warn",
      detail: `Usage limit reached; next session allowed ${clockLabel(next)} (${relLabel(next, nowMs)})`,
    };
  }
  return { key: "idle", label: "Idle", tone: "neutral", detail: "Between sessions; the next one starts at the next tick." };
}

// ---------------------------------------------------------------------------------------------
// Timeline

export interface TimelineBar {
  key: string;
  instance: string;
  index: number;
  outcome: string;
  start: number;
  /** Start clipped to the window (for in-window hours). */
  visibleStart: number;
  end: number;
  leftPct: number;
  widthPct: number;
  running: boolean;
  session: ClaudeSession;
}

/** Bars for one instance over [nowMs − hours, nowMs]; a live session runs to now. */
export function timelineBars(inst: ClaudeInstance, nowMs: number, hours = TIMELINE_HOURS): TimelineBar[] {
  const from = nowMs - hours * HOUR;
  const span = nowMs - from;
  const out: TimelineBar[] = [];
  const name = inst.name ?? "main";
  const push = (s: ClaudeSession, index: number, running: boolean) => {
    const end = running ? nowMs : (ms(s.ended_at) ?? null);
    let start = ms(s.started_at);
    if (start == null && end != null && typeof s.runtime_s === "number") start = end - s.runtime_s * 1000;
    if (start == null || end == null || end < from || start > nowMs) return;
    const a = Math.max(start, from);
    const b = Math.min(Math.max(end, start), nowMs);
    const leftPct = ((a - from) / span) * 100;
    const widthPct = Math.max(0.35, ((b - a) / span) * 100);
    out.push({
      key: `${name}-${index}-${start}`,
      instance: name,
      index,
      outcome: running ? "running" : (s.outcome ?? "unknown"),
      start,
      visibleStart: a,
      end: b,
      leftPct: Math.min(leftPct, 100 - widthPct),
      widthPct,
      running,
      session: s,
    });
  };
  (inst.sessions ?? []).forEach((s, i) => push(s, i, false));
  if (inst.session_alive && inst.started_at) {
    push({ started_at: inst.started_at, outcome: "running" }, -1, true);
  }
  return out.sort((x, y) => x.start - y.start);
}

/** Tick marks every `stepH` hours, aligned to whole UTC hours. */
export function timelineTicks(nowMs: number, hours = TIMELINE_HOURS, stepH = 12): Array<{ t: number; pct: number }> {
  const from = nowMs - hours * HOUR;
  const first = Math.ceil(from / (stepH * HOUR)) * stepH * HOUR;
  const out = [];
  for (let t = first; t <= nowMs; t += stepH * HOUR) out.push({ t, pct: ((t - from) / (hours * HOUR)) * 100 });
  return out;
}

export interface WindowStats {
  sessions: number;
  hours: number;
  byOutcome: Record<string, number>;
  costUsd: number | null;
}

/** Sessions that ended inside the window (plus a live one), their hours and outcome counts. */
export function windowStats(inst: ClaudeInstance, nowMs: number, hours = TIMELINE_HOURS): WindowStats {
  const bars = timelineBars(inst, nowMs, hours);
  const byOutcome: Record<string, number> = {};
  let h = 0;
  let cost: number | null = null;
  for (const b of bars) {
    byOutcome[b.outcome] = (byOutcome[b.outcome] ?? 0) + 1;
    h += (b.end - b.visibleStart) / HOUR;
    if (typeof b.session.cost_usd === "number" && Number.isFinite(b.session.cost_usd)) cost = (cost ?? 0) + b.session.cost_usd;
  }
  return { sessions: bars.length, hours: h, byOutcome, costUsd: cost };
}

// ---------------------------------------------------------------------------------------------
// Commits

export function commitFeed(commits: CommitItem[] | undefined, limit = 30): CommitItem[] {
  if (!Array.isArray(commits)) return [];
  return commits
    .filter((c) => c && typeof c === "object" && (c.subject || c.sha))
    .sort((a, b) => (ms(b.at) ?? 0) - (ms(a.at) ?? 0))
    .slice(0, limit);
}

// ---------------------------------------------------------------------------------------------
// Labels

export function durationLabel(seconds: number | null | undefined): string {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "–";
  if (seconds < 60) return `${Math.round(seconds)} s`;
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem ? `${h} h ${String(rem).padStart(2, "0")} min` : `${h} h`;
}

/** "5 min ago" / "in 2 h" relative to now. */
export function relLabel(t: number | null, nowMs: number): string {
  if (t == null) return "–";
  const d = (t - nowMs) / 1000;
  const a = Math.abs(d);
  let word: string;
  if (a < 60) return d >= 0 ? "in under a minute" : "just now";
  if (a < 3600) word = `${Math.floor(a / 60)} min`;
  else if (a < 48 * 3600) word = `${Math.floor(a / 3600)} h`;
  else word = `${Math.floor(a / 86400)} days`;
  return d >= 0 ? `in ${word}` : `${word} ago`;
}

export function clockLabel(t: number | null): string {
  if (t == null) return "–";
  return new Date(t).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

export function costLabel(usd: number | null | undefined): string | null {
  if (typeof usd !== "number" || !Number.isFinite(usd)) return null;
  return `$${usd >= 100 ? Math.round(usd).toLocaleString("en-GB") : usd.toFixed(2)}`;
}

// ---------------------------------------------------------------------------------------------
// Markdown-lite (rendered as React elements by the board; never as HTML)

export type Inline = { kind: "text" | "strong" | "code"; text: string };
export type MdBlock =
  | { kind: "p"; inlines: Inline[] }
  | { kind: "h"; inlines: Inline[] }
  | { kind: "ul" | "ol"; items: Inline[][] };

export function parseInline(src: string): Inline[] {
  const out: Inline[] = [];
  const re = /\*\*([^*]+)\*\*|`([^`]+)`/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src))) {
    if (m.index > last) out.push({ kind: "text", text: src.slice(last, m.index) });
    if (m[1] != null) out.push({ kind: "strong", text: m[1] });
    else out.push({ kind: "code", text: m[2] });
    last = m.index + m[0].length;
  }
  if (last < src.length) out.push({ kind: "text", text: src.slice(last) });
  return out;
}

/** Paragraphs, `#` headings, `-`/`*`/`1.` lists, **bold** and `code`. Anything else is plain text. */
export function parseMarkdownLite(text: string | null | undefined): MdBlock[] {
  if (!text) return [];
  const blocks: MdBlock[] = [];
  let para: string[] = [];
  let list: { kind: "ul" | "ol"; items: Inline[][] } | null = null;
  const flushPara = () => {
    if (para.length) blocks.push({ kind: "p", inlines: parseInline(para.join(" ")) });
    para = [];
  };
  const flushList = () => {
    if (list) blocks.push(list);
    list = null;
  };
  for (const raw of text.replace(/\r\n?/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    const t = line.trim();
    if (!t) {
      flushPara();
      flushList();
      continue;
    }
    const h = /^#{1,6}\s+(.*)$/.exec(t);
    const ul = /^[-*•]\s+(.*)$/.exec(t);
    const ol = /^\d+[.)]\s+(.*)$/.exec(t);
    if (h) {
      flushPara();
      flushList();
      blocks.push({ kind: "h", inlines: parseInline(h[1]) });
    } else if (ul || ol) {
      flushPara();
      const kind = ul ? "ul" : "ol";
      if (!list || list.kind !== kind) {
        flushList();
        list = { kind, items: [] };
      }
      list.items.push(parseInline((ul ?? ol)![1]));
    } else if (list && /^\s{2,}/.test(raw)) {
      const items = (list as { items: Inline[][] }).items;
      items[items.length - 1].push({ kind: "text", text: ` ${t}` });
    } else {
      flushList();
      para.push(t);
    }
  }
  flushPara();
  flushList();
  return blocks;
}
