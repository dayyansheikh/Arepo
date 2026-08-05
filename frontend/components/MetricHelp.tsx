"use client";

import Link from "next/link";
import { METRICS, type MetricId } from "@/lib/metrics";
import { Popover } from "./Popover";

/**
 * Reusable metric-help affordance. Renders the term (optionally) with a small info icon; a
 * plain-English definition, a short interpretation and a "Learn more" link to the exact Methodology
 * anchor appear in a viewport-aware popover (see components/Popover.tsx). The dotted underline marks
 * the term as explainable, so colour is never the only cue.
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

  return (
    <Popover
      triggerClassName={className}
      label={showTerm ? undefined : `About ${def.term}`}
      panelClassName="w-72"
      trigger={
        <>
          {showTerm && (
            <span className="border-b border-dotted border-arepo-muted/70">{def.term}</span>
          )}
          <span
            aria-hidden="true"
            className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-arepo-muted/60 text-[9px] font-semibold leading-none text-arepo-muted"
          >
            i
          </span>
        </>
      }
    >
      <span className="block text-sm font-semibold text-arepo-ink">{def.term}</span>
      <span className="mt-1 block text-sm leading-relaxed text-arepo-ink2">{def.definition}</span>
      <span className="mt-1.5 block text-sm leading-relaxed text-arepo-muted">
        {def.interpretation}
      </span>
      <Link
        href={`/methodology#${def.id}`}
        className="focus-ring mt-2 inline-block text-sm font-medium text-arepo-accentActive hover:text-arepo-accentHover"
      >
        Learn more &rarr;
      </Link>
    </Popover>
  );
}
