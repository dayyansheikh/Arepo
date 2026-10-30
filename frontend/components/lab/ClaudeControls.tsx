"use client";

import { useState } from "react";
import { cancelLabMessage, postLabCommand, postLabMessage } from "@/lib/lab/api";
import {
  instanceState,
  instanceTargets,
  latestFor,
  MESSAGE_STEPS,
  messageProgress,
  ms,
  relLabel,
  startState,
} from "@/lib/lab/claude";
import { commandStepLabel, IN_FLIGHT } from "@/lib/lab/model";
import type { AnyCommandTarget, ClaudeInstance, CommandAction, LabCommand, LabMessage } from "@/lib/lab/types";
import { Card, Dot, Pill } from "./primitives";

const MAX_CHARS = 4000;

function Steps({ labels, reached, bad, waiting }: { labels: readonly string[]; reached: number; bad: string | null; waiting: boolean }) {
  return (
    <ol className="flex flex-wrap items-center gap-1.5">
      {labels.map((l, i) => {
        const complete = i <= reached && !(bad && i > 0);
        const isNext = waiting && i === reached + 1;
        const cls = complete
          ? "bg-arepo-pos/10 text-arepo-pos"
          : isNext
            ? "bg-arepo-accentTint text-arepo-accentActive"
            : "bg-arepo-surface2 text-arepo-muted";
        return (
          <li key={l} className="flex items-center gap-1.5">
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls}`}>
              {complete ? <span aria-hidden="true">✓</span> : null}
              {isNext ? <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" /> : null}
              {l}
            </span>
            {i < labels.length - 1 ? <span aria-hidden="true" className="h-px w-3 bg-arepo-borderStrong" /> : null}
          </li>
        );
      })}
      {bad ? (
        <li>
          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${bad === "failed" ? "bg-arepo-neg/10 text-arepo-neg" : "bg-arepo-surface2 text-arepo-muted"}`}>
            {bad === "failed" ? "Failed" : bad === "expired" ? "Expired" : "Cancelled"}
          </span>
        </li>
      ) : null}
    </ol>
  );
}

// ---------------------------------------------------------------------------------------------
// Messages

