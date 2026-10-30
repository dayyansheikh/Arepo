// Pure model for the Claude activity board (/lab/claude). Everything here tolerates absent or
// malformed fields: the Mac snapshot is optional, and older Mac clients send no `activity` block.

import type { Tone } from "./model";
import type { AutopilotBlock, ClaudeInstance, ClaudeSession, CommitItem, CostsBlock, LabCommand, LabMessage, MacPayload } from "./types";

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

// ---------------------------------------------------------------------------------------------
// Plain-English summaries (board v2)

const MD_MARKERS = /(\*\*|__|`|^#{1,6}\s+|^\s*[-*•]\s+|^\s*\d+[.)]\s+)/gm;

/** First one or two sentences of a result text without markdown markers (≤ n chars). */
export function firstSentences(text: string | null | undefined, n = 280): string | null {
  if (!text) return null;
  // Drop heading lines ("## Summary", "**Results**") when there is other text: they are labels, not sentences.
  const lines = text.split(/\r?\n/);
  const body = lines.filter((l) => !/^\s*(#{1,6}\s+.*|\*\*[^*]+\*\*:?)\s*$/.test(l));
  const flat = (body.some((l) => l.trim()) ? body.join("\n") : text).replace(MD_MARKERS, "").replace(/\s+/g, " ").trim();
  if (!flat) return null;
  const parts = flat.split(/(?<=[.!?])\s+(?=[A-Z0-9("'])/);
  let out = parts[0];
  if (out.length < 120 && parts.length > 1) out = `${out} ${parts[1]}`;
  return out.length > n ? `${out.slice(0, n - 1).trimEnd()}…` : out;
}

/** The session's one-line plain-English summary: AUTOPILOT_DONE line, else first sentences. */
export function sessionSummary(s: ClaudeSession): string | null {
  return s.done?.trim() || s.plain?.trim() || firstSentences(s.summary) || null;
}

export type FailureKind = "network" | "usage_limit" | "auth" | "error" | "interrupted";

export const FAILURE_LABEL: Record<FailureKind, string> = {
  network: "failed: couldn't reach the API",
  usage_limit: "stopped at the usage limit",
  auth: "failed: Claude login problem",
  error: "ended with an error",
  interrupted: "ended without a record (Mac asleep, restarted or stopped)",
};

const NETWORK_RE = /API Error|Can't reach the API|ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|socket hang up|Connection error|fetch failed|overloaded/i;
const LIMIT_RE = /hit your (?:[\w ]+ )?limit|usage limit reached/i;

/**
 * Why a session produced nothing worth reading, or null when it is a meaningful session.
 * A session with an AUTOPILOT_DONE line is always meaningful.
 */
export function failureKind(s: ClaudeSession): FailureKind | null {
  if (s.done && s.done.trim()) return null;
  const text = `${s.plain ?? ""} ${s.summary ?? ""}`;
  if (s.outcome === "usage_limit" || LIMIT_RE.test(text)) return "usage_limit";
  if (s.outcome === "auth_error") return "auth";
  if (NETWORK_RE.test(text) && text.length < 800) return "network";
  if (s.outcome === "error") return "error";
  if (s.outcome === "interrupted" && !s.summary) return "interrupted";
  return null;
}

// ---------------------------------------------------------------------------------------------
// Session log rows, with runs of failed sessions collapsed into one group

export interface SessionRowData {
  key: string;
  instance: string;
  session: ClaudeSession;
  live: boolean;
  sortT: number;
}

export function sessionRows(instances: ClaudeInstance[]): SessionRowData[] {
  const rows: SessionRowData[] = [];
  for (const inst of instances) {
    const name = inst.name ?? "main";
    if (inst.session_alive && inst.started_at) {
      rows.push({
        key: `${name}-live`,
        instance: name,
        live: true,
        session: { started_at: inst.started_at, outcome: "running" },
        sortT: Number.MAX_SAFE_INTEGER,
      });
    }
    (inst.sessions ?? []).forEach((s, i) => {
      rows.push({ key: `${name}-${i}`, instance: name, live: false, session: s, sortT: ms(s.ended_at) ?? ms(s.started_at) ?? 0 });
    });
  }
  return rows.sort((a, b) => b.sortT - a.sortT);
}

export type LogEntry =
  | { kind: "session"; row: SessionRowData }
  | { kind: "group"; key: string; instance: string; failure: FailureKind; rows: SessionRowData[]; from: number | null; to: number | null };

/** Collapses consecutive failed sessions of the same kind and instance into one group entry. */
export function logEntries(rows: SessionRowData[]): LogEntry[] {
  const out: LogEntry[] = [];
  for (const row of rows) {
    const f = row.live ? null : failureKind(row.session);
    const prev = out[out.length - 1];
    if (f && prev && prev.kind === "group" && prev.failure === f && prev.instance === row.instance) {
      prev.rows.push(row);
      const start = ms(row.session.started_at) ?? ms(row.session.ended_at);
      if (start != null) prev.from = prev.from == null ? start : Math.min(prev.from, start);
      continue;
    }
    if (f) {
      const start = ms(row.session.started_at) ?? ms(row.session.ended_at);
      const end = ms(row.session.ended_at) ?? start;
      out.push({ kind: "group", key: `g-${row.key}`, instance: row.instance, failure: f, rows: [row], from: start, to: end });
    } else {
      out.push({ kind: "session", row });
    }
  }
  return out;
}

function hhmm(t: number): string {
  return new Date(t).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function dayKey(t: number): string {
  return new Date(t).toDateString();
}

/** "08:03–11:55", or "Mon 22:10 – Tue 01:40" across days. */
export function spanLabel(from: number | null, to: number | null): string {
  if (from == null && to == null) return "";
  const a = from ?? to!;
  const b = to ?? from!;
  if (dayKey(a) === dayKey(b)) {
    const day = new Date(a).toLocaleDateString("en-GB", { weekday: "short" });
    return a === b ? `${day} ${hhmm(a)}` : `${day} ${hhmm(a)}–${hhmm(b)}`;
  }
  return `${clockLabel(a)} – ${clockLabel(b)}`;
}

export function groupLabel(g: Extract<LogEntry, { kind: "group" }>): string {
  const n = g.rows.length;
  const span = spanLabel(g.from, g.to);
  return `${n} session${n === 1 ? "" : "s"} ${FAILURE_LABEL[g.failure]}${span ? ` (${span})` : ""}`;
}

// ---------------------------------------------------------------------------------------------
// "Right now" lines

export function instanceTitle(inst: ClaudeInstance): string {
  const n = (inst.name ?? "main").trim();
  const nice = n.charAt(0).toUpperCase() + n.slice(1);
  return /autopilot/i.test(nice) ? nice : `${nice} autopilot`;
}

export function cleanReason(reason: string | null | undefined): string {
  return (reason ?? "").replace(/^\d{4}-\d\d-\d\dT[\d:.]+Z\s*/, "").trim();
}

export interface RightNow {
  key: InstanceState["key"];
  tone: Tone;
  title: string;
  status: string;
  said: string | null;
  saidAt: number | null;
  saidLabel: string;
}

export function rightNow(inst: ClaudeInstance, nowMs: number): RightNow {
  const st = instanceState(inst, nowMs);
  const title = instanceTitle(inst);
  let status: string;
  const started = ms(inst.started_at);
  if (st.key === "error") status = "no data from the Mac for this instance";
  else if (st.key === "paused") {
    const why = cleanReason(inst.pause_reason);
    status = `paused${why && why !== "manual pause" ? ` (${why})` : " by hand"}`;
    if (inst.session_alive && started != null) status += `; the current session is still finishing (${durationLabel((nowMs - started) / 1000)})`;
  } else if (st.key === "running") status = started != null ? `working for ${durationLabel((nowMs - started) / 1000)}` : "working";
  else if (st.key === "waiting") {
    const next = ms(inst.next_allowed);
    status = `waiting for the usage reset at ${next != null ? hhmm(next) : "–"} (${relLabel(next, nowMs)})`;
  } else status = "idle; the next session starts at the next half-hourly check";
  let said: string | null = null;
  let saidAt: number | null = null;
  let saidLabel = "last said";
  if (inst.session_alive && inst.current?.text) {
    said = inst.current.text;
    saidAt = ms(inst.current.at);
    saidLabel = "now saying";
  } else {
    const last = (inst.sessions ?? []).find((s) => !failureKind(s) && sessionSummary(s));
    if (last) {
      said = sessionSummary(last);
      saidAt = ms(last.ended_at);
      saidLabel = "last session";
    }
  }
  return { key: st.key, tone: st.tone, title, status, said, saidAt, saidLabel };
}

/** Whether "Start a session now" can work, and why not. */
export function startState(inst: ClaudeInstance, nowMs: number): { ok: boolean; why: string } {
  if (!inst.key) return { ok: false, why: "This Mac client is too old to start sessions." };
  if (!inst.startable) return { ok: false, why: "No launchd job for this instance on the Mac." };
  if (inst.paused) return { ok: false, why: "Paused: resume it first." };
  if (inst.session_alive) return { ok: false, why: "A session is already running." };
  const next = ms(inst.next_allowed);
  if (next != null && next > nowMs) return { ok: false, why: `Usage limit: allowed again ${clockLabel(next)}.` };
  return { ok: true, why: "Starts one session at the Mac's next check (within 10 min); the autopilot re-checks pause, usage limit and login." };
}

// ---------------------------------------------------------------------------------------------
// Today / this week digest

export interface Digest {
  sessions: number;
  meaningful: number;
  failed: number;
  failures: Partial<Record<FailureKind, number>>;
  hours: number;
  costUsd: number | null;
  commits: number;
  items: Array<{ key: string; instance: string; at: number; text: string; outcome: string }>;
}

export function digest(instances: ClaudeInstance[], commits: CommitItem[] | undefined, nowMs: number, sinceMs: number): Digest {
  const d: Digest = { sessions: 0, meaningful: 0, failed: 0, failures: {}, hours: 0, costUsd: null, commits: 0, items: [] };
  for (const inst of instances) {
    const name = inst.name ?? "main";
    (inst.sessions ?? []).forEach((s, i) => {
      const end = ms(s.ended_at) ?? ms(s.started_at);
      if (end == null || end < sinceMs || end > nowMs + 60_000) return;
      d.sessions += 1;
      if (typeof s.runtime_s === "number") d.hours += s.runtime_s / 3600;
      if (typeof s.cost_usd === "number" && Number.isFinite(s.cost_usd)) d.costUsd = (d.costUsd ?? 0) + s.cost_usd;
      const f = failureKind(s);
      if (f) {
        d.failed += 1;
        d.failures[f] = (d.failures[f] ?? 0) + 1;
        return;
      }
      d.meaningful += 1;
      const text = sessionSummary(s);
      if (text) d.items.push({ key: `${name}-${i}`, instance: name, at: end, text, outcome: s.outcome ?? "ok" });
    });
  }
  d.items.sort((a, b) => b.at - a.at);
  d.commits = (commits ?? []).filter((c) => {
    const t = ms(c?.at);
    return t != null && t >= sinceMs;
  }).length;
  return d;
}

/** Local midnight today. */
export function startOfToday(nowMs: number): number {
  const d = new Date(nowMs);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function failuresSentence(f: Partial<Record<FailureKind, number>>): string {
  const words: Record<FailureKind, string> = {
    network: "couldn't reach the API",
    usage_limit: "hit the usage limit",
    auth: "had a login problem",
    error: "ended with an error",
    interrupted: "ended without a record",
  };
  return (Object.entries(f) as Array<[FailureKind, number]>)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([k, n]) => `${n} ${words[k]}`)
    .join(", ");
}

// ---------------------------------------------------------------------------------------------
// Costs

export function usdLabel(v: number | null | undefined): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "–";
  if (v >= 100) return `$${Math.round(v).toLocaleString("en-GB")}`;
  return `$${v.toFixed(2)}`;
}

/** The last `days` UTC days ending today, zero-filled. */
export function costDays(costs: CostsBlock | null | undefined, nowMs: number, days = 30): Array<{ date: string; usd: number }> {
  const map = new Map((costs?.by_day ?? []).filter((d) => d && typeof d.date === "string").map((d) => [d.date, Number(d.usd) || 0]));
  const out = [];
  const today = new Date(nowMs);
  for (let i = days - 1; i >= 0; i--) {
    const t = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - i);
    const date = new Date(t).toISOString().slice(0, 10);
    out.push({ date, usd: map.get(date) ?? 0 });
  }
  return out;
}

export function sourceLabel(s: { key: string; label?: string; kind?: string }): string {
  if (s.kind === "interactive" || s.key === "interactive") return "Interactive (you + Claude)";
  if (s.key === "other_headless") return "Other headless runs";
  const base = (s.label ?? s.key).replace(/\s*autopilot$/i, "");
  return `${base.charAt(0).toUpperCase()}${base.slice(1)} autopilot`;
}

// ---------------------------------------------------------------------------------------------
// Messages and per-instance commands

export const MESSAGE_STEPS = ["Sent", "Delivered", "Read"] as const;

export function messageProgress(m: Pick<LabMessage, "status">): { reached: number; bad: "failed" | "cancelled" | null; label: string } {
  switch (m.status) {
    case "pending":
      return { reached: 0, bad: null, label: "Waiting for the Mac to pick it up (it checks every 10 minutes)." };
    case "fetched":
      return { reached: 0, bad: null, label: "The Mac picked it up and is writing it to the inbox." };
    case "delivered":
      return { reached: 1, bad: null, label: "In the instance's INBOX.md; Claude reads it at the start of its next session." };
    case "read":
      return { reached: 2, bad: null, label: "Read: the session took it from the inbox." };
    case "failed":
      return { reached: 0, bad: "failed", label: "The Mac could not deliver it." };
    case "cancelled":
      return { reached: 0, bad: "cancelled", label: "Cancelled before delivery." };
    default:
      return { reached: 0, bad: null, label: m.status };
  }
}

/** Instance choices for messages/controls; the experiments instance ("autopilot") is the fallback. */
export function instanceTargets(instances: ClaudeInstance[]): Array<{ key: string; title: string; inst: ClaudeInstance | null }> {
  const out = instances
    .filter((i) => typeof i.key === "string" && /^autopilot(-[a-z0-9]{1,24})?$/.test(i.key))
    .map((i) => ({ key: i.key!, title: instanceTitle(i), inst: i }));
  return out.length ? out : [{ key: "autopilot", title: "Experiments autopilot", inst: instances[0] ?? null }];
}

export function latestFor(commands: LabCommand[] | undefined, target: string): LabCommand | null {
  return (commands ?? []).filter((c) => c && c.target === target).sort((a, b) => b.id - a.id)[0] ?? null;
}
