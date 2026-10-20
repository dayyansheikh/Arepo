"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { redeemRecoveryCode, registerKey, unlockWithKey, webauthnSupported } from "@/lib/webauthn";
import { Padlock } from "./Padlock";
import { RecoveryCodes } from "./RecoveryCodes";
import styles from "./unlock.module.css";

const OPEN_MS = 650; // shackle animation (~600 ms) before the page fades in
const LEAVE_MS = 220;

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Calm full-page prompt shown whenever the API answers 403 hardware_key_required: the session is
 * valid but this account is protected by a security key / passkey and this browser has not been
 * unlocked (or the unlock expired). `keys === 0` only happens under LAB_REQUIRE_HARDWARE_KEY=always
 * before the first key exists, so the screen offers to set one up instead.
 */
export function UnlockScreen({ keys = 1, onUnlocked }: { keys?: number; onUnlocked: () => void }) {
  const router = useRouter();
  const { signOut } = useAuth();
  const [phase, setPhase] = useState<"idle" | "waiting" | "open" | "leaving">("idle");
  const [message, setMessage] = useState<string>("");
  const [shake, setShake] = useState(0);
  const [showRecovery, setShowRecovery] = useState(false);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [supported, setSupported] = useState(true);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    setSupported(webauthnSupported());
    const t = timers.current;
    return () => t.forEach(clearTimeout);
  }, []);

  function finish() {
    setPhase("open");
    setMessage("Unlocked.");
    const reduce = prefersReducedMotion();
    timers.current.push(
      setTimeout(() => setPhase("leaving"), reduce ? 0 : OPEN_MS),
      setTimeout(onUnlocked, reduce ? 0 : OPEN_MS + LEAVE_MS),
    );
  }

  function fail(text: string) {
    setPhase("idle");
    setMessage(text);
    setShake((n) => n + 1);
  }

  async function unlock() {
    setPhase("waiting");
    setMessage("");
    const res = await unlockWithKey();
    if (res.ok) finish();
    else fail(res.message);
  }

  async function setUp() {
    setPhase("waiting");
    setMessage("");
    const res = await registerKey("Security key");
    if (!res.ok) return fail(res.message);
    if (res.data.recovery_codes?.length) {
      setPhase("idle");
      setCodes(res.data.recovery_codes);
      return;
    }
    finish();
  }

  async function submitCode(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setPhase("waiting");
    setMessage("");
    const res = await redeemRecoveryCode(code);
    if (!res.ok) return fail(res.message);
    setCode("");
    finish();
  }

  async function leave() {
    await signOut();
    router.push("/");
  }

  if (codes) {
    return (
      <div className={`mx-auto max-w-md py-6 ${styles.rise}`}>
        <RecoveryCodes codes={codes} doneLabel="Continue" onDone={() => { setCodes(null); finish(); }} />
      </div>
    );
  }

  const setup = keys === 0;
  const busy = phase === "waiting" || phase === "open" || phase === "leaving";

  return (
    <div
      className={`mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center py-10 text-center ${styles.rise} ${
        phase === "leaving" ? styles.leaving : ""
      }`}
      data-testid="unlock-screen"
    >
      <Padlock state={phase === "open" || phase === "leaving" ? "open" : "locked"} shakeKey={shake} />
      <p className="section-label mt-7 flex items-center gap-2">
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-arepo-accent" /> Protected account
      </p>
      <h1 className="display-title mt-2 text-[30px] sm:text-[34px]">{setup ? "Add a security key" : "Unlock with your key"}</h1>
      <p className="mt-2 max-w-sm text-[15px] leading-relaxed text-arepo-ink2">
        {setup
          ? "This account needs a security key or passkey before it can be used. Touch ID, an iPhone or a YubiKey all work."
          : "This account is protected by a security key. Use Touch ID, your iPhone or your YubiKey to continue."}
      </p>

      <button
        type="button"
        className="btn btn-primary mt-7 min-w-[16rem] justify-center"
        onClick={() => void (setup ? setUp() : unlock())}
        disabled={busy || !supported}
      >
        {phase === "waiting"
          ? "Waiting for your key…"
          : phase === "open" || phase === "leaving"
            ? "Unlocked"
            : setup
              ? "Set up a key"
              : "Unlock with Touch ID / passkey / key"}
      </button>

      <p role="status" aria-live="polite" className={`mt-3 min-h-[1.5em] text-[13.5px] ${phase === "open" ? "text-arepo-pos" : "text-arepo-accentActive"}`}>
        {!supported ? "This browser can't use security keys or passkeys. Try Safari, Chrome, Edge or Firefox." : message}
      </p>

      {!setup ? (
        <div className="mt-6 w-full">
          {showRecovery ? (
            <form onSubmit={(e) => void submitCode(e)} className="flex flex-col gap-2 sm:flex-row" aria-label="Use a recovery code">
              <label className="min-w-0 flex-1">
                <span className="sr-only">Recovery code</span>
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="xxxxx-xxxxx"
                  autoComplete="one-time-code"
                  spellCheck={false}
                  className="w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-2 text-center font-mono text-[14px] tracking-wider text-arepo-ink placeholder:text-arepo-muted"
                />
              </label>
              <button type="submit" className="btn btn-secondary justify-center" disabled={busy || !code.trim()}>
                Use code
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setShowRecovery(true)}
              className="focus-ring rounded px-1 text-[13px] text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline"
            >
              Lost your key? Use a recovery code
            </button>
          )}
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => void leave()}
        className="focus-ring mt-4 rounded px-1 text-[13px] text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline"
      >
        Sign out
      </button>
    </div>
  );
}

/** Wraps page content that has just been unlocked so it fades in instead of popping. */
export function Revealed({ active, children }: { active: boolean; children: React.ReactNode }) {
  return <div className={active ? styles.reveal : undefined}>{children}</div>;
}
