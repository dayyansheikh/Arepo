"use client";

import Link from "next/link";
import { LogoMark } from "@/components/Logo";

/**
 * The Arepo brand showcase used by every account page (sign-in, sign-up, reset, forgot, verify) -
 * spec §12. The brand is the visual focus: a large grid symbol, the supplied wordmark asset (with
 * the red mark under the A) and the Arepo meaning. The form sits beside it, clearly secondary.
 * Two columns on desktop; stacks on mobile with the brand first.
 */
export function AuthShell({
  title,
  lead,
  children,
  footer,
}: {
  title: string;
  lead?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="mx-auto grid w-full max-w-4xl grid-cols-1 items-start gap-10 py-4 lg:grid-cols-[1.1fr_1fr] lg:gap-16 lg:py-10">
      {/* Brand panel: the primary focus. */}
      <div className="flex flex-col items-start">
        <LogoMark size={72} title="Arepo" />
        {/* The supplied wordmark (red mark beneath the A); not recreated with a substitute font. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/brand/arepo-wordmark.png"
          alt="AREPO"
          className="mt-5 h-auto w-56 max-w-full select-none"
        />
        <p className="mt-6 max-w-reading text-[15px] leading-relaxed text-arepo-ink2">
          Just as Arepo is believed to have been created to unite the Sator Square, we unite
          information as it is created, conviction as it is expressed, action as it is taken, and
          markets as they move. Arepo reads the hidden signal found between the lines.
        </p>
        <p className="mt-4 max-w-reading text-[14px] leading-relaxed text-arepo-muted">
          A free account unlocks high-priority research alerts, saved markets and your own
          preferences. The rest of Arepo stays open without one.
        </p>
      </div>

      {/* Form: visually secondary. */}
      <div className="w-full">
        <h1 className="font-display text-xl font-semibold tracking-tight text-arepo-ink">
          {title}
        </h1>
        {lead && <p className="mt-2 text-[14px] leading-relaxed text-arepo-muted">{lead}</p>}
        <div className="mt-5 rounded-card border border-arepo-border bg-arepo-surface p-6 shadow-arepo-sm">
          {children}
        </div>
        {footer && <div className="mt-4 text-[13px] text-arepo-muted">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({
  label,
  type = "text",
  value,
  onChange,
  required,
  autoComplete,
  hint,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  autoComplete?: string;
  hint?: string;
}) {
  return (
    <label className="mb-4 block">
      <span className="mb-1 block text-[13px] font-medium text-arepo-ink2">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="focus-ring w-full rounded-md border border-arepo-border bg-arepo-surface px-3 py-2 text-[14px] text-arepo-ink placeholder:text-arepo-muted"
      />
      {hint && <span className="mt-1 block text-[12px] text-arepo-muted">{hint}</span>}
    </label>
  );
}

export function SubmitButton({
  children,
  pending,
  disabled,
}: {
  children: React.ReactNode;
  pending?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={pending || disabled}
      className="focus-ring inline-flex w-full items-center justify-center rounded-md bg-arepo-accent px-4 py-2 text-[14px] font-semibold text-white transition-colors hover:bg-arepo-accentHover disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending ? "Working…" : children}
    </button>
  );
}

export function FormMessage({ tone, children }: { tone: "error" | "ok"; children: React.ReactNode }) {
  if (!children) return null;
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={`mb-4 rounded-md border px-3 py-2 text-[13px] ${
        tone === "error"
          ? "border-arepo-warn/30 bg-arepo-warn/10 text-arepo-warnText"
          : "border-arepo-border bg-arepo-surface2 text-arepo-ink2"
      }`}
    >
      {children}
    </p>
  );
}

export function TextLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="focus-ring font-medium text-arepo-accentActive hover:text-arepo-accentHover"
    >
      {children}
    </Link>
  );
}
