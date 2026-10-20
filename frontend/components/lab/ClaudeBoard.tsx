"use client";

import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLabDashboard } from "@/lib/lab/use-lab-dashboard";
import { agoLabel, outcomeTone, parsePayload, snapshotFreshness } from "@/lib/lab/model";
import {
  claudeInstances,
  clockLabel,
  commitFeed,
  costLabel,
  durationLabel,
  instanceState,
  ms,
  outcomeMeta,
  parseMarkdownLite,
  relLabel,
  TIMELINE_HOURS,
  timelineBars,
  timelineTicks,
  windowStats,
  type Inline,
  type TimelineBar,
} from "@/lib/lab/claude";
import type { ClaudeInstance, ClaudeSession, HostPayload, MacPayload, QueueJob } from "@/lib/lab/types";
import { SkeletonBlock } from "@/components/Skeletons";
import { ErrorState } from "@/components/ErrorState";
import { LabTabs } from "./LabTabs";
import { Card, Dot, fmtCount, LabNotFound, LabSection, Pill, Quiet, TONE_COLOR } from "./primitives";

const MAC_STALE_S = 30 * 60; // the Mac client reports every 10 min

// ---------------------------------------------------------------------------------------------
// Markdown-lite: parsed into plain blocks and rendered as React elements (text is always escaped).

function InlineText({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((p, i) =>
        p.kind === "strong" ? (
          <strong key={i} className="font-semibold text-arepo-ink">
            {p.text}
          </strong>
        ) : p.kind === "code" ? (
          <code key={i} className="rounded bg-arepo-surface2 px-1 py-px font-mono text-[12px] text-arepo-ink">
            {p.text}
          </code>
        ) : (
          <Fragment key={i}>{p.text}</Fragment>
        ),
      )}
    </>
  );
}

