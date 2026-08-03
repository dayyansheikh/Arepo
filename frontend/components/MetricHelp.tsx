"use client";

import Link from "next/link";
import { useCallback, useId, useRef, useState } from "react";
import { METRICS, type MetricId } from "@/lib/metrics";

/**
 * Reusable metric-help affordance. Renders the term (optionally) with a small
 * info icon; a plain-English definition, a short interpretation and a
 * "Learn more" link to the exact Methodology anchor appear in a popover.
 *
 * Accessibility: the trigger is a real button, so it is keyboard-focusable and
 * toggles with Enter/Space (works on touch). The popover also appears on hover
 * and focus, and closes on Escape or when focus/pointer leaves. Colour is never
 * the only cue — the dotted underline marks the term as explainable.
 */
export function MetricHelp({
  metric,
  showTerm = true,
  className = "",
}: {
  metric: MetricId;
  showTerm?: boolean;
  className?: string;
}) {
  const def = METRICS[metric];
  const panelId = useId();
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);

  const visible = pinned || hovered || focused;

  const handleBlur = useCallback((e: React.FocusEvent<HTMLSpanElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setFocused(false);
      setPinned(false);
    }
  }, []);

  return (
    <span
      ref={containerRef}
      className={`relative inline-flex items-center gap-1 ${className}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={handleBlur}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setPinned(false);
          setHovered(false);
        }
      }}
    >
      <button
        type="button"
        aria-expanded={visible}
        aria-controls={panelId}
        aria-label={showTerm ? undefined : `About ${def.term}`}
        onClick={() => setPinned((v) => !v)}
        className="focus-ring inline-flex items-center gap-1 text-left"
      >
        {showTerm && (
          <span className="border-b border-dotted border-arepo-muted/70">
            {def.term}
          </span>
        )}
        <span
          aria-hidden="true"
          className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-arepo-muted/60 text-[9px] font-semibold leading-none text-arepo-muted"
        >
          i
        </span>
      </button>

      {visible && (
        <span
          id={panelId}
          role="tooltip"
          className="absolute left-0 top-full z-50 mt-2 block w-72 rounded-[10px] border border-arepo-border bg-arepo-surface p-3 text-left shadow-[0_6px_20px_rgba(16,16,16,0.10)]"
        >
          <span className="block text-sm font-semibold text-arepo-ink">
            {def.term}
          </span>
          <span className="mt-1 block text-[13px] leading-relaxed text-arepo-ink2">
            {def.definition}
          </span>
          <span className="mt-1.5 block text-[13px] leading-relaxed text-arepo-muted">
            {def.interpretation}
          </span>
          <Link
            href={`/methodology#${def.id}`}
            className="focus-ring mt-2 inline-block text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover"
          >
            Learn more &rarr;
          </Link>
        </span>
      )}
    </span>
  );
}
