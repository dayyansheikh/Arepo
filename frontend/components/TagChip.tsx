"use client";

import { useCallback, useId, useRef, useState } from "react";
import type { OpportunityTag } from "@/lib/types";
import { FAMILY_LABEL, FAMILY_WHY } from "@/lib/opportunity";

/**
 * A single evidence tag. The chip shows the tag's name; a popover gives the plain-English
 * definition, why it matters, its evidence family and a link to the exact Methodology section.
 *
 * Accessibility (spec §8): the trigger is a real button, keyboard-focusable, toggled with
 * Enter/Space (so it works on touch). The popover also opens on hover and focus and closes on
 * Escape or when focus/pointer leaves. The reader never has to leave the market page to learn
 * what a tag means; the Methodology link is there only for those who want the full definition.
 */
export function TagChip({ tag }: { tag: OpportunityTag }) {
  const panelId = useId();
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const visible = pinned || hovered || focused;

  const handleBlur = useCallback((e: React.FocusEvent<HTMLSpanElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setFocused(false);
      setPinned(false);
    }
  }, []);

  const why = FAMILY_WHY[tag.family] ?? "An independent line of evidence Arepo tracks.";
  const familyLabel = FAMILY_LABEL[tag.family] ?? tag.family.replace(/_/g, " ");

  return (
    <span
      ref={ref}
      className="relative inline-flex"
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
        onClick={() => setPinned((v) => !v)}
        className="focus-ring inline-flex items-center rounded-full border border-arepo-border bg-arepo-surface2 px-2.5 py-0.5 text-[11px] font-medium text-arepo-ink2 hover:bg-arepo-accentTint hover:text-arepo-accentActive"
      >
        {tag.label}
      </button>

      {visible && (
        // A self-contained, non-interactive explanation (role="tooltip"). The old "Full
        // definition" link was removed (spec §3): several tag anchors (trade-flow,
        // wallet-concentration, trade-timing) had no matching Methodology section, so the link
        // landed on an irrelevant place. The popover explains the tag in full without navigation.
        <span
          id={panelId}
          role="tooltip"
          className="absolute left-0 top-full z-50 mt-2 block w-72 rounded-[10px] border border-arepo-border bg-arepo-surface p-3 text-left shadow-[0_6px_20px_rgba(16,16,16,0.10)]"
        >
          <span className="block text-sm font-semibold text-arepo-ink">{tag.label}</span>
          <span className="mt-1 block text-sm leading-relaxed text-arepo-ink2">
            {tag.explanation}
          </span>
          <span className="mt-1.5 block text-[13px] leading-relaxed text-arepo-muted">
            Why it matters: {why}
          </span>
          <span className="mt-1.5 block text-[12px] uppercase tracking-wide text-arepo-muted">
            Evidence family: {familyLabel}
          </span>
        </span>
      )}
    </span>
  );
}