function MessageItem({
  m,
  title,
  nowMs,
  onChange,
  simulate,
}: {
  m: LabMessage;
  title: string;
  nowMs: number;
  onChange: (m: LabMessage) => void;
  simulate: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const p = messageProgress(m);
  const long = m.body.length > 180 || m.body.includes("\n");
  async function cancel() {
    setBusy(true);
    setError(null);
    const r = simulate ? { ok: true as const, message: { ...m, status: "cancelled" } } : await cancelLabMessage(m.id);
    setBusy(false);
    if (r.ok) onChange(r.message ?? { ...m, status: "cancelled" });
    else setError(r.message);
  }
  return (
    <li className="py-3.5 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-[12px] text-arepo-muted">
        <span>
          To <span className="font-medium text-arepo-ink2">{title}</span> · {relLabel(ms(m.created_at), nowMs)}
        </span>
        {m.status === "pending" ? (
          <button type="button" onClick={() => void cancel()} disabled={busy} className="focus-ring rounded px-1 text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline">
            {busy ? "Cancelling…" : "Cancel"}
          </button>
        ) : null}
      </div>
      <p className={`mt-1 whitespace-pre-wrap text-[13.5px] leading-snug text-arepo-ink [overflow-wrap:anywhere] ${open ? "" : "line-clamp-2"}`}>{m.body}</p>
      {long ? (
        <button type="button" onClick={() => setOpen(!open)} className="focus-ring mt-0.5 rounded px-1 text-[12px] text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline" aria-expanded={open}>
          {open ? "Show less" : "Show all"}
        </button>
      ) : null}
      <div className="mt-2">
        <Steps labels={MESSAGE_STEPS} reached={p.reached} bad={p.bad} waiting={!p.bad && p.reached < 2} />
        <p className="mt-1 text-[11.5px] text-arepo-muted">
          {p.label}
          {m.result && (m.status === "failed" || m.status === "read") ? ` (${m.result})` : ""}
        </p>
      </div>
      {error ? (
        <p className="mt-1 text-[12px] text-arepo-neg" role="alert">
          {error}
        </p>
      ) : null}
    </li>
  );
}

export function MessagePanel({
  instances,
  messages,
  limits,
  nowMs,
  onMessage,
  simulate = false,
}: {
  instances: ClaudeInstance[];
  messages: LabMessage[];
  limits?: { message_max_chars?: number; messages_per_day?: number; messages_last_24h?: number };
  nowMs: number;
  onMessage: (m: LabMessage) => void;
  simulate?: boolean;
}) {
  const targets = instanceTargets(instances);
  const [target, setTarget] = useState(targets[0]?.key ?? "autopilot");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const max = limits?.message_max_chars ?? MAX_CHARS;
  const perDay = limits?.messages_per_day ?? 20;
  const used = limits?.messages_last_24h;
  const titleOf = (key: string) => targets.find((t) => t.key === key)?.title ?? key;
  const trimmed = body.trim();

  async function send() {
    if (!trimmed || trimmed.length > max) return;
    setSending(true);
    setError(null);
    const r = simulate
      ? { ok: true as const, message: { id: Date.now(), target, body: trimmed, status: "pending", created_at: new Date().toISOString() } }
      : await postLabMessage(target, trimmed);
    setSending(false);
    if (r.ok) {
      setBody("");
      if (r.message) onMessage(r.message);
    } else setError(r.message);
  }

  const shown = showAll ? messages : messages.slice(0, 5);
  return (
    <Card>
      <h3 className="text-[15px] font-semibold text-arepo-ink">Send Claude a message</h3>
      <p className="mt-0.5 text-[12.5px] leading-relaxed text-arepo-muted">
        The Mac puts it in that autopilot&apos;s inbox (INBOX.md) within about 10 minutes; Claude reads it first thing in its next session and
        treats it as your instruction for that session.
      </p>
      {simulate ? (
        <p className="mt-3 rounded-control bg-arepo-warn/10 px-3 py-2 text-[12px] text-arepo-warnText">Fixture: messages are simulated in this browser and never sent.</p>
      ) : null}
      <form
        className="mt-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <div role="radiogroup" aria-label="Send to" className="flex flex-wrap gap-2">
          {targets.map((t) => (
            <button
              key={t.key}
              type="button"
              role="radio"
              aria-checked={target === t.key}
              onClick={() => setTarget(t.key)}
              className={`focus-ring rounded-full border px-3 py-1 text-[12.5px] transition-colors ${
                target === t.key ? "border-arepo-ink bg-arepo-ink text-white" : "border-arepo-border bg-arepo-surface text-arepo-ink2 hover:bg-arepo-surface2"
              }`}
            >
              {t.title}
            </button>
          ))}
        </div>
        <label className="block">
          <span className="sr-only">Message</span>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={4}
            maxLength={max}
            placeholder="e.g. Finish the CB18 census before starting anything new, and keep the summary to one plain sentence."
            className="w-full resize-y rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-2 text-[14px] leading-relaxed text-arepo-ink placeholder:text-arepo-muted"
          />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="font-tabular text-[12px] text-arepo-muted">
            {body.length.toLocaleString("en-GB")} / {max.toLocaleString("en-GB")}
            {typeof used === "number" ? ` · ${used} of ${perDay} messages used in the last 24 h` : ` · up to ${perDay} a day`}
          </p>
          <button type="submit" className="btn btn-primary" disabled={sending || !trimmed}>
            {sending ? "Sending…" : `Send to ${titleOf(target)}`}
          </button>
        </div>
        {error ? (
          <p className="text-[12.5px] text-arepo-neg" role="alert">
            {error}
          </p>
        ) : null}
      </form>
      <div className="mt-6 border-t border-arepo-border pt-4">
        <h4 className="text-[12px] font-semibold uppercase tracking-wider text-arepo-muted">Inbox history</h4>
        {messages.length ? (
          <>
            <ol className="mt-3 divide-y divide-arepo-border">
              {shown.map((m) => (
                <MessageItem key={m.id} m={m} title={titleOf(m.target)} nowMs={nowMs} onChange={onMessage} simulate={simulate} />
              ))}
            </ol>
            {messages.length > shown.length ? (
              <button type="button" onClick={() => setShowAll(true)} className="focus-ring mt-2 rounded px-1 text-[12.5px] text-arepo-ink2 underline-offset-2 hover:underline">
                Show all {messages.length} messages
              </button>
            ) : null}
          </>
        ) : (
          <p className="mt-2 text-[13px] text-arepo-muted">No messages sent yet.</p>
        )}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------------------------
// Pause / resume / start now, per instance

const ACTION_COPY: Record<CommandAction, { verb: string; explain: string }> = {
  pause: { verb: "Pause", explain: "No new sessions start; a running session finishes normally." },
  resume: { verb: "Resume", explain: "Sessions start again at the half-hourly checks (usage limits still apply)." },
  start: { verb: "Start a session now", explain: "" },
};

function CommandLine({ cmd }: { cmd: LabCommand }) {
  const reached = { pending: 0, delivered: 1, done: 2, failed: 1, expired: 0 }[cmd.status] ?? 0;
  const bad = cmd.status === "failed" ? "failed" : cmd.status === "expired" ? "expired" : null;
  const word = cmd.action === "start" ? "start now" : cmd.action;
  return (
    <div className="mt-2">
      <Steps labels={["Requested", "Delivered", "Done"]} reached={bad ? Math.min(reached, 1) : reached} bad={bad} waiting={IN_FLIGHT.has(cmd.status)} />
      <p className="mt-1 text-[11.5px] text-arepo-muted">
        Last command: {word} · {cmd.status === "expired" ? "expired (the Mac did not pick it up within 2 hours)" : commandStepLabel(cmd.status)}
        {cmd.result ? ` · ${cmd.result}` : ""}
      </p>
    </div>
  );
}

function InstanceControl({
  inst,
  target,
  title,
  latest,
  nowMs,
  onSent,
  simulate,
}: {
  inst: ClaudeInstance | null;
  target: string;
  title: string;
  latest: LabCommand | null;
  nowMs: number;
  onSent: (c: LabCommand) => void;
  simulate: boolean;
}) {
  const [confirming, setConfirming] = useState<CommandAction | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const st = inst ? instanceState(inst, nowMs) : null;
  const start = inst ? startState(inst, nowMs) : { ok: false, why: "No report for this instance yet." };
  const paused = inst?.paused;
  const inFlight = latest && IN_FLIGHT.has(latest.status);

  async function send(action: CommandAction) {
    setSending(true);
    setError(null);
    const r = simulate
      ? { ok: true as const, command: { id: Date.now(), target, action, status: "pending", created_at: new Date().toISOString() } }
      : await postLabCommand(target as AnyCommandTarget, action);
    setSending(false);
    if (r.ok) {
      setConfirming(null);
      if (r.command) onSent(r.command);
    } else setError(r.message);
  }

  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[14.5px] font-semibold text-arepo-ink">{title}</p>
          <p className="mt-0.5 flex items-center gap-1.5 text-[12.5px] text-arepo-muted">
            {st ? <Dot tone={st.tone} /> : null} {st?.label ?? "Unknown"}
            {inFlight ? <span className="text-arepo-ink2"> · {latest!.action === "start" ? "start" : latest!.action} requested</span> : null}
          </p>
        </div>
        {!confirming ? (
          <div className="flex flex-wrap gap-2">
            {paused ? (
              <button type="button" className="btn btn-secondary" onClick={() => setConfirming("resume")} disabled={sending}>
                Resume
              </button>
            ) : (
              <button type="button" className="btn btn-secondary" onClick={() => setConfirming("pause")} disabled={sending}>
                Pause
              </button>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setConfirming("start")}
              disabled={sending || !start.ok}
              title={start.ok ? undefined : start.why}
            >
              Start now
            </button>
          </div>
        ) : null}
      </div>
      {!start.ok && !confirming ? <p className="mt-1 text-[11.5px] text-arepo-muted">Start now: {start.why}</p> : null}
      {confirming ? (
        <div className="lab-rise mt-3 rounded-control border border-arepo-accentBorder bg-arepo-accentTint/50 p-3.5" role="group" aria-label={`Confirm ${confirming}`}>
          <p className="text-[13.5px] font-semibold text-arepo-ink">
            {ACTION_COPY[confirming].verb} — {title}?
          </p>
          <p className="mt-0.5 text-[12.5px] leading-relaxed text-arepo-ink2">
            {confirming === "start" ? start.why : ACTION_COPY[confirming].explain} The Mac checks for commands about every 10 minutes.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="btn btn-primary" onClick={() => void send(confirming)} disabled={sending} autoFocus>
              {sending ? "Sending…" : `Yes, ${confirming === "start" ? "start" : confirming}`}
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
      {latest ? <CommandLine cmd={latest} /> : null}
    </div>
  );
}

export function ControlPanel({
  instances,
  commands,
  nowMs,
  onSent,
  simulate = false,
}: {
  instances: ClaudeInstance[];
  commands: LabCommand[];
  nowMs: number;
  onSent: (c: LabCommand) => void;
  simulate?: boolean;
}) {
  const targets = instanceTargets(instances);
  return (
    <Card>
      <h3 className="text-[15px] font-semibold text-arepo-ink">Controls</h3>
      <p className="mb-5 mt-0.5 text-[12.5px] text-arepo-muted">
        Pause, resume or start each autopilot. Start never skips a pause or a usage limit. Unclaimed commands expire after 2 hours.
      </p>
      {simulate ? (
        <p className="mb-4 rounded-control bg-arepo-warn/10 px-3 py-2 text-[12px] text-arepo-warnText">Fixture: commands are simulated in this browser and never sent.</p>
      ) : null}
      <div className="divide-y divide-arepo-border">
        {targets.map((t) => (
          <InstanceControl
            key={t.key}
            inst={t.inst}
            target={t.key}
            title={t.title}
            latest={latestFor(commands, t.key)}
            nowMs={nowMs}
            onSent={onSent}
            simulate={simulate}
          />
        ))}
      </div>
      <p className="mt-4 border-t border-arepo-border pt-3 text-[11.5px] text-arepo-muted">
        <Pill tone="muted">Needs your security key</Pill> Every control and message requires the unlocked owner session.
      </p>
    </Card>
  );
}
