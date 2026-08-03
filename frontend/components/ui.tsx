import type { ReactNode } from "react";

/** Uppercase eyebrow label used above card grids, tables and sections. */
export function SectionLabel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <h2 className={`section-label ${className}`}>{children}</h2>;
}

/** Expandable "Show the maths" / "Show advanced" panel (native details/summary). */
export function Disclose({
  summary,
  children,
  defaultOpen = false,
  className = "",
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  return (
    <details className={`disclose ${className}`} open={defaultOpen}>
      <summary className="focus-ring">{summary}</summary>
      <div className="pt-3">{children}</div>
    </details>
  );
}

/** A single stat tile: label (optionally with a MetricHelp) over a big value. */
export function StatTile({
  label,
  value,
  help,
  emphasis = false,
}: {
  label: ReactNode;
  value: ReactNode;
  help?: ReactNode;
  emphasis?: boolean;
}) {
  return (
    <div
      className={`rounded-card border p-5 ${
        emphasis
          ? "border-arepo-accentBorder bg-arepo-accentTint"
          : "border-arepo-border bg-arepo-surface"
      }`}
    >
      <div
        className={`mb-2 flex items-center gap-1 text-xs ${
          emphasis ? "text-arepo-accentActive" : "text-arepo-muted"
        }`}
      >
        {label}
        {help}
      </div>
      <div
        className={`font-tabular text-2xl font-bold ${
          emphasis ? "text-arepo-accentActive" : "text-arepo-ink"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

type BadgeTone =
  | "good"
  | "limited"
  | "poor"
  | "strong"
  | "moderate"
  | "weak"
  | "neutral"
  | "accent";

const TONE_CLASS: Record<BadgeTone, string> = {
  // Data-quality: green/amber/neutral, but each carries its own word too.
  good: "bg-arepo-pos/12 text-arepo-pos",
  limited: "bg-arepo-warn/12 text-arepo-warnText",
  poor: "bg-arepo-neg/12 text-arepo-neg",
  // Strength tiers: distinguished by the word; accent only for STRONG.
  strong: "bg-arepo-accentTint text-arepo-accentActive",
  moderate: "bg-arepo-surface2 text-arepo-ink2",
  weak: "bg-arepo-surface2 text-arepo-muted",
  neutral: "bg-arepo-surface2 text-arepo-muted",
  accent: "bg-arepo-accentTint text-arepo-accentActive",
};

/** Small pill label. Tone sets the tint; the child word carries the meaning. */
export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: BadgeTone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${TONE_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}

/** Status/category dot + text, e.g. an "Active" marker. Colour never alone. */
export function StatusDot({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "active" | "neutral";
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-arepo-muted">
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${
          tone === "active" ? "bg-arepo-pos" : "bg-arepo-muted"
        }`}
      />
      {label}
    </span>
  );
}
