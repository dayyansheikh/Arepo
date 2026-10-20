"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SkeletonBlock } from "@/components/Skeletons";
import { ErrorState } from "@/components/ErrorState";
import { RecoveryCodes } from "@/components/security/RecoveryCodes";
import { Revealed, UnlockScreen } from "@/components/security/UnlockScreen";
import { useAuth } from "@/lib/auth-context";
import {
  getStepUpStatus,
  keyKindLabel,
  listKeys,
  lockNow,
  regenerateRecoveryCodes,
  registerKey,
  removeKey,
  renameKey,
  type SecurityKey,
  type StepUpStatus,
} from "@/lib/webauthn";
import { LabTabs } from "./LabTabs";
import { LabNotFound, LabSection, Pill, Quiet } from "./primitives";

const SIGNIN = "/signin?next=/lab/security";
const SUGGESTED = ["MacBook Touch ID", "iPhone", "YubiKey"];

const OPTIONS: Array<{ title: string; body: string }> = [
  {
    title: "This Mac (Touch ID)",
    body: "When the browser asks, choose this Mac or iCloud Keychain and touch the fingerprint sensor.",
  },
  {
    title: "iPhone",
    body: "Choose “iPhone, iPad or Android device” and scan the QR code with the iPhone camera, or open this page on the iPhone itself and use Face ID.",
  },
  {
    title: "USB security key (YubiKey)",
    body: "Choose “Security key”, plug the key in and touch its gold contact when it blinks.",
  },
];

type View =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; message: string }
  | { kind: "locked"; keys: number }
  | { kind: "ready"; status: StepUpStatus; keys: SecurityKey[] };

function when(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "–"
    : d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function KeyRow({
  k,
  onRename,
  onRemove,
  canRemove,
}: {
  k: SecurityKey;
  onRename: (name: string) => Promise<boolean>;
  onRemove: () => Promise<boolean>;
  canRemove: boolean;
}) {
  const [mode, setMode] = useState<"view" | "rename" | "remove">("view");
  const [name, setName] = useState(k.nickname);
  const [busy, setBusy] = useState(false);

  return (
    <li className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        {mode === "rename" ? (
          <form
            className="flex flex-wrap gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              if (await onRename(name)) setMode("view");
              setBusy(false);
            }}
          >
            <label className="min-w-0 flex-1">
              <span className="sr-only">Key name</span>
              <input
                value={name}
                maxLength={60}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-1.5 text-[14px] text-arepo-ink"
              />
            </label>
            <button type="submit" className="btn btn-secondary" disabled={busy || !name.trim()}>
              Save
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => { setName(k.nickname); setMode("view"); }}>
              Cancel
            </button>
          </form>
        ) : (
          <>
            <p className="truncate text-[15px] font-semibold text-arepo-ink">{k.nickname}</p>
            <p className="mt-0.5 text-[12.5px] text-arepo-muted">
              {keyKindLabel(k)} · added {when(k.created_at)} · last used {when(k.last_used_at)}
            </p>
          </>
        )}
      </div>
      {mode === "view" ? (
        <div className="flex flex-none gap-2">
          <button type="button" className="btn btn-ghost" onClick={() => setMode("rename")}>
            Rename
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setMode("remove")}
            disabled={!canRemove}
            title={canRemove ? undefined : "Add another key before removing your last one."}
          >
            Remove
          </button>
        </div>
      ) : null}
      {mode === "remove" ? (
        <div className="flex flex-none flex-wrap items-center gap-2" role="group" aria-label={`Remove ${k.nickname}`}>
          <span className="text-[13px] text-arepo-ink2">Remove this key?</span>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              if (!(await onRemove())) setMode("view");
              setBusy(false);
            }}
          >
            Remove
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setMode("view")}>
            Keep
          </button>
        </div>
      ) : null}
    </li>
  );
}

