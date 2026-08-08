"use client";

import Link from "next/link";
import type { OpportunityCard } from "@/lib/types";
import { formatPercent } from "@/lib/format";
import { priorityBand } from "@/lib/opportunity";
import { directionLabel, DIRECTION_TONE_CLASS } from "@/lib/directional";
import { TagChip } from "./TagChip";
import { Badge } from "./ui";

const LIQ_TONE: Record<string, string> = {
  good: "text-arepo-pos",
  moderate: "text-arepo-ink2",
  thin: "text-arepo-warnText",
};

function timeLeft(hours: number | null): string {
  if (hours === null) return "no close time";
  if (hours <= 0) return "closing now";
  if (hours < 48) return `${Math.round(hours)}h to close`;
  return `${Math.round(hours / 24)}d to close`;
}

/**
 * One Opportunity Board card. It LEADS with the plain-English hypothesis (what the evidence
 * currently favours, or an explicit "not enough evidence" statement) and the market question,
 * so a reader learns the conclusion before any number. Research Priority is demoted to a small
 * labelled chip with a High/Medium/Low interpretation; evidence tags each explain themselves in
 * an accessible popover. This is the "lead with the conclusion, demote the score" redesign.
 */
export function OpportunityCardView({ card }: { card: OpportunityCard }) {
  const href = `/markets/${encodeURIComponent(card.market_id)}`;
  const band = priorityBand(card.research_priority);
  const dir = directionLabel(card.direction, card.outcome);

  return (
    <div className="flex flex-col rounded-card border border-arepo-border bg-arepo-surface p-5 shadow-arepo-sm">
      {/* Top line: the market question leads; probability sits to the side as context. */}
      <div className="flex items-start justify-between gap-3">
        <Link
          href={href}
          className="focus-ring rounded-md font-medium leading-snug text-arepo-ink hover:text-arepo-accentActive"
        >
          {card.question}
        </Link>
        <div className="flex-none text-right text-[13px] text-arepo-muted">
          <div className="font-tabular text-[15px] font-semibold text-arepo-ink">
            {formatPercent(card.probability, 0)}
          </div>
          <div>{card.outcome ?? "leading"}</div>
        </div>
      </div>

      {/* The hypothesis: the conclusion, first. */}
      <p className="mt-3 text-[13.5px] font-medium leading-relaxed text-arepo-ink2">
        {card.hypothesis}
      </p>

      {/* Direction cue, only when the evidence warrants a directional view. */}
      {card.directional && card.direction && (
        <div className="mt-2">
          <span
            className={`inline-flex items-center gap-1 text-[12px] font-medium ${DIRECTION_TONE_CLASS[dir.tone]}`}
          >
            <span aria-hidden="true">{dir.glyph}</span>
            {dir.text}
          </span>
        </div>
      )}

      {card.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {card.tags.map((t) => (
            <TagChip key={t.label} tag={t} />
          ))}
        </div>
      )}

      <p className="mt-3 flex-1 text-[13px] leading-relaxed text-arepo-muted">{card.explanation}</p>

      {/* Research Priority, demoted: a labelled chip with a plain interpretation, not a headline. */}
      <div className="mt-4 flex items-center gap-2 border-t border-arepo-border pt-3">
        <span
          className="inline-flex items-center gap-1.5 rounded-md bg-arepo-surface2 px-2 py-1"
          title="Research Priority: how urgently this market is worth investigating relative to others right now. Not expected profit."
        >
          <span className="text-[11px] uppercase tracking-wide text-arepo-muted">Priority</span>
          <span className="font-tabular text-[13px] font-semibold text-arepo-ink">
            {card.research_priority}
          </span>
          <span className={`text-[12px] font-medium ${band.tone}`}>{band.label}</span>
        </span>
        {card.high_priority && <Badge tone="accent">High priority</Badge>}
        <span className="ml-auto text-[12px] text-arepo-muted">{band.meaning}</span>
      </div>

      <div className="mt-3 flex items-center justify-between text-[12px] text-arepo-muted">
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className={LIQ_TONE[card.liquidity_quality] ?? "text-arepo-muted"}>
            {card.liquidity_quality} liquidity
          </span>
          <span>{timeLeft(card.time_remaining_hours)}</span>
          <span>
            {card.n_families === 1
              ? "1 independent line of evidence"
              : `${card.n_families} independent lines of evidence`}
          </span>
        </span>
        <Link
          href={href}
          className="focus-ring font-medium text-arepo-accentActive hover:text-arepo-accentHover"
        >
          View analysis &rarr;
        </Link>
      </div>
    </div>
  );
}