function MdText({ text }: { text: string }) {
  const blocks = useMemo(() => parseMarkdownLite(text), [text]);
  return (
    <div className="space-y-2.5 text-[13.5px] leading-relaxed text-arepo-ink2 [overflow-wrap:anywhere]">
      {blocks.map((b, i) => {
        if (b.kind === "h")
          return (
            <p key={i} className="pt-1 text-[13px] font-semibold text-arepo-ink">
              <InlineText parts={b.inlines} />
            </p>
          );
        if (b.kind === "p")
          return (
            <p key={i}>
              <InlineText parts={b.inlines} />
            </p>
          );
        const List = b.kind === "ul" ? "ul" : "ol";
        return (
          <List key={i} className={`space-y-1 pl-5 ${b.kind === "ul" ? "list-disc" : "list-decimal"} marker:text-arepo-muted`}>
            {b.items.map((it, j) => (
              <li key={j}>
                <InlineText parts={it} />
              </li>
            ))}
          </List>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// Instance cards

function InstanceCard({ inst, nowMs }: { inst: ClaudeInstance; nowMs: number }) {
  const st = instanceState(inst, nowMs);
  const stats = windowStats(inst, nowMs);
  const last = inst.sessions?.[0];
  const lastEnd = ms(inst.last_finished_at) ?? ms(last?.ended_at);
  const lastOutcome = inst.last_outcome ?? last?.outcome;
  const cost = costLabel(stats.costUsd);
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-[19px] font-semibold capitalize leading-tight text-arepo-ink">{inst.name ?? "main"}</h3>
          {inst.home ? <p className="mt-0.5 truncate font-mono text-[11px] text-arepo-muted">{inst.home}</p> : null}
        </div>
        <Pill tone={st.tone}>
          <Dot tone={st.tone} pulse={st.key === "running"} size={7} />
          {st.label}
        </Pill>
      </div>
      <p className="mt-4 text-[13.5px] leading-snug text-arepo-ink2">{st.detail}</p>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-arepo-border pt-4 text-[12.5px]">
        <div>
          <dt className="text-arepo-muted">Last session</dt>
          <dd className="mt-0.5 text-arepo-ink">
            {lastOutcome ? outcomeMeta(lastOutcome).label : "–"}
            {lastEnd != null ? <span className="text-arepo-muted"> · {relLabel(lastEnd, nowMs)}</span> : null}
          </dd>
        </div>
        <div>
          <dt className="text-arepo-muted">Last {TIMELINE_HOURS} h</dt>
          <dd className="mt-0.5 font-tabular text-arepo-ink">
            {stats.sessions} session{stats.sessions === 1 ? "" : "s"} · {durationLabel(stats.hours * 3600)}
          </dd>
        </div>
        {cost ? (
          <div className="col-span-2">
            <dt className="text-arepo-muted">Reported cost, last {TIMELINE_HOURS} h</dt>
            <dd className="mt-0.5 font-tabular text-arepo-ink" title="total_cost_usd from the Claude CLI: an API-equivalent figure; sessions run on the subscription">
              ≈ {cost} <span className="text-arepo-muted">API-equivalent, on the subscription</span>
            </dd>
          </div>
        ) : null}
      </dl>
    </Card>
  );
}

// ---------------------------------------------------------------------------------------------
// Timeline

function barLabel(b: TimelineBar, nowMs: number) {
  const o = outcomeMeta(b.outcome);
  const when = b.running ? `started ${relLabel(b.start, nowMs)}` : `ended ${relLabel(b.end, nowMs)}`;
  return `${b.instance}: ${o.label}, ${durationLabel((b.end - b.start) / 1000)}, ${when}`;
}

function Timeline({
  instances,
  nowMs,
  onPick,
}: {
  instances: ClaudeInstance[];
  nowMs: number;
  onPick: (key: string) => void;
}) {
  const ticks = timelineTicks(nowMs);
  const lanes = instances.map((inst) => ({ inst, bars: timelineBars(inst, nowMs) }));
  const seen = new Set(lanes.flatMap((l) => l.bars.map((b) => b.outcome)));
  const legend = ["running", "ok", "usage_limit", "timeout", "error", "auth_error", "interrupted"].filter((o) => seen.has(o));
  const fmtTick = (t: number) => new Date(t).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
  return (
    <div>
      <div className="space-y-4">
        {lanes.map(({ inst, bars }) => (
          <div key={inst.name ?? "main"} className="grid grid-cols-1 gap-1.5 sm:grid-cols-[7.5rem_1fr] sm:items-center sm:gap-4">
            <p className="truncate text-[12.5px] font-medium capitalize text-arepo-ink2">{inst.name ?? "main"}</p>
            <ol
              className="relative h-9 rounded-[6px] bg-arepo-surface2"
              aria-label={`${inst.name ?? "main"}: sessions in the last ${TIMELINE_HOURS} hours, oldest to newest`}
            >
              {ticks.map((t) => (
                <li key={t.t} aria-hidden="true" className="absolute inset-y-0 w-px bg-arepo-border" style={{ left: `${t.pct}%` }} />
              ))}
              {bars.length === 0 ? (
                <li className="absolute inset-0 flex items-center justify-center text-[11.5px] text-arepo-muted">No sessions</li>
              ) : null}
              {bars.map((b) => {
                const tone = outcomeMeta(b.outcome).tone;
                const label = barLabel(b, nowMs);
                return (
                  <li key={b.key} className="absolute inset-y-1" style={{ left: `${b.leftPct}%`, width: `${b.widthPct}%`, minWidth: 4 }}>
                    <button
                      type="button"
                      onClick={() => onPick(b.running ? `${b.instance}-live` : `${b.instance}-${b.index}`)}
                      title={label}
                      aria-label={label}
                      className={`focus-ring block h-full w-full rounded-[4px] transition-transform hover:scale-y-110 ${b.running ? "lab-stripe" : ""}`}
                      style={{ background: TONE_COLOR[tone] }}
                    />
                  </li>
                );
              })}
            </ol>
          </div>
        ))}
      </div>
      <div className="mt-1.5 grid grid-cols-1 sm:grid-cols-[7.5rem_1fr] sm:gap-4">
        <span aria-hidden="true" className="hidden sm:block" />
        <div className="relative h-5 text-[11px] text-arepo-muted" aria-hidden="true">
          {ticks.map((t, i) => (
            <span
              key={t.t}
              className={`absolute -translate-x-1/2 whitespace-nowrap ${i % 2 ? "hidden md:inline" : ""} ${t.pct < 6 || t.pct > 90 ? "hidden" : ""}`}
              style={{ left: `${t.pct}%` }}
            >
              {fmtTick(t.t)}
            </span>
          ))}
          <span className="absolute left-0">{TIMELINE_HOURS} h ago</span>
          <span className="absolute right-0">now</span>
        </div>
      </div>
      {legend.length ? (
        <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-arepo-muted" aria-label="Legend">
          {legend.map((o) => {
            const m = outcomeMeta(o);
            const tone = m.tone;
            return (
              <li key={o} className="inline-flex items-center gap-1.5" title={m.help}>
                <span aria-hidden="true" className="h-2.5 w-2.5 rounded-[2px]" style={{ background: TONE_COLOR[tone] }} />
                {m.label}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// Session log

interface Row {
  key: string;
  instance: string;
  session: ClaudeSession;
  live: boolean;
  sortT: number;
}

function sessionRows(instances: ClaudeInstance[]): Row[] {
  const rows: Row[] = [];
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

function MetaItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-arepo-muted">{label}</dt>
      <dd className="font-tabular text-arepo-ink">{children}</dd>
    </div>
  );
}

function SessionRow({
  row,
  open,
  onToggle,
  showInstance,
  nowMs,
}: {
  row: Row;
  open: boolean;
  onToggle: () => void;
  showInstance: boolean;
  nowMs: number;
}) {
  const s = row.session;
  const o = outcomeMeta(row.live ? "running" : s.outcome);
  const tone = o.tone;
  const start = ms(s.started_at);
  const end = ms(s.ended_at);
  const runtime = row.live && start != null ? (nowMs - start) / 1000 : s.runtime_s;
  const when = row.live ? `Started ${relLabel(start, nowMs)}` : end != null ? clockLabel(end) : start != null ? clockLabel(start) : "–";
  const headline = row.live
    ? "Working now. Its summary arrives when the session ends."
    : s.done ?? (s.summary ? s.summary.split("\n").find((l) => l.trim()) : null) ?? o.help;
  const hasDetail = !row.live;
  const panelId = `session-${row.key}`;
  const cost = costLabel(s.cost_usd);
  return (
    <li id={`row-${row.key}`} className="scroll-mt-28">
      <button
        type="button"
        onClick={onToggle}
        disabled={!hasDetail}
        aria-expanded={hasDetail ? open : undefined}
        aria-controls={hasDetail ? panelId : undefined}
        className="focus-ring group grid w-full grid-cols-[auto_1fr_auto] items-start gap-x-3 gap-y-1 px-4 py-3.5 text-left transition-colors enabled:hover:bg-arepo-surface2/60 sm:px-5"
      >
        <span className="mt-[5px]">
          <Dot tone={tone} pulse={row.live} />
        </span>
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-arepo-muted">
            <span className="font-tabular text-arepo-ink2">{when}</span>
            {typeof runtime === "number" ? <span className="font-tabular">· {durationLabel(runtime)}</span> : null}
            {showInstance ? (
              <span className="rounded-full border border-arepo-border px-2 py-px text-[11px] capitalize text-arepo-ink2">{row.instance}</span>
            ) : null}
            {s.test ? <span className="rounded-full border border-arepo-border px-2 py-px text-[11px]">test run</span> : null}
          </span>
          <span className={`mt-1 block text-[13.5px] leading-snug text-arepo-ink [overflow-wrap:anywhere] ${open ? "" : "line-clamp-2"}`}>
            {headline}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <Pill tone={tone}>{o.label}</Pill>
          {hasDetail ? (
            <svg
              aria-hidden="true"
              viewBox="0 0 16 16"
              className={`h-4 w-4 flex-none text-arepo-muted transition-transform ${open ? "rotate-180" : ""}`}
            >
              <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : null}
        </span>
      </button>
      {hasDetail && open ? (
        <div id={panelId} className="border-t border-dashed border-arepo-border px-4 pb-5 pt-4 sm:pl-12 sm:pr-5">
          {s.done ? (
            <p className="mb-3 text-[12px] font-semibold uppercase tracking-wider text-arepo-muted">Closing summary</p>
          ) : null}
          {s.summary ? (
            <MdText text={s.summary} />
          ) : (
            <p className="text-[13px] text-arepo-muted">
              {s.log_state === "empty" || s.log_state === "missing"
                ? "No result text: the session ended before Claude wrote its result."
                : "No summary text in this session's result."}
            </p>
          )}
          {s.summary_truncated ? <p className="mt-2 text-[12px] text-arepo-muted">Shortened on the Mac; the full text stays in the local log.</p> : null}
          {s.note ? <p className="mt-2 text-[12px] text-arepo-muted">Note: {s.note}.</p> : null}
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-[12px] sm:grid-cols-4">
            <MetaItem label="Started">{start != null ? clockLabel(start) : "–"}</MetaItem>
            <MetaItem label="Ended">{end != null ? clockLabel(end) : "–"}</MetaItem>
            {typeof s.turns === "number" ? <MetaItem label="Turns">{fmtCount(s.turns)}</MetaItem> : null}
            {cost ? <MetaItem label="Reported cost">≈ {cost}</MetaItem> : null}
            {s.terminal_reason ? <MetaItem label="Ended because">{s.terminal_reason.replace(/_/g, " ")}</MetaItem> : null}
          </dl>
        </div>
      ) : null}
    </li>
  );
}

function SessionLog({
  instances,
  nowMs,
  openKey,
  setOpenKey,
}: {
  instances: ClaudeInstance[];
  nowMs: number;
  openKey: string | null;
  setOpenKey: (k: string | null) => void;
}) {
  const [filter, setFilter] = useState<string>("all");
  const [showAll, setShowAll] = useState(false);
  const names = instances.map((i) => i.name ?? "main");
  const rows = sessionRows(instances).filter((r) => filter === "all" || r.instance === filter);
  const openIdx = openKey ? rows.findIndex((r) => r.key === openKey) : -1;
  const limit = showAll ? rows.length : Math.max(10, openIdx + 1);
  const shown = rows.slice(0, limit);
  if (!rows.length && filter === "all") return <Quiet>No sessions reported yet.</Quiet>;
  return (
    <div>
      {names.length > 1 ? (
        <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Show sessions from">
          {["all", ...names].map((n) => (
            <button
              key={n}
              type="button"
              aria-pressed={filter === n}
              onClick={() => setFilter(n)}
              className={`focus-ring rounded-full border px-3 py-1 text-[12.5px] capitalize transition-colors ${
                filter === n ? "border-arepo-ink bg-arepo-ink text-white" : "border-arepo-border bg-arepo-surface text-arepo-ink2 hover:bg-arepo-surface2"
              }`}
            >
              {n === "all" ? "All instances" : n}
            </button>
          ))}
        </div>
      ) : null}
      <div className="panel overflow-hidden">
        <ol className="divide-y divide-arepo-border">
          {shown.map((r) => (
            <SessionRow
              key={r.key}
              row={r}
              open={openKey === r.key}
              onToggle={() => setOpenKey(openKey === r.key ? null : r.key)}
              showInstance={names.length > 1}
              nowMs={nowMs}
            />
          ))}
        </ol>
      </div>
      {rows.length > shown.length ? (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="focus-ring mt-3 rounded px-1 text-[13px] text-arepo-ink2 underline-offset-2 hover:text-arepo-ink hover:underline"
        >
          Show all {rows.length} sessions
        </button>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// Commits + research server

function CommitList({ mac, nowMs }: { mac: MacPayload | null; nowMs: number }) {
  const commits = commitFeed(mac?.activity?.commits);
  if (!commits.length) return <Quiet>No commits reported yet.</Quiet>;
  return (
    <ol className="divide-y divide-arepo-border">
      {commits.map((c, i) => {
        const t = ms(c.at);
        return (
          <li key={`${c.sha}-${i}`} className="grid grid-cols-[1fr_auto] gap-x-3 py-2.5">
            <p className="min-w-0 text-[13.5px] leading-snug text-arepo-ink [overflow-wrap:anywhere]">{c.subject ?? "(no subject)"}</p>
            <p className="text-right text-[12px] text-arepo-muted">
              <span className="block whitespace-nowrap" title={t != null ? new Date(t).toLocaleString("en-GB") : undefined}>
                {relLabel(t, nowMs)}
              </span>
              {c.sha ? <span className="font-mono text-[11px]">{c.sha.slice(0, 8)}</span> : null}
            </p>
          </li>
        );
      })}
    </ol>
  );
}

const QUEUE_WORD: Record<string, string> = { done: "done", tempfail: "retried", error: "errors", failed: "failed", interrupted: "interrupted", timeout: "timed out" };

function ServerCard({ host, nowMs }: { host: HostPayload | null; nowMs: number }) {
  const tally = host?.activity?.queue;
  const running = host?.queue?.running ?? [];
  const recent: QueueJob[] = [...(host?.queue?.recent ?? [])]
    .filter((j) => j && ms(j.at) != null)
    .sort((a, b) => (ms(b.at) ?? 0) - (ms(a.at) ?? 0))
    .slice(0, 6);
  return (
    <Card>
      <h3 className="text-[15px] font-semibold text-arepo-ink">Research server</h3>
      <p className="mt-0.5 text-[12.5px] text-arepo-muted">The queue keeps running when Claude is at a usage limit.</p>
      {!host ? (
        <div className="mt-4">
          <Quiet>No report from the research host yet.</Quiet>
        </div>
      ) : (
        <>
          {tally && typeof tally.attempts === "number" ? (
            <div className="mt-4">
              <p className="font-display font-tabular text-[24px] font-semibold leading-none text-arepo-ink">{fmtCount(tally.attempts)}</p>
              <p className="mt-1 text-[12.5px] text-arepo-muted">
                job attempts in {tally.window_h ?? 48} h
                {typeof tally.distinct_jobs === "number" ? ` across ${fmtCount(tally.distinct_jobs)} jobs` : ""}
              </p>
              {tally.outcomes ? (
                <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-arepo-ink2">
                  {Object.entries(tally.outcomes)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, v]) => (
                      <span key={k} className="inline-flex items-center gap-1.5">
                        <span aria-hidden="true" className="h-2 w-2 rounded-[2px]" style={{ background: TONE_COLOR[outcomeTone(k)] }} />
                        {fmtCount(v)} {QUEUE_WORD[k] ?? k.replace(/_/g, " ")}
                      </span>
                    ))}
                </p>
              ) : null}
            </div>
          ) : null}
          <h4 className="mt-5 text-[12px] font-semibold uppercase tracking-wider text-arepo-muted">Running now</h4>
          {running.length ? (
            <ul className="mt-2 space-y-2">
              {running.map((j, i) => (
                <li key={`${j.id}-${i}`} className="flex items-start gap-2 text-[13px]">
                  <span className="mt-[6px]">
                    <Dot tone="pos" pulse />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-arepo-ink">{j.title ?? j.id}</span>
                    <span className="text-[11.5px] text-arepo-muted">
                      {ms(j.started_at) != null ? `since ${relLabel(ms(j.started_at), nowMs)}` : "running"}
                      {j.lane ? ` · ${j.lane}` : ""}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-[13px] text-arepo-muted">Nothing running.</p>
          )}
          {recent.length ? (
            <>
              <h4 className="mt-5 text-[12px] font-semibold uppercase tracking-wider text-arepo-muted">Last finished</h4>
              <ul className="mt-2 space-y-1.5">
                {recent.map((j, i) => (
                  <li key={`${j.id}-${i}`} className="grid grid-cols-[auto_1fr_auto] items-baseline gap-2 text-[12.5px]">
                    <span aria-hidden="true" className="h-2 w-2 translate-y-[-1px] rounded-[2px]" style={{ background: TONE_COLOR[outcomeTone(j.outcome)] }} />
                    <span className="min-w-0 truncate text-arepo-ink2" title={`${j.title ?? j.id}: ${j.outcome ?? "unknown"}`}>
                      {j.title ?? j.id}
                      <span className="sr-only">: {j.outcome ?? "unknown"}</span>
                    </span>
                    <span className="whitespace-nowrap text-[11.5px] text-arepo-muted">{relLabel(ms(j.at), nowMs)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------------------------
// Page

function LoadingView() {
  return (
    <div className="space-y-10" aria-busy="true" aria-label="Loading Claude activity">
      <SkeletonBlock className="h-10 w-48" />
      <div className="grid gap-4 sm:grid-cols-2">
        <SkeletonBlock className="h-44" />
        <SkeletonBlock className="h-44" />
      </div>
      <SkeletonBlock className="h-40 w-full" />
    </div>
  );
}

export function ClaudeBoard() {
  const { data, fetchedAt, loading, error, notFound: missing, isFixture, refresh } = useLabDashboard();
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [openKey, setOpenKey] = useState<string | null>(null);

  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 30_000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => setNowMs(Date.now()), [fetchedAt]);

  const host = useMemo(() => parsePayload<HostPayload>(data?.host), [data]);
  const mac = useMemo(() => parsePayload<MacPayload>(data?.mac), [data]);
  const instances = useMemo(() => claudeInstances(mac), [mac]);

  const pick = (key: string) => {
    setOpenKey(key);
    requestAnimationFrame(() => {
      const el = document.getElementById(`row-${key}`);
      if (!el) return;
      const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest" });
    });
  };

  if (missing) return <LabNotFound />;
  if (loading && !data) return <LoadingView />;
  if (!data) return <ErrorState title="Couldn't load the lab" message={error ?? "Something went wrong."} />;

  const macFresh = snapshotFreshness(data.mac?.received_at, data.server_time, fetchedAt, nowMs, MAC_STALE_S);
  const activityError = mac?.activity?.error;
  const branch = mac?.activity?.branch;

  return (
    <div className="mx-auto max-w-6xl space-y-14 pb-10 sm:space-y-16">
      {isFixture ? (
        <div
          role="note"
          className="z-30 rounded-control border border-arepo-warn/50 md:sticky md:top-[72px] bg-[repeating-linear-gradient(135deg,#FBF3E4_0_10px,#F7EAD2_10px_20px)] px-4 py-2 text-center text-[12.5px] font-semibold uppercase tracking-wider text-arepo-warnText"
        >
          Fixture · local development data, not real results
        </div>
      ) : null}

      <header className="lab-rise space-y-6">
        <LabTabs current="claude" />
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
          <div className="min-w-0">
            <p className="section-label flex items-center gap-2">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-arepo-accent" /> Private · owner only · view only
            </p>
            <h1 className="display-hero mt-2 text-[40px] sm:text-[52px]">Claude</h1>
            <p className="mt-2 max-w-reading text-[15.5px] leading-relaxed text-arepo-ink2">
              What the unattended Claude sessions on the Mac are doing: which instance is working, how each session ended,
              what it reported, and the commits landing on the research branch.
            </p>
          </div>
          <p
            className={`flex items-center gap-1.5 text-[13px] ${macFresh.state === "stale" ? "text-arepo-warnText" : "text-arepo-muted"}`}
            aria-live="polite"
          >
            {macFresh.state === "missing"
              ? "Waiting for the Mac's first report"
              : macFresh.state === "stale"
                ? `▲ Out of date · Mac reported ${agoLabel(macFresh.ageSeconds)}`
                : `Mac reported ${agoLabel(macFresh.ageSeconds)}`}
            <button type="button" onClick={refresh} className="focus-ring ml-1 rounded px-1 text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline">
              Refresh
            </button>
          </p>
        </div>
        {error ? (
          <p className="rounded-control border border-arepo-warn/40 bg-arepo-warn/10 px-4 py-2 text-[13px] text-arepo-warnText" role="status">
            {error} Showing the last data received.
          </p>
        ) : null}
        {macFresh.state === "stale" ? (
          <p className="rounded-control border border-arepo-warn/40 bg-arepo-warn/10 px-4 py-2 text-[13px] text-arepo-warnText" role="status">
            The Mac last reported {agoLabel(macFresh.ageSeconds)} (it normally reports every 10 minutes); it may be asleep. Everything
            below is as of then.
          </p>
        ) : null}
      </header>

      {!mac ? (
        <Quiet>No report from the Mac yet. Once it sends one, the autopilot instances and their sessions appear here.</Quiet>
      ) : (
        <>
          <LabSection id="instances" eyebrow="Right now" title="Autopilot instances">
            {instances.length ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {instances.map((inst) => (
                  <InstanceCard key={inst.name ?? "main"} inst={inst} nowMs={nowMs} />
                ))}
              </div>
            ) : (
              <Quiet>The Mac report has no autopilot instances.</Quiet>
            )}
            {activityError ? (
              <p className="mt-3 text-[12.5px] text-arepo-muted">The Mac could not build the session list this time ({activityError}).</p>
            ) : null}
          </LabSection>

          <LabSection
            id="timeline"
            eyebrow={`Last ${TIMELINE_HOURS} hours`}
            title="Sessions over time"
            lead="Each bar is one session, coloured by how it ended. Select a bar to open its summary."
          >
            <div className="panel px-4 py-5 sm:px-6 sm:py-6">
              {instances.length ? <Timeline instances={instances} nowMs={nowMs} onPick={pick} /> : <Quiet>No sessions to draw.</Quiet>}
            </div>
          </LabSection>

          <LabSection
            id="sessions"
            eyebrow="What each session reported"
            title="Session log"
            lead="Newest first. Each session's closing line, with its full summary on open. Summaries are shortened and scrubbed of anything secret-looking on the Mac before they are sent."
          >
            <SessionLog instances={instances} nowMs={nowMs} openKey={openKey} setOpenKey={setOpenKey} />
          </LabSection>
        </>
      )}

      <LabSection
        id="commits"
        eyebrow="Live feed"
        title="Latest commits"
        lead={branch ? <>On the research branch <code className="font-mono text-[13px]">{branch}</code>.</> : "On the research branch."}
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CommitList mac={mac} nowMs={nowMs} />
          </Card>
          <ServerCard host={host} nowMs={nowMs} />
        </div>
      </LabSection>
    </div>
  );
}
