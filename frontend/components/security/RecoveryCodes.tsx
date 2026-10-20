"use client";

import { useState } from "react";
import { recoveryCodesText } from "@/lib/webauthn";

/**
 * Shown exactly once after the codes are created: a calm "save these now" step with a copy
 * button. `onDone` is only enabled after the owner confirms they saved them.
 */
export function RecoveryCodes({ codes, onDone, doneLabel = "Done" }: { codes: string[]; onDone: () => void; doneLabel?: string }) {
  const [copied, setCopied] = useState<"idle" | "ok" | "failed">("idle");
  const [saved, setSaved] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(recoveryCodesText(codes));
      setCopied("ok");
    } catch {
      setCopied("failed");
    }
  }

  return (
    <section aria-labelledby="recovery-title" className="panel space-y-4 p-5 text-left sm:p-6">
      <div>
        <p className="section-label">Save these now</p>
        <h2 id="recovery-title" className="display-title mt-1 text-[22px]">
          Your recovery codes
        </h2>
        <p className="mt-1.5 text-[14px] leading-relaxed text-arepo-ink2">
          If you ever lose every key, one of these unlocks your account once. They are shown only this time. Keep them
          somewhere safe and offline, such as a password manager or a printed sheet.
        </p>
      </div>
      <ol className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-control border border-arepo-border bg-arepo-surface2 px-4 py-3 font-mono text-[14px] tracking-wide text-arepo-ink">
        {codes.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn btn-secondary" onClick={() => void copy()}>
          {copied === "ok" ? "Copied" : "Copy all"}
        </button>
        <span role="status" aria-live="polite" className="text-[13px] text-arepo-muted">
          {copied === "ok" ? "Copied to the clipboard." : copied === "failed" ? "Couldn't copy. Select the codes and copy them by hand." : ""}
        </span>
      </div>
      <label className="flex items-start gap-2.5 text-[14px] text-arepo-ink2">
        <input
          type="checkbox"
          checked={saved}
          onChange={(e) => setSaved(e.target.checked)}
          className="mt-0.5 h-4 w-4 accent-[#E50C0E]"
        />
        I have saved these codes somewhere safe.
      </label>
      <button type="button" className="btn btn-primary" disabled={!saved} onClick={onDone}>
        {doneLabel}
      </button>
    </section>
  );
}
