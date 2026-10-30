"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  KEY_METHODS,
  METHOD_LABELS,
  browserFamily,
  methodTip,
  primaryMethod,
  redeemRecoveryCode,
  registerKey,
  rememberMethod,
  rememberedMethod,
  unlockWithKey,
  webauthnSupported,
  type BrowserFamily,
  type KeyMethod,
} from "@/lib/webauthn";
import { Padlock } from "./Padlock";
import { RecoveryCodes } from "./RecoveryCodes";
import styles from "./unlock.module.css";

const OPEN_MS = 650; // shackle animation (~600 ms) before the page fades in
const LEAVE_MS = 220;

const SETUP_BUTTONS: Record<KeyMethod, string> = {
  device: "Set up Touch ID / Face ID",
  phone: "Set up my phone",
  security_key: "Set up a security key",
};

const SETUP_NAMES: Record<KeyMethod, string> = {
  device: "This device",
  phone: "Phone",
  security_key: "Security key",
};

const LINK_LABELS: Record<KeyMethod, string> = {
  device: "Touch ID / Face ID",
  phone: "Phone (QR code)",
  security_key: "Security key",
};

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

async function platformAuthenticator(): Promise<boolean> {
  try {
    const pkc = typeof window !== "undefined" ? window.PublicKeyCredential : undefined;
    return !!pkc && typeof pkc.isUserVerifyingPlatformAuthenticatorAvailable === "function"
      ? await pkc.isUserVerifyingPlatformAuthenticatorAvailable()
      : false;
  } catch {
    return false;
  }
}

/**
 * Calm, minimal prompt shown whenever the API answers 403 hardware_key_required: a small padlock,
 * one line, one primary button for the most likely method (the one that last worked on this
 * browser, else this device's Touch ID / Face ID, else the phone), and the other methods as small
 * links underneath. A tip on getting the browser to show the right prompt appears only after a
 * failed or cancelled attempt (or on hover). `keys === 0` only happens under
 * LAB_REQUIRE_HARDWARE_KEY=always before the first key exists, so the screen offers set-up instead.
 */
