import type { ReactNode } from "react";
import type { Tone } from "@/lib/lab/model";
import { theme } from "@/lib/theme";

export const TONE_PILL: Record<Tone, string> = {
  pos: "bg-arepo-pos/10 text-arepo-pos",
  warn: "bg-arepo-warn/15 text-arepo-warnText",
  neg: "bg-arepo-neg/10 text-arepo-neg",
  accent: "bg-arepo-accentTint text-arepo-accentActive",
  neutral: "bg-arepo-surface2 text-arepo-ink2",
  muted: "bg-arepo-surface2 text-arepo-muted",
};

export const TONE_COLOR: Record<Tone, string> = {
  pos: theme.pos,
  warn: theme.warn,
  neg: theme.neg,
  accent: theme.accent,
  neutral: theme.series2,
  muted: theme.borderStrong,
};

/** Small rounded label; the word always carries the meaning, the tint only supports it. */
export function Pill({
  tone = "neutral",
  children,
  title,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11.5px] font-semibold ${TONE_PILL[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Dot({ tone, pulse = false, size = 8 }: { tone: Tone; pulse?: boolean; size?: number }) {
  return (
    <span aria-hidden="true" className="relative inline-flex flex-none" style={{ width: size, height: size }}>
      {pulse ? (
        <span
          className="lab-ping absolute inset-0 rounded-full"
          style={{ background: TONE_COLOR[tone] }}
        />
      ) : null}
      <span className="relative inline-flex h-full w-full rounded-full" style={{ background: TONE_COLOR[tone] }} />
    </span>
  );
}

/**
 * One idea per section: an eyebrow, a display-face title, an optional one-line lead, and an
 * optional right-hand aside (a badge or a headline number).
 */
export function LabSection({
  id,
  eyebrow,
  title,
  lead,
  aside,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lead?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="lab-rise scroll-mt-24">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <p className="section-label">{eyebrow}</p>
          <h2 id={`${id}-title`} className="display-title mt-1 text-[24px] sm:text-[28px]">
            {title}
          </h2>
          {lead ? <p className="mt-1.5 max-w-reading text-[14.5px] leading-relaxed text-arepo-ink2">{lead}</p> : null}
        </div>
        {aside ? <div className="flex-none">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`panel p-5 sm:p-6 ${className}`}>{children}</div>;
}

/** Calm, honest empty state used when a block is absent from the snapshot. */
export function Quiet({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-control border border-dashed border-arepo-border px-4 py-5 text-center text-[13.5px] text-arepo-muted">
      {children}
    </p>
  );
}

/** Horizontal progress bar with an accessible text value. */
export function ProgressBar({
  value,
  max,
  label,
  tone = "accent",
}: {
  value: number;
  max: number;
  label: string;
  tone?: Tone;
}) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className="h-2 w-full overflow-hidden rounded-full bg-arepo-surface2"
    >
      <div
        className="lab-grow h-full rounded-full"
        style={{ width: `${pct}%`, background: TONE_COLOR[tone] }}
      />
    </div>
  );
}

export const nf = new Intl.NumberFormat("en-GB");
export function fmtCount(n: number | null | undefined): string {
  return typeof n === "number" && Number.isFinite(n) ? nf.format(n) : "–";
}
