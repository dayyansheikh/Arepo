"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SkeletonBlock } from "@/components/Skeletons";
import { ErrorState } from "@/components/ErrorState";
import { RecoveryCodes } from "@/components/security/RecoveryCodes";
import { Revealed, UnlockScreen } from "@/components/security/UnlockScreen";
import { useAuth } from "@/lib/auth-context";
import {
  KEY_METHODS,
  METHOD_LABELS,
  forgetDevice,
  getStepUpStatus,
  keyKindLabel,
  listDevices,
  listKeys,
  lockNow,
  regenerateRecoveryCodes,
  registerKey,
  rememberMethod,
  rememberedMethod,
  removeKey,
  renameDevice,
  renameKey,
  trustThisDevice,
  unlockWithKey,
  untrustDevice,
  type Device,
  type KeyMethod,
  type Outcome,
  type SecurityKey,
  type StepUpStatus,
} from "@/lib/webauthn";
import { LabTabs } from "./LabTabs";
import { LabNotFound, LabSection, Pill, Quiet } from "./primitives";

const SIGNIN = "/signin?next=/lab/security";
const ADD_HELP: Record<KeyMethod, { name: string; help: string }> = {
  device: { name: "MacBook Touch ID", help: "Touch ID or Face ID on the device you're using now." },
  phone: { name: "iPhone", help: "Scan the QR code with your phone's camera. Bluetooth on." },
  security_key: { name: "YubiKey", help: "Plug in or tap the key, then touch it when it blinks." },
};

type View =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; message: string }
  | { kind: "locked"; keys: number }
  | { kind: "ready"; status: StepUpStatus; keys: SecurityKey[]; devices: Device[] };

