"use client";

import { useState } from "react";
import { postLabCommand } from "@/lib/lab/api";
import {
  agoLabel,
  commandStepLabel,
  IN_FLIGHT,
  latestCommand,
  outcomeTone,
  type Freshness,
  type Tone,
} from "@/lib/lab/model";
import type {
  AutopilotBlock,
  CommandAction,
  CommandTarget,
  InfraBlock,
  LabCommand,
} from "@/lib/lab/types";
import { theme } from "@/lib/theme";
import { Card, Dot, Pill, ProgressBar, Quiet, TONE_COLOR } from "./primitives";

// ---------------------------------------------------------------------------------------------
// Gauges and sparklines (clean SVG)

function Gauge({ used, total, unit, label }: { used: number; total: number; unit: string; label: string }) {
  const pct = total > 0 ? Math.max(0, Math.min(100, (used / total) * 100)) : 0;
  const colour = pct >= 90 ? theme.neg : pct >= 80 ? theme.warn : theme.ink2;
  const arc = "M10,60 A50,50 0 0 1 110,60";
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 68" className="w-full max-w-[150px]" role="img" aria-label={`${label}: ${Math.round(pct)}% used, ${used.toFixed(1)} of ${total.toFixed(0)} ${unit}`}>
        <path d={arc} fill="none" stroke={theme.surface2} strokeWidth={10} strokeLinecap="round" />
        <path
          d={arc}
          fill="none"
          stroke={colour}
          strokeWidth={10}
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={`${pct} 100`}
          style={{ transition: "stroke-dasharray 700ms ease" }}
        />
        <text x="60" y="54" textAnchor="middle" fontSize="20" fontWeight="600" fill={theme.ink} style={{ fontVariantNumeric: "tabular-nums" }}>
          {Math.round(pct)}%
        </text>
      </svg>
      <p className="-mt-0.5 text-[12.5px] font-medium text-arepo-ink2">{label}</p>
      <p className="font-tabular text-[11.5px] text-arepo-muted">
        {used.toFixed(1)} / {total.toFixed(0)} {unit}
      </p>
    </div>
  );
}

