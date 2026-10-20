"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { SkeletonBlock } from "@/components/Skeletons";
import { ErrorState } from "@/components/ErrorState";
import { agoLabel } from "@/lib/lab/model";
import {
  auditSentence,
  filterCounts,
  filterMembers,
  type AuditEntry,
  type MemberFilter,
} from "@/lib/lab/members";
import { useMembers } from "@/lib/lab/use-members";
import { useAuth } from "@/lib/auth-context";
import { Revealed, UnlockScreen } from "@/components/security/UnlockScreen";
import { LabTabs } from "./LabTabs";
import { MemberRow, ROW_GRID } from "./MemberRow";
import { fmtCount, LabNotFound, LabSection, Quiet } from "./primitives";

const FILTERS: Array<{ key: MemberFilter; label: string }> = [
  { key: "all", label: "All" },
  { key: "admins", label: "Admins" },
  { key: "unverified", label: "Unverified" },
  { key: "suspended", label: "Suspended" },
];

function FilterChip({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`focus-ring inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-[12.5px] font-medium transition-colors ${
        active
          ? "border-arepo-ink bg-arepo-ink text-white"
          : "border-arepo-border bg-arepo-surface text-arepo-ink2 hover:border-arepo-borderStrong hover:bg-arepo-surface2"
      }`}
    >
      {label}
      <span className={`font-tabular text-[11px] ${active ? "text-white/70" : "text-arepo-muted"}`}>{count}</span>
    </button>
  );
}

type Toast = { id: number; tone: "ok" | "error"; text: string };