export function UnlockScreen({ keys = 1, onUnlocked }: { keys?: number; onUnlocked: () => void }) {
  const router = useRouter();
  const { signOut } = useAuth();
  const [phase, setPhase] = useState<"idle" | "waiting" | "open" | "leaving">("idle");
  const [message, setMessage] = useState<string>("");
  const [tip, setTip] = useState<string>("");
  const [shake, setShake] = useState(0);
  const [showRecovery, setShowRecovery] = useState(false);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [supported, setSupported] = useState(true);
  const [primary, setPrimary] = useState<KeyMethod>("device");
  const [family, setFamily] = useState<BrowserFamily>("other");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const setup = keys === 0;

  useEffect(() => {
    setSupported(webauthnSupported());
    setFamily(browserFamily(typeof navigator !== "undefined" ? navigator.userAgent : ""));
    const remembered = rememberedMethod();
    if (remembered) setPrimary(remembered);
    else void platformAuthenticator().then((has) => setPrimary(primaryMethod(null, has)));
    const t = timers.current;
    return () => t.forEach(clearTimeout);
  }, []);

  function finish() {
    setPhase("open");
    setMessage("Unlocked.");
    setTip("");
    const reduce = prefersReducedMotion();
    timers.current.push(
      setTimeout(() => setPhase("leaving"), reduce ? 0 : OPEN_MS),
      setTimeout(onUnlocked, reduce ? 0 : OPEN_MS + LEAVE_MS),
    );
  }

  function fail(text: string, method?: KeyMethod) {
    setPhase("idle");
    setMessage(text);
    setTip(method ? methodTip(method, family) : "");
    setShake((n) => n + 1);
  }

  async function run(method: KeyMethod) {
    setPrimary(method);
    setShowRecovery(false);
    setPhase("waiting");
    setMessage("");
    setTip("");
    if (setup) {
      const res = await registerKey(SETUP_NAMES[method], method);
      if (!res.ok) return fail(res.message, method);
      rememberMethod(method);
      if (res.data.recovery_codes?.length) {
        setPhase("idle");
        setCodes(res.data.recovery_codes);
        return;
      }
      return finish();
    }
    const res = await unlockWithKey(method);
    if (!res.ok) return fail(res.message, method);
    rememberMethod(method);
    finish();
  }

  async function submitCode(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setPhase("waiting");
    setMessage("");
    setTip("");
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

  const busy = phase === "waiting" || phase === "open" || phase === "leaving";
  const others = KEY_METHODS.filter((m) => m !== primary);
  const linkClass =
    "focus-ring rounded px-1 py-0.5 text-[13px] text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline disabled:opacity-50";

  return (
    <div
      className={`mx-auto flex min-h-[55vh] max-w-sm flex-col items-center justify-center px-4 py-10 text-center ${styles.rise} ${
        phase === "leaving" ? styles.leaving : ""
      }`}
      data-testid="unlock-screen"
    >
      <Padlock size={40} state={phase === "open" || phase === "leaving" ? "open" : "locked"} shakeKey={shake} />
      <h1 className="mt-5 font-display text-[22px] font-semibold tracking-tight text-arepo-ink">
        {setup ? "Add a security key" : "Unlock your account"}
      </h1>

      <button
        type="button"
        className="btn btn-primary mt-6 w-full max-w-[17rem] justify-center"
        onClick={() => void run(primary)}
        disabled={busy || !supported}
        data-method={primary}
        title={methodTip(primary, family)}
      >
        {phase === "waiting"
          ? "Waiting…"
          : phase === "open" || phase === "leaving"
            ? "Unlocked"
            : setup
              ? SETUP_BUTTONS[primary]
              : METHOD_LABELS[primary].button}
      </button>

      <p
        role="status"
        aria-live="polite"
        className={`mt-3 min-h-[1.25em] text-[13px] ${phase === "open" ? "text-arepo-pos" : "text-arepo-accentActive"}`}
      >
        {!supported ? "This browser can't use passkeys or security keys." : message}
      </p>
      {tip ? (
        <p className="-mt-1 max-w-xs text-[12.5px] leading-relaxed text-arepo-muted" data-testid="unlock-tip">
          {tip}
        </p>
      ) : null}

      <nav
        aria-label={setup ? "Other ways to set up" : "Other ways to unlock"}
        className="mt-5 flex flex-wrap items-center justify-center gap-x-1 gap-y-1"
      >
        <span className="px-1 text-[13px] text-arepo-muted">Or use</span>
        {others.map((m, i) => (
          <span key={m} className="inline-flex items-center">
            <button
              type="button"
              className={linkClass}
              onClick={() => void run(m)}
              disabled={busy || !supported}
              data-method={m}
              title={methodTip(m, family)}
            >
              {LINK_LABELS[m]}
            </button>
            {i < others.length - 1 || !setup ? (
              <span aria-hidden="true" className="mx-0.5 text-arepo-muted">
                ·
              </span>
            ) : null}
          </span>
        ))}
        {!setup ? (
          <button
            type="button"
            className={linkClass}
            onClick={() => setShowRecovery((v) => !v)}
            aria-expanded={showRecovery}
            disabled={phase === "open" || phase === "leaving"}
          >
            Recovery code
          </button>
        ) : null}
      </nav>

      {!setup && showRecovery ? (
        <form
          onSubmit={(e) => void submitCode(e)}
          className="mt-4 flex w-full max-w-[17rem] gap-2"
          aria-label="Use a recovery code"
        >
          <label className="min-w-0 flex-1">
            <span className="sr-only">Recovery code</span>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="xxxxx-xxxxx"
              autoComplete="one-time-code"
              spellCheck={false}
              autoFocus
              className="w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-1.5 text-center font-mono text-[13.5px] tracking-wider text-arepo-ink placeholder:text-arepo-muted"
            />
          </label>
          <button type="submit" className="btn btn-secondary justify-center" disabled={busy || !code.trim()}>
            Use
          </button>
        </form>
      ) : null}

      <button type="button" onClick={() => void leave()} className={`${linkClass} mt-6`}>
        Sign out
      </button>
    </div>
  );
}

/** Wraps page content that has just been unlocked so it fades in instead of popping. */
export function Revealed({ active, children }: { active: boolean; children: React.ReactNode }) {
  return <div className={active ? styles.reveal : undefined}>{children}</div>;
}