function Sparkline({ values, label }: { values: number[]; label: string }) {
  const pts = values.filter((v) => Number.isFinite(v));
  if (pts.length < 2) return null;
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const span = max - min || 1;
  const d = pts
    .map((v, i) => `${i === 0 ? "M" : "L"}${((i / (pts.length - 1)) * 100).toFixed(2)},${(26 - ((v - min) / span) * 22).toFixed(2)}`)
    .join(" ");
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="mt-2 h-7 w-full max-w-[150px]" role="img" aria-label={`${label}: from ${pts[0]} to ${pts[pts.length - 1]}`}>
      <title>{label}</title>
      <path d={d} fill="none" stroke={theme.series2} strokeWidth={1.5} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

function StatusRow({ tone, label, value }: { tone: Tone; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 text-[13px]">
      <span className="flex items-center gap-2 text-arepo-ink2">
        <Dot tone={tone} />
        {label}
      </span>
      <span className="text-right text-arepo-muted">{value}</span>
    </div>
  );
}

function since(iso: string | null | undefined, nowMs: number): string {
  const t = iso ? Date.parse(iso) : NaN;
  return Number.isNaN(t) ? "unknown" : agoLabel((nowMs - t) / 1000);
}

export function HostCard({ infra, fresh, nowMs }: { infra: InfraBlock | undefined; fresh: Freshness; nowMs: number }) {
  return (
    <Card>
      <MachineHeader name="Research host" fresh={fresh} />
      {!infra ? (
        <div className="mt-4">
          <Quiet>No infrastructure figures in the latest snapshot.</Quiet>
        </div>
      ) : (
        <>
          <div className="mt-5 grid grid-cols-2 gap-4">
            <div className="flex flex-col items-center">
              {typeof infra.disk_free_gb === "number" && typeof infra.disk_total_gb === "number" ? (
                <Gauge used={infra.disk_total_gb - infra.disk_free_gb} total={infra.disk_total_gb} unit="GB" label="Disk" />
              ) : (
                <p className="text-[12px] text-arepo-muted">Disk: unknown</p>
              )}
              <Sparkline values={(infra.history ?? []).map((h) => h.disk_free_gb ?? NaN)} label="Disk free over time (GB)" />
            </div>
            <div className="flex flex-col items-center">
              {typeof infra.mem_available_mb === "number" && typeof infra.mem_total_mb === "number" ? (
                <Gauge
                  used={(infra.mem_total_mb - infra.mem_available_mb) / 1024}
                  total={infra.mem_total_mb / 1024}
                  unit="GB"
                  label="Memory"
                />
              ) : (
                <p className="text-[12px] text-arepo-muted">Memory: unknown</p>
              )}
              <Sparkline values={(infra.history ?? []).map((h) => h.mem_available_mb ?? NaN)} label="Memory available over time (MB)" />
            </div>
          </div>
          <div className="mt-4 divide-y divide-arepo-border border-t border-arepo-border">
            <StatusRow
              tone={infra.collector_ok === false ? "neg" : infra.collector_ok ? "pos" : "muted"}
              label="Live collector"
              value={infra.collector_ok === false ? `Failing · last ok ${since(infra.collector_last_ok, nowMs)}` : `OK · ${since(infra.collector_last_ok, nowMs)}`}
            />
            {typeof infra.data_gb === "number" ? (
              <div className="py-2.5 text-[13px]">
                <div className="mb-1.5 flex justify-between gap-3">
                  <span className="text-arepo-ink2">Research data</span>
                  <span className="font-tabular text-arepo-muted">
                    {infra.data_gb.toFixed(1)}
                    {infra.data_cap_gb ? ` / ${infra.data_cap_gb} GB cap` : " GB"}
                  </span>
                </div>
                {infra.data_cap_gb ? (
                  <ProgressBar value={infra.data_gb} max={infra.data_cap_gb} label="Research data used against its cap" tone="neutral" />
                ) : null}
              </div>
            ) : null}
            {infra.second_server ? (
              <StatusRow
                tone={infra.second_server.status === "created" ? "pos" : "warn"}
                label="Second server"
                value={
                  infra.second_server.status === "created"
                    ? "Created"
                    : `${infra.second_server.status ?? "unknown"}${
                        typeof infra.second_server.attempts === "number" ? ` · ${infra.second_server.attempts} attempts` : ""
                      }${infra.second_server.last_try ? ` · ${since(infra.second_server.last_try, nowMs)}` : ""}`
                }
              />
            ) : null}
          </div>
        </>
      )}
    </Card>
  );
}

function MachineHeader({ name, fresh }: { name: string; fresh: Freshness }) {
  const tone: Tone = fresh.state === "fresh" ? "pos" : fresh.state === "stale" ? "warn" : "muted";
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-[15px] font-semibold text-arepo-ink">{name}</h3>
      <span className="inline-flex items-center gap-1.5 text-[12px] text-arepo-muted">
        <Dot tone={tone} />
        {fresh.state === "missing" ? "No report yet" : `${fresh.state === "stale" ? "Stale · " : ""}reported ${agoLabel(fresh.ageSeconds)}`}
      </span>
    </div>
  );
}