function day(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "–" : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

/** Runs `fn`; if the server wants a fresh key tap first (e.g. on a trusted device), asks for one
 * with the remembered method and tries once more. */
async function withFreshUnlock<T>(fn: () => Promise<Outcome<T>>): Promise<Outcome<T>> {
  const first = await fn();
  if (first.ok || first.code !== "hardware_key_required") return first;
  const unlocked = await unlockWithKey(rememberedMethod() ?? "any");
  if (!unlocked.ok) return unlocked;
  return fn();
}

function DeviceRow({
  d,
  hours,
  onUntrust,
  onRename,
  onForget,
}: {
  d: Device;
  hours: number;
  onUntrust: () => Promise<boolean>;
  onRename: (name: string) => Promise<boolean>;
  onForget: () => Promise<boolean>;
}) {
  const [mode, setMode] = useState<"view" | "rename" | "forget">("view");
  const [name, setName] = useState(d.nickname);
  const [busy, setBusy] = useState(false);
  const act = async (fn: () => Promise<boolean>) => {
    setBusy(true);
    await fn();
    setBusy(false);
  };

  return (
    <li className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between" data-testid="device-row">
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
              <span className="sr-only">Device name</span>
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
            <button type="button" className="btn btn-ghost" onClick={() => { setName(d.nickname); setMode("view"); }}>
              Cancel
            </button>
          </form>
        ) : (
          <>
            <p className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-arepo-ink">
              <span className="truncate">{d.nickname}</span>
              {d.current ? <Pill tone="neutral">This device</Pill> : null}
              {d.trusted ? <Pill tone="pos">No key until {day(d.trusted_until)}</Pill> : <Pill tone="muted">Key every {hours} h</Pill>}
            </p>
            <p className="mt-0.5 text-[12.5px] text-arepo-muted">
              First seen {when(d.first_seen_at)} · last seen {when(d.last_seen_at)}
            </p>
          </>
        )}
      </div>
      {mode === "view" ? (
        <div className="flex flex-none flex-wrap gap-2">
          {d.trusted ? (
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void act(onUntrust)}>
              Ask for my key again
            </button>
          ) : null}
          <button type="button" className="btn btn-ghost" onClick={() => setMode("rename")}>
            Rename
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setMode("forget")}>
            Forget
          </button>
        </div>
      ) : null}
      {mode === "forget" ? (
        <div className="flex flex-none flex-wrap items-center gap-2" role="group" aria-label={`Forget ${d.nickname}`}>
          <span className="text-[13px] text-arepo-ink2">Forget this device?</span>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              if (!(await onForget())) setMode("view");
              setBusy(false);
            }}
          >
            Forget
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setMode("view")}>
            Keep
          </button>
        </div>
      ) : null}
    </li>
  );
}

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
  const [adding, setAdding] = useState<KeyMethod | null>(null);
  const [trusting, setTrusting] = useState(false);
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
    const unlocked = st.data.unlocked ?? st.data.step_up.active;
    if (st.data.required && !unlocked) return setView({ kind: "locked", keys: st.data.keys });
    const [ks, ds] = await Promise.all([listKeys(), listDevices()]);
    if (!ks.ok) {
      if (ks.code === "hardware_key_required") return setView({ kind: "locked", keys: st.data.keys });
      if (ks.status === 401) return router.replace(SIGNIN);
      return setView({ kind: "error", message: ks.message });
    }
    setView({ kind: "ready", status: st.data, keys: ks.data.keys, devices: ds.ok ? ds.data.devices : [] });
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

  const { status, keys, devices } = view;
  const canRemoveLast = status.enforcement === "off";
  const current = devices.find((d) => d.current) ?? status.device ?? null;
  const trustDays = status.trusted_device_days ?? 30;

  async function add(method: KeyMethod) {
    setAdding(method);
    setNote(null);
    const res = await withFreshUnlock(() => registerKey(nickname.trim() || ADD_HELP[method].name, method));
    setAdding(null);
    if (!res.ok) {
      if (res.code === "hardware_key_required") return setView({ kind: "locked", keys: keys.length });
      return setNote({ tone: "error", text: res.message });
    }
    setNickname("");
    rememberMethod(method);
    setNote({ tone: "ok", text: `Added “${res.data.key.nickname}”.` });
    if (res.data.recovery_codes?.length) {
      setCodes(res.data.recovery_codes);
      void auth.refresh();
      return;
    }
    void load();
  }

  async function trustHere() {
    setNote(null);
    const res = await trustThisDevice(rememberedMethod() ?? "any");
    if (!res.ok) {
      setNote({ tone: "error", text: res.message });
      return false;
    }
    setNote({
      tone: "ok",
      text: `This device won't ask for your key until ${day(res.data.device.trusted_until)}. You can turn this off any time.`,
    });
    void load();
    return true;
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
  const thisBrowser = current?.trusted
    ? `Trusted until ${day(current.trusted_until)}`
    : expires
      ? `Unlocked until ${expires}`
      : "Not unlocked";

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
            {status.step_up.active || current?.trusted ? (
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
              <dd className="mt-1.5 text-[14px] text-arepo-ink2">{thisBrowser}</dd>
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
                  onRemove={() => outcome(withFreshUnlock(() => removeKey(k.id)), `Removed “${k.nickname}”.`)}
                />
              ))}
            </ul>
          ) : (
            <Quiet>No keys yet. Add your first one below; from then on every signed-in page needs it.</Quiet>
          )}
        </LabSection>

        <LabSection
          id="devices"
          eyebrow="Your devices"
          title="Devices"
          lead={`Each browser you unlock from. Normally it asks for your key every ${status.stepup_hours} hours; on a device you trust it won't ask for ${trustDays} days.`}
        >
          {keys.length && current && !current.trusted && trustDays > 0 ? (
            <div className="panel mb-4 flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5" data-testid="this-device">
              <div className="min-w-0">
                <p className="text-[15px] font-semibold text-arepo-ink">Don&apos;t ask for my key on {current.nickname}</p>
                <p className="mt-0.5 text-[13px] text-arepo-ink2">
                  One key tap to confirm. Lasts {trustDays} days, and you can turn it off any time.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary flex-none"
                disabled={trusting}
                onClick={async () => {
                  setTrusting(true);
                  await trustHere();
                  setTrusting(false);
                }}
              >
                {trusting ? "Tap your key…" : "Trust this device"}
              </button>
            </div>
          ) : null}
          {devices.length ? (
            <ul className="panel divide-y divide-arepo-border px-4 sm:px-6" aria-label="Devices">
              {devices.map((d) => (
                <DeviceRow
                  key={d.id}
                  d={d}
                  hours={status.stepup_hours}
                  onUntrust={() => outcome(untrustDevice(d.id), `“${d.nickname}” will ask for your key again.`)}
                  onRename={(name) => outcome(renameDevice(d.id, name), "Renamed.")}
                  onForget={() => outcome(forgetDevice(d.id), `Forgot “${d.nickname}”.`)}
                />
              ))}
            </ul>
          ) : (
            <Quiet>No devices yet. This browser appears here after your first unlock.</Quiet>
          )}
        </LabSection>

        <LabSection
          id="add-key"
          eyebrow="Add a key"
          title={keys.length ? "Add another key" : "Add your first key"}
          lead="A backup key (say your iPhone as well as Touch ID) means losing one device never locks you out."
        >
          <div className="panel space-y-4 p-5 sm:p-6">
            <label className="block">
              <span className="text-[13px] font-medium text-arepo-ink">Name (optional)</span>
              <input
                value={nickname}
                maxLength={60}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="e.g. MacBook Touch ID"
                className="mt-1 block w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-2 text-[14px] text-arepo-ink placeholder:text-arepo-muted sm:max-w-sm"
              />
            </label>
            <div className="grid gap-3 sm:grid-cols-3" role="group" aria-label="Add a key with">
              {KEY_METHODS.map((m) => (
                <div key={m}>
                  <button
                    type="button"
                    className="btn btn-secondary w-full justify-center"
                    disabled={adding !== null}
                    onClick={() => void add(m)}
                    data-method={m}
                  >
                    {adding === m ? "Waiting for your key…" : METHOD_LABELS[m].add}
                  </button>
                  <p className="mt-1.5 text-[12.5px] leading-relaxed text-arepo-muted">{ADD_HELP[m].help}</p>
                </div>
              ))}
            </div>
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
                      const res = await withFreshUnlock(() => regenerateRecoveryCodes());
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