function ToastRegion({ toast, onClose }: { toast: Toast | null; onClose: () => void }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-4 bottom-4 z-40 flex justify-center sm:inset-x-auto sm:right-6 sm:justify-end"
    >
      {toast ? (
        <div
          key={toast.id}
          className={`lab-rise pointer-events-auto flex max-w-sm items-start gap-3 rounded-card border px-4 py-3 text-[13.5px] shadow-arepo-hover ${
            toast.tone === "ok"
              ? "border-arepo-border bg-arepo-surface text-arepo-ink"
              : "border-arepo-accentBorder bg-arepo-accentTint text-arepo-accentActive"
          }`}
        >
          <span
            aria-hidden="true"
            className={`mt-1.5 h-2 w-2 flex-none rounded-full ${toast.tone === "ok" ? "bg-arepo-pos" : "bg-arepo-accent"}`}
          />
          <p className="min-w-0 break-words">{toast.text}</p>
          <button type="button" onClick={onClose} className="focus-ring -mr-1 flex-none rounded px-1 text-arepo-muted hover:text-arepo-ink">
            <span className="sr-only">Dismiss</span>
            <span aria-hidden="true">×</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}

function AuditList({ entries, nowMs }: { entries: AuditEntry[]; nowMs: number }) {
  if (!entries.length) return <Quiet>No admin actions yet. Everything you do here is recorded in this list.</Quiet>;
  return (
    <ol className="panel divide-y divide-arepo-border px-4 sm:px-6">
      {entries.map((e) => {
        const t = e.at ? Date.parse(e.at) : NaN;
        const age = Number.isFinite(t) ? Math.max(0, (nowMs - t) / 1000) : null;
        return (
          <li key={e.id} className="flex flex-col gap-0.5 py-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
            <p className="min-w-0 break-words text-[13.5px] text-arepo-ink2">{auditSentence(e)}</p>
            <time
              dateTime={e.at ?? undefined}
              title={e.at ?? undefined}
              className="flex-none font-tabular text-[12.5px] text-arepo-muted"
            >
              {agoLabel(age)}
            </time>
          </li>
        );
      })}
    </ol>
  );
}

function LoadingView() {
  return (
    <div className="mx-auto max-w-6xl space-y-8" aria-busy="true" aria-label="Loading members">
      <SkeletonBlock className="h-10 w-48" />
      <SkeletonBlock className="h-24 w-full" />
      <SkeletonBlock className="h-72 w-full" />
    </div>
  );
}

export function MembersAdmin() {
  const { data, loading, error, notFound, isFixture, locked, refresh, act } = useMembers();
  const auth = useAuth();
  const [revealed, setRevealed] = useState(false);
  const lockedState = locked ?? auth.locked;
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<MemberFilter>("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 30_000);
    return () => {
      clearInterval(t);
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);
  useEffect(() => setNowMs(Date.now()), [data]);

  function showToast(tone: Toast["tone"], text: string) {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ id: Date.now(), tone, text });
    toastTimer.current = setTimeout(() => setToast(null), 6000);
  }

  const users = useMemo(() => data?.users ?? [], [data]);
  const counts = useMemo(() => filterCounts(users), [users]);
  const shown = useMemo(() => filterMembers(users, query, filter), [users, query, filter]);

  if (lockedState) {
    return (
      <UnlockScreen
        keys={lockedState.keys}
        onUnlocked={() => {
          setRevealed(true);
          void auth.refresh();
          void refresh();
        }}
      />
    );
  }
  if (notFound) return <LabNotFound />;
  if (loading && !data) return <LoadingView />;
  if (!data) return <ErrorState title="Couldn't load members" message={error ?? "Something went wrong."} />;

  const verified = users.filter((u) => u.is_verified).length;

  return (
    <Revealed active={revealed}>
    <div className="mx-auto max-w-6xl space-y-14 pb-10 sm:space-y-16">
      {isFixture ? (
        <div
          role="note"
          className="z-30 rounded-control border border-arepo-warn/50 bg-[repeating-linear-gradient(135deg,#FBF3E4_0_10px,#F7EAD2_10px_20px)] px-4 py-2 text-center text-[12.5px] font-semibold uppercase tracking-wider text-arepo-warnText md:sticky md:top-[72px]"
        >
          Fixture · local development data, actions are simulated
        </div>
      ) : null}

      <header className="lab-rise space-y-6">
        <LabTabs current="members" />
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
          <div className="min-w-0">
            <p className="section-label flex items-center gap-2">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-arepo-accent" /> Private · owner only
            </p>
            <h1 className="display-hero mt-2 text-[40px] sm:text-[52px]">Members</h1>
            <p className="mt-2 max-w-reading text-[15.5px] leading-relaxed text-arepo-ink2">
              Everyone with an Arepo account. Send password resets, verify or suspend accounts, remove them, and choose
              who else can run the Lab. Passwords are never visible here.
            </p>
          </div>
          <button type="button" onClick={() => void refresh()} className="btn btn-ghost" disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        {error ? (
          <p className="rounded-control border border-arepo-warn/40 bg-arepo-warn/10 px-4 py-2 text-[13px] text-arepo-warnText" role="status">
            {error} Showing the last list received.
          </p>
        ) : null}
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:flex sm:flex-wrap sm:gap-x-10">
          {(
            [
              ["Members", users.length],
              ["Verified", verified],
              ["Admins", counts.admins],
              ["Suspended", counts.suspended],
            ] as Array<[string, number]>
          ).map(([label, v]) => (
            <div key={label}>
              <dt className="text-[12px] text-arepo-muted">{label}</dt>
              <dd className="font-display font-tabular text-[26px] font-semibold leading-tight text-arepo-ink">{fmtCount(v)}</dd>
            </div>
          ))}
        </dl>
      </header>

      <LabSection id="members" eyebrow="Accounts" title="All members" lead="Open Manage on a member to see what you can do. Every action asks you to confirm first.">
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <label className="relative min-w-0 flex-1 sm:basis-64">
              <span className="sr-only">Search members</span>
              <svg aria-hidden="true" viewBox="0 0 16 16" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-arepo-muted">
                <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name or email"
                className="w-full rounded-control border border-arepo-borderStrong bg-arepo-surface py-2 pl-9 pr-3 text-[14px] text-arepo-ink placeholder:text-arepo-muted"
              />
            </label>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter members">
              {FILTERS.map((f) => (
                <FilterChip key={f.key} active={filter === f.key} onClick={() => setFilter(f.key)} label={f.label} count={counts[f.key]} />
              ))}
            </div>
          </div>
          <p className="font-tabular text-[13px] text-arepo-muted" aria-live="polite">
            Showing {fmtCount(shown.length)} of {fmtCount(users.length)}
          </p>

          {shown.length ? (
            <div className="md:rounded-card md:border md:border-arepo-border md:bg-arepo-surface md:px-4 md:py-1">
              <div
                aria-hidden="true"
                className={`hidden border-b border-arepo-border px-2 py-2.5 text-[11.5px] font-semibold uppercase tracking-wider text-arepo-muted ${ROW_GRID}`}
              >
                <span>Member</span>
                <span>Status</span>
                <span>Saved data</span>
                <span>Joined</span>
                <span className="w-[92px]" />
              </div>
              <ul className="space-y-3 md:space-y-0" aria-label="Members">
                {shown.map((m) => (
                  <MemberRow
                    key={m.id}
                    m={m}
                    meId={data.me}
                    open={openId === m.id}
                    onToggle={() => setOpenId((cur) => (cur === m.id ? null : m.id))}
                    act={async (kind, id, confirmEmail) => {
                      const res = await act(kind, id, confirmEmail);
                      if (!res.ok) showToast("error", res.message);
                      return res;
                    }}
                    onDone={(message) => {
                      showToast("ok", isFixture ? `${message} (simulated)` : message);
                    }}
                  />
                ))}
              </ul>
            </div>
          ) : (
            <Quiet>{users.length ? "No members match this search." : "No members yet."}</Quiet>
          )}
        </div>
      </LabSection>

      <LabSection id="admin-activity" eyebrow="Audit" title="Recent admin activity" lead="The last 50 member actions taken from this page, newest first.">
        <AuditList entries={data.audit} nowMs={nowMs} />
      </LabSection>

      <ToastRegion toast={toast} onClose={() => setToast(null)} />
    </div>
    </Revealed>
  );
}
