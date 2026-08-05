"use client";

import type { OpportunityTag } from "@/lib/types";
import { FAMILY_LABEL, FAMILY_WHY } from "@/lib/opportunity";
import { Popover } from "./Popover";

/**
 * A single evidence tag. The chip shows the tag's name; a viewport-aware popover (see
 * components/Popover.tsx) gives the plain-English definition, why it matters and its evidence
 * family. It opens on hover, focus and tap and never overflows the viewport.
 */
export function TagChip({ tag }: { tag: OpportunityTag }) {
  const why = FAMILY_WHY[tag.family] ?? "An independent line of evidence Arepo tracks.";
  const familyLabel = FAMILY_LABEL[tag.family] ?? tag.family.replace(/_/g, " ");

  return (
    <Popover
      panelClassName="w-72"
      triggerClassName="rounded-full border border-arepo-border bg-arepo-surface2 px-2.5 py-0.5 text-[11px] font-medium text-arepo-ink2 hover:bg-arepo-accentTint hover:text-arepo-accentActive"
      trigger={tag.label}
    >
      <span className="block text-sm font-semibold text-arepo-ink">{tag.label}</span>
      <span className="mt-1 block text-sm leading-relaxed text-arepo-ink2">{tag.explanation}</span>
      <span className="mt-1.5 block text-[13px] leading-relaxed text-arepo-muted">
        Why it matters: {why}
      </span>
      <span className="mt-1.5 block text-[12px] uppercase tracking-wide text-arepo-muted">
        Evidence family: {familyLabel}
      </span>
    </Popover>
  );
}
