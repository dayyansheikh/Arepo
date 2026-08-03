"use client";

import Link from "next/link";

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
    <div className="mx-auto w-full max-w-md">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-arepo-ink">
        {title}
      </h1>
      {lead && <p className="mt-2 text-[14px] leading-relaxed text-arepo-muted">{lead}</p>}
      <div className="mt-6 rounded-card border border-arepo-border bg-arepo-surface p-6 shadow-arepo-sm">
        {children}
      </div>
      {footer && <div className="mt-4 text-[13px] text-arepo-muted">{footer}</div>}
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