export function AutopilotCard({ autopilot, fresh, nowMs }: { autopilot: AutopilotBlock | undefined; fresh: Freshness; nowMs: number }) {
  const state = !autopilot
    ? null
    : autopilot.paused
      ? { label: "Paused", tone: "warn" as Tone }
      : autopilot.session_alive
        ? { label: "Working", tone: "pos" as Tone }
        : { label: "Idle between sessions", tone: "neutral" as Tone };
  const recent = [...(autopilot?.recent ?? [])].filter((r) => r?.at).sort((a, b) => Date.parse(a.at ?? "") - Date.parse(b.at ?? "")).slice(-12);
  return (
    <Card>
      <MachineHeader name="Autopilot (Mac)" fresh={fresh} />
      {!autopilot || !state ? (
        <div className="mt-4">
          <Quiet>No autopilot report yet.</Quiet>
        </div>
      ) : (
        <>
          <div className="mt-5 flex items-center gap-3">
            <span className="relative flex h-12 w-12 items-center justify-center rounded-full bg-arepo-surface2">
              <Dot tone={state.tone} pulse={state.tone === "pos"} size={12} />
            </span>
            <div>
              <p className="font-display text-[20px] font-semibold leading-tight text-arepo-ink">{state.label}</p>
              <p className="text-[12.5px] text-arepo-muted">
                {autopilot.paused && autopilot.pause_reason
                  ? autopilot.pause_reason
                  : autopilot.session_alive && autopilot.started_at
                    ? `Session started ${since(autopilot.started_at, nowMs)}`
                    : autopilot.next_allowed
                      ? `Next session allowed ${new Date(autopilot.next_allowed).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`
                      : "Claude research sessions on the Mac"}
              </p>
            </div>
          </div>
          {recent.length ? (
            <div className="mt-5">
              <p className="mb-2 text-[12px] text-arepo-muted">Recent sessions</p>
              <ol className="flex h-7 items-stretch gap-1" aria-label="Recent autopilot sessions, oldest to newest">
                {recent.map((r, i) => {
                  const tone = outcomeTone(r.outcome);
                  const label = `${r.outcome ?? "unknown"}${typeof r.runtime_s === "number" ? `, ${(r.runtime_s / 3600).toFixed(1)} h` : ""}, ${since(r.at, nowMs)}`;
                  return (
                    <li
                      key={i}
                      title={label}
                      aria-label={label}
                      className="flex-1 rounded-[4px]"
                      style={{ background: TONE_COLOR[tone], opacity: tone === "pos" ? 0.75 : 1, maxWidth: 48 }}
                    />
                  );
                })}
              </ol>
            </div>
          ) : null}
          <div className="mt-4 divide-y divide-arepo-border border-t border-arepo-border">
            {autopilot.last_outcome ? (
              <StatusRow tone={outcomeTone(autopilot.last_outcome)} label="Last session ended" value={autopilot.last_outcome.replace(/_/g, " ")} />
            ) : null}
          </div>
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------------------------
// Controls

function CommandSteps({ cmd }: { cmd: LabCommand }) {
  // Steps: Requested -> Delivered -> Done. `reached` is the last completed step; a failed or
  // expired command ends on a red/grey terminal step instead of Done.
  const reached = { pending: 0, delivered: 1, done: 2, failed: 1, expired: 0 }[cmd.status] ?? 0;
  const bad = cmd.status === "failed" || cmd.status === "expired";
  const labels = ["Requested", "Delivered", cmd.status === "failed" ? "Failed" : cmd.status === "expired" ? "Expired" : "Done"];
  return (
    <div>
      <ol className="flex flex-wrap items-center gap-1.5" aria-label={`${cmd.action} ${cmd.target}: ${commandStepLabel(cmd.status)}`}>
        {labels.map((l, i) => {
          const isLast = i === labels.length - 1;
          const complete = i <= reached;
          const waiting = IN_FLIGHT.has(cmd.status) && i === reached + 1;
          const cls =
            bad && isLast
              ? cmd.status === "failed"
                ? "bg-arepo-neg/10 text-arepo-neg"
                : "bg-arepo-surface2 text-arepo-muted"
              : complete
                ? "bg-arepo-pos/10 text-arepo-pos"
                : waiting
                  ? "bg-arepo-accentTint text-arepo-accentActive"
                  : "bg-arepo-surface2 text-arepo-muted";
          return (
            <li key={l} className="flex items-center gap-1.5">
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls}`}>
                {complete && !(bad && isLast) ? <span aria-hidden="true">✓</span> : null}
                {waiting ? <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" /> : null}
                {l}
              </span>
              {!isLast ? <span aria-hidden="true" className="h-px w-3 bg-arepo-borderStrong" /> : null}
            </li>
          );
        })}
      </ol>
      <p className="mt-1.5 text-[11.5px] text-arepo-muted">
        <span className="capitalize">{cmd.action}</span> · {commandStepLabel(cmd.status)}
        {cmd.result ? ` · ${cmd.result}` : ""}
      </p>
    </div>
  );
}

const CONTROL_COPY: Record<CommandTarget, { title: string; pause: string; resume: string; cadence: string }> = {
  queue: {
    title: "Research queue",
    pause: "Running jobs finish; nothing new starts.",
    resume: "The host starts taking queued jobs again.",
    cadence: "The host checks for commands about every 10 minutes.",
  },
  autopilot: {
    title: "Claude autopilot",
    pause: "No new research sessions start on the Mac.",
    resume: "The Mac may start research sessions again.",
    cadence: "The Mac checks for commands about every 30 minutes.",
  },
};

function ControlRow({
  target,
  paused,
  latest,
  onSent,
  simulate = false,
}: {
  target: CommandTarget;
  paused: boolean | undefined;
  latest: LabCommand | null;
  onSent: (cmd: LabCommand | null) => void;
  simulate?: boolean;
}) {
  const [confirming, setConfirming] = useState<CommandAction | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const copy = CONTROL_COPY[target];
  const inFlight = latest && IN_FLIGHT.has(latest.status) ? latest : null;
  const stateLabel = paused === true ? "Paused" : paused === false ? "Running" : "Unknown";
  const stateTone: Tone = paused === true ? "warn" : paused === false ? "pos" : "muted";
  // Offer the action that changes the reported state; when the state is unknown offer both.
  const actions: CommandAction[] = paused === true ? ["resume"] : paused === false ? ["pause"] : ["pause", "resume"];

  async function send(action: CommandAction) {
    setSending(true);
    setError(null);
    // Fixture (dev only): never POST; fabricate a local pending command so the flow can be seen.
    const res = simulate
      ? {
          ok: true as const,
          command: { id: Date.now(), target, action, status: "pending", created_at: new Date().toISOString() },
        }
      : await postLabCommand(target, action);
    setSending(false);
    if (res.ok) {
      setConfirming(null);
      onSent(res.command);
    } else {
      setError(res.message);
    }
  }

  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[14.5px] font-semibold text-arepo-ink">{copy.title}</p>
          <p className="mt-0.5 flex items-center gap-1.5 text-[12.5px] text-arepo-muted">
            <Dot tone={stateTone} /> {stateLabel}
            {inFlight ? <span className="text-arepo-ink2"> · {inFlight.action} requested</span> : null}
          </p>
        </div>
        {!confirming ? (
          <div className="flex gap-2">
            {actions.map((a) => (
              <button key={a} type="button" className="btn btn-secondary" onClick={() => setConfirming(a)} disabled={sending}>
                {a === "pause" ? "Pause" : "Resume"}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      {confirming ? (
        <div className="lab-rise mt-3 rounded-control border border-arepo-accentBorder bg-arepo-accentTint/50 p-3.5" role="group" aria-label={`Confirm ${confirming}`}>
          <p className="text-[13.5px] font-semibold text-arepo-ink">
            {confirming === "pause" ? "Pause" : "Resume"} the {copy.title.toLowerCase()}?
          </p>
          <p className="mt-0.5 text-[12.5px] leading-relaxed text-arepo-ink2">
            {confirming === "pause" ? copy.pause : copy.resume} {copy.cadence}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="btn btn-primary" onClick={() => void send(confirming)} disabled={sending} autoFocus>
              {sending ? "Sending…" : `Yes, ${confirming}`}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setConfirming(null)} disabled={sending}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      {error ? (
        <p className="mt-2 text-[12.5px] text-arepo-neg" role="alert">
          {error}
        </p>
      ) : null}
      {latest ? (
        <div className="mt-3">
          <CommandSteps cmd={latest} />
        </div>
      ) : null}
    </div>
  );
}

export function Controls({
  commands,
  queuePaused,
  autopilotPaused,
  onSent,
  nowMs,
  simulate = false,
}: {
  commands: LabCommand[];
  queuePaused: boolean | undefined;
  autopilotPaused: boolean | undefined;
  onSent: (cmd: LabCommand | null) => void;
  nowMs: number;
  /** Fixture mode: commands are simulated locally and never sent. */
  simulate?: boolean;
}) {
  const history = commands.slice(0, 6);
  return (
    <Card>
      <h3 className="text-[15px] font-semibold text-arepo-ink">Controls</h3>
      <p className="mb-5 mt-0.5 text-[12.5px] text-arepo-muted">
        Commands wait on the server until the machine picks them up; unclaimed commands expire after 2 hours.
      </p>
      {simulate ? (
        <p className="mb-4 rounded-control bg-arepo-warn/10 px-3 py-2 text-[12px] text-arepo-warnText">
          Fixture: commands are simulated in this browser and never sent.
        </p>
      ) : null}
      <div className="divide-y divide-arepo-border">
        <ControlRow target="queue" paused={queuePaused} latest={latestCommand(commands, "queue")} onSent={onSent} simulate={simulate} />
        <ControlRow
          target="autopilot"
          paused={autopilotPaused}
          latest={latestCommand(commands, "autopilot")}
          onSent={onSent}
          simulate={simulate}
        />
      </div>
      {history.length ? (
        <details className="disclose mt-5 border-t border-arepo-border pt-3">
          <summary className="focus-ring">Command history</summary>
          <ul className="mt-2 space-y-1.5">
            {history.map((c) => (
              <li key={c.id} className="flex flex-wrap items-baseline justify-between gap-x-3 text-[12.5px]">
                <span className="text-arepo-ink2">
                  {c.action} {c.target}
                </span>
                <span className="text-arepo-muted">
                  <Pill tone={c.status === "done" ? "pos" : c.status === "failed" ? "neg" : IN_FLIGHT.has(c.status) ? "accent" : "muted"}>
                    {c.status}
                  </Pill>{" "}
                  {since(c.created_at, nowMs)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </Card>
  );
}
