"use client";

import { useEffect, useId, useRef, useState } from "react";
import {
  ACTION_COPY,
  availableActions,
  dataSummary,
  displayName,
  emailMatches,
  type Member,
  type MemberActionKind,
  type MemberActionResult,
} from "@/lib/lab/members";
import { Pill } from "./primitives";

const joinedFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });

export function joinedLabel(iso: string | null | undefined): string {
  if (!iso) return "–";
  const t = Date.parse(iso);
  return Number.isFinite(t) ? joinedFmt.format(new Date(t)) : "–";
}

/** Shared column template: a card on mobile, a table-like row from md up. */
export const ROW_GRID = "md:grid md:grid-cols-[minmax(0,2.2fr)_minmax(0,1.6fr)_minmax(0,1.4fr)_minmax(0,0.9fr)_auto] md:items-center md:gap-4";

export function StatusPills({ m, self }: { m: Member; self: boolean }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {m.is_superuser ? <Pill tone="accent">Admin</Pill> : null}
      {m.is_verified ? <Pill tone="pos">Verified</Pill> : <Pill tone="warn">Unverified</Pill>}
      {m.is_active ? <Pill tone="muted">Active</Pill> : <Pill tone="neg">Suspended</Pill>}
      {self ? <Pill tone="neutral">You</Pill> : null}
    </div>
  );
}

function ConfirmStep({
  m,
  kind,
  onCancel,
  onDone,
  act,
}: {
  m: Member;
  kind: MemberActionKind;
  onCancel: () => void;
  onDone: (message: string) => void;
  act: (kind: MemberActionKind, id: string, confirmEmail?: string) => Promise<MemberActionResult>;
}) {
  const copy = ACTION_COPY[kind];
  const [typed, setTyped] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();
  const ready = !copy.typed || emailMatches(typed, m.email);

  async function submit() {
    if (!ready || pending) return;
    setPending(true);
    setError(null);
    const res = await act(kind, m.id, copy.typed ? typed.trim() : "");
    setPending(false);
    if (res.ok) onDone(copy.done(m));
    else setError(res.message);
  }

  return (
    <div
      role="group"
      aria-label={copy.label}
      className={`lab-rise rounded-control border p-3.5 ${
        copy.danger ? "border-arepo-accentBorder bg-arepo-accentTint/50" : "border-arepo-border bg-arepo-surface2/60"
      }`}
    >
      <p className="break-words text-[13.5px] font-semibold text-arepo-ink">{copy.title(m)}</p>
      <p className="mt-0.5 text-[12.5px] leading-relaxed text-arepo-ink2">{copy.body}</p>
      <form
        className="mt-3 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {copy.typed ? (
          <div>
            <label htmlFor={inputId} className="block text-[12.5px] font-medium text-arepo-ink2">
              Type <span className="break-all font-semibold text-arepo-ink">{m.email}</span> to confirm
            </label>
            <input
              id={inputId}
              type="email"
              autoComplete="off"
              spellCheck={false}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              disabled={pending}
              autoFocus
              className="mt-1.5 w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-2 text-[14px] text-arepo-ink placeholder:text-arepo-muted"
              placeholder={m.email}
            />
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <button type="submit" className="btn btn-primary" disabled={!ready || pending} autoFocus={!copy.typed}>
            {pending ? "Working…" : copy.confirm}
          </button>
          <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={pending}>
            Cancel
          </button>
        </div>
      </form>
      {error ? (
        <p className="mt-2 text-[12.5px] text-arepo-neg" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function MemberRow({
  m,
  meId,
  open,
  onToggle,
  onDone,
  act,
}: {
  m: Member;
  meId: string | null;
  open: boolean;
  onToggle: () => void;
  onDone: (message: string) => void;
  act: (kind: MemberActionKind, id: string, confirmEmail?: string) => Promise<MemberActionResult>;
}) {
  const self = meId !== null && m.id === meId;
  const name = displayName(m);
  const actions = availableActions(m, meId);
  const [confirming, setConfirming] = useState<MemberActionKind | null>(null);
  const panelId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) setConfirming(null);
  }, [open]);

  return (
    <li className="rounded-card border border-arepo-border bg-arepo-surface p-4 md:rounded-none md:border-0 md:border-t md:bg-transparent md:px-2 md:py-3.5 md:first:border-t-0">
      <div className={`flex flex-col gap-3 ${ROW_GRID}`}>
        <div className="min-w-0">
          <p className="truncate text-[14.5px] font-semibold text-arepo-ink" title={name || m.email}>
            {name || m.email}
          </p>
          {name ? (
            <p className="truncate text-[13px] text-arepo-muted" title={m.email}>
              {m.email}
            </p>
          ) : null}
        </div>
        <StatusPills m={m} self={self} />
        <p className="text-[13px] text-arepo-ink2">
          <span className="text-arepo-muted md:hidden">Saved data: </span>
          {dataSummary(m.data)}
        </p>
        <p className="font-tabular text-[13px] text-arepo-ink2">
          <span className="text-arepo-muted md:hidden">Joined </span>
          {joinedLabel(m.created_at)}
        </p>
        <div className="md:justify-self-end">
          <button
            ref={toggleRef}
            type="button"
            className="btn btn-secondary w-full md:w-auto"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={onToggle}
          >
            Manage
            <svg aria-hidden="true" viewBox="0 0 12 12" className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}>
              <path d="M2.5 4.5L6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>
      {open ? (
        <div id={panelId} className="mt-3 md:mt-3.5">
          {confirming ? (
            <ConfirmStep
              m={m}
              kind={confirming}
              act={act}
              onCancel={() => {
                setConfirming(null);
              }}
              onDone={(message) => {
                setConfirming(null);
                onDone(message);
                toggleRef.current?.focus();
              }}
            />
          ) : (
            <div className="rounded-control border border-arepo-border bg-arepo-surface2/50 p-3">
              {actions.length ? (
                <ul className="flex flex-wrap gap-2" aria-label={`Actions for ${m.email}`}>
                  {actions.map((k) => (
                    <li key={k}>
                      <button
                        type="button"
                        onClick={() => setConfirming(k)}
                        className={`btn btn-secondary text-[13px] ${
                          ACTION_COPY[k].danger ? "text-arepo-accentActive hover:border-arepo-accentBorder" : ""
                        }`}
                      >
                        {ACTION_COPY[k].label}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12.5px] text-arepo-muted">No actions available.</p>
              )}
              {self ? (
                <p className="mt-2.5 text-[12px] text-arepo-muted">
                  This is your account. You can&apos;t suspend, delete or remove admin from yourself here.
                </p>
              ) : m.is_superuser ? (
                <p className="mt-2.5 text-[12px] text-arepo-muted">Revoke admin first to suspend or delete this account.</p>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </li>
  );
}