export function SecurityKeys() {
  const router = useRouter();
  const auth = useAuth();
  const [view, setView] = useState<View>({ kind: "loading" });
  const [revealed, setRevealed] = useState(false);
  const [nickname, setNickname] = useState("");
  const [adding, setAdding] = useState(false);
  const [note, setNote] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [confirmCodes, setConfirmCodes] = useState(false);

  const load = useCallback(async () => {
    const st = await getStepUpStatus();
    if (!st.ok) {
      if (st.status === 401) return router.replace(SIGNIN);
      if (st.status === 404) return setView({ kind: "not_found" });
      return setView({ kind: "error", message: st.message });
    }
    if (st.data.required && !st.data.step_up.active) return setView({ kind: "locked", keys: st.data.keys });
    const ks = await listKeys();
    if (!ks.ok) {
      if (ks.code === "hardware_key_required") return setView({ kind: "locked", keys: st.data.keys });
      if (ks.status === 401) return router.replace(SIGNIN);
      return setView({ kind: "error", message: ks.message });
    }
    setView({ kind: "ready", status: st.data, keys: ks.data.keys });
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (view.kind === "loading") {
    return (
      <div className="mx-auto max-w-4xl space-y-8" aria-busy="true" aria-label="Loading security">
        <SkeletonBlock className="h-10 w-48" />
        <SkeletonBlock className="h-40 w-full" />
      </div>
    );
  }
  if (view.kind === "not_found") return <LabNotFound />;
  if (view.kind === "error") return <ErrorState title="Couldn't load security keys" message={view.message} />;
  if (view.kind === "locked") {
    return (
      <UnlockScreen
        keys={view.keys}
        onUnlocked={() => {
          setRevealed(true);
          void auth.refresh();
          void load();
        }}
      />
    );
  }
  if (codes) {
    return (
      <div className="mx-auto max-w-md py-6">
        <RecoveryCodes
          codes={codes}
          onDone={() => {
            setCodes(null);
            void load();
          }}
        />
      </div>
    );
  }

  const { status, keys } = view;
  const canRemoveLast = status.enforcement === "off";

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    setNote(null);
    const res = await registerKey(nickname.trim() || "Security key");
    setAdding(false);
    if (!res.ok) {
      if (res.code === "hardware_key_required") return setView({ kind: "locked", keys: keys.length });
      return setNote({ tone: "error", text: res.message });
    }
    setNickname("");
    setNote({ tone: "ok", text: `Added “${res.data.key.nickname}”.` });
    if (res.data.recovery_codes?.length) {
      setCodes(res.data.recovery_codes);
      void auth.refresh();
      return;
    }
    void load();
  }

  async function outcome(p: Promise<{ ok: boolean; message?: string; code?: string }>, okText: string) {
    const res = await p;
    if (!res.ok) {
      if (res.code === "hardware_key_required") {
        setView({ kind: "locked", keys: keys.length });
      } else {
        setNote({ tone: "error", text: res.message ?? "Something went wrong." });
      }
      return false;
    }
    setNote({ tone: "ok", text: okText });
    void load();
    return true;
  }

  const expires = status.step_up.expires_at ? when(status.step_up.expires_at) : null;

  return (
    <Revealed active={revealed}>
      <div className="mx-auto max-w-4xl space-y-14 pb-10 sm:space-y-16">
        <header className="lab-rise space-y-6">
          <LabTabs current="security" />
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
            <div className="min-w-0">
              <p className="section-label flex items-center gap-2">
                <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-arepo-accent" /> Private · owner only
              </p>
              <h1 className="display-hero mt-2 text-[40px] sm:text-[52px]">Security</h1>
              <p className="mt-2 max-w-reading text-[15.5px] leading-relaxed text-arepo-ink2">
                Once you add a security key or passkey, every signed-in page of your account (the Lab, Members, your
                account and alerts) needs it as well as your password. One unlock lasts{" "}
                {status.stepup_hours} hours on this browser.
              </p>
            </div>
            {status.step_up.active ? (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={async () => {
                  await lockNow();
                  setView({ kind: "locked", keys: keys.length });
                }}
              >
                Lock now
              </button>
            ) : null}
          </div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:flex sm:flex-wrap sm:gap-x-10">
            <div>
              <dt className="text-[12px] text-arepo-muted">Keys</dt>
              <dd className="font-display font-tabular text-[26px] font-semibold leading-tight text-arepo-ink">{keys.length}</dd>
            </div>
            <div>
              <dt className="text-[12px] text-arepo-muted">Protection</dt>
              <dd className="mt-1.5">
                {status.required ? <Pill tone="pos">On</Pill> : status.enforcement === "off" ? <Pill tone="warn">Switched off</Pill> : <Pill tone="muted">Not set up</Pill>}
              </dd>
            </div>
            <div>
              <dt className="text-[12px] text-arepo-muted">This browser</dt>
              <dd className="mt-1.5 text-[14px] text-arepo-ink2">{expires ? `Unlocked until ${expires}` : "Not unlocked"}</dd>
            </div>
            <div>
              <dt className="text-[12px] text-arepo-muted">Recovery codes left</dt>
              <dd className="font-display font-tabular text-[26px] font-semibold leading-tight text-arepo-ink">
                {status.recovery_codes_remaining}
              </dd>
            </div>
          </dl>
          {status.enforcement === "off" ? (
            <p className="rounded-control border border-arepo-warn/40 bg-arepo-warn/10 px-4 py-2 text-[13px] text-arepo-warnText" role="status">
              Keys are switched off on the server (LAB_REQUIRE_HARDWARE_KEY=off), so your password alone opens everything.
            </p>
          ) : null}
          {note ? (
            <p
              role="status"
              aria-live="polite"
              className={`rounded-control border px-4 py-2 text-[13px] ${
                note.tone === "ok"
                  ? "border-arepo-border bg-arepo-surface text-arepo-ink2"
                  : "border-arepo-accentBorder bg-arepo-accentTint text-arepo-accentActive"
              }`}
            >
              {note.text}
            </p>
          ) : null}
        </header>

        <LabSection id="keys" eyebrow="Your keys" title="Registered keys" lead="Any one of these unlocks your account.">
          {keys.length ? (
            <ul className="panel divide-y divide-arepo-border px-4 sm:px-6">
              {keys.map((k) => (
                <KeyRow
                  key={k.id}
                  k={k}
                  canRemove={keys.length > 1 || canRemoveLast}
                  onRename={(name) => outcome(renameKey(k.id, name), "Renamed.")}
                  onRemove={() => outcome(removeKey(k.id), `Removed “${k.nickname}”.`)}
                />
              ))}
            </ul>
          ) : (
            <Quiet>No keys yet. Add your first one below; from then on every signed-in page needs it.</Quiet>
          )}
        </LabSection>

        <LabSection
          id="add-key"
          eyebrow="Add a key"
          title={keys.length ? "Add another key" : "Add your first key"}
          lead="Name it so you can tell them apart, then follow your browser's prompt. Adding a backup key (for example your iPhone as well as Touch ID) means losing one device never locks you out."
        >
          <div className="panel space-y-5 p-5 sm:p-6">
            <ul className="grid gap-4 sm:grid-cols-3">
              {OPTIONS.map((o) => (
                <li key={o.title} className="rounded-control border border-arepo-border bg-arepo-surface2/60 p-4">
                  <p className="text-[14px] font-semibold text-arepo-ink">{o.title}</p>
                  <p className="mt-1 text-[13px] leading-relaxed text-arepo-ink2">{o.body}</p>
                </li>
              ))}
            </ul>
            <form onSubmit={(e) => void add(e)} className="space-y-3">
              <label className="block">
                <span className="text-[13px] font-medium text-arepo-ink">Name</span>
                <input
                  value={nickname}
                  maxLength={60}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="e.g. MacBook Touch ID"
                  className="mt-1 w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-2 text-[14px] text-arepo-ink placeholder:text-arepo-muted sm:max-w-sm"
                />
              </label>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Name suggestions">
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setNickname(s)}
                    className="focus-ring rounded-full border border-arepo-border bg-arepo-surface px-3 py-1 text-[12.5px] text-arepo-ink2 hover:border-arepo-borderStrong hover:bg-arepo-surface2"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <button type="submit" className="btn btn-primary" disabled={adding}>
                {adding ? "Waiting for your key…" : "Add key"}
              </button>
            </form>
          </div>
        </LabSection>

        <LabSection
          id="recovery"
          eyebrow="If you lose every key"
          title="Recovery codes"
          lead="Each code unlocks your account once. Making new codes cancels the old ones."
        >
          {keys.length ? (
            <div className="panel flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6">
              <p className="text-[14px] text-arepo-ink2">
                {status.recovery_codes_remaining} of 10 codes left.
              </p>
              {confirmCodes ? (
                <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Make new recovery codes">
                  <span className="text-[13px] text-arepo-ink2">Replace your current codes?</span>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={async () => {
                      setConfirmCodes(false);
                      const res = await regenerateRecoveryCodes();
                      if (res.ok) setCodes(res.data.recovery_codes);
                      else if (res.code === "hardware_key_required") setView({ kind: "locked", keys: keys.length });
                      else setNote({ tone: "error", text: res.message });
                    }}
                  >
                    Make new codes
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => setConfirmCodes(false)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <button type="button" className="btn btn-secondary" onClick={() => setConfirmCodes(true)}>
                  Make new codes
                </button>
              )}
            </div>
          ) : (
            <Quiet>Your recovery codes are created with your first key.</Quiet>
          )}
        </LabSection>
      </div>
    </Revealed>
  );
}
