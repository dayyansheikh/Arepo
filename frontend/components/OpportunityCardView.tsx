import Link from "next/link";
import type { OpportunityCard } from "@/lib/types";
import { formatPercent } from "@/lib/format";
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
 * One Opportunity Board card. Leads with the Research Priority score (a research ranking, not
 * expected profit), states the market and outcome, shows the tags that fired (each links to
 * its methodology and explains itself on hover), and links to the full market analysis.
 */
export function OpportunityCardView({ card }: { card: OpportunityCard }) {
  const href = `/markets/${encodeURIComponent(card.market_id)}`;
  return (
    <div className="flex flex-col rounded-card border border-arepo-border bg-arepo-surface p-5 shadow-arepo-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div
            className="flex h-11 w-11 flex-none flex-col items-center justify-center rounded-lg bg-arepo-surface2"
            title="Research Priority: a transparent ranking of how much this market deserves a look, not expected profit."
          >
            <span className="font-tabular text-[17px] font-bold leading-none text-arepo-ink">
              {card.research_priority}
            </span>
            <span className="text-[9px] uppercase tracking-wide text-arepo-muted">prio</span>
          </div>
          <div className="text-[13px] text-arepo-muted">
            <div>Research Priority</div>
            {card.high_priority && (
              <Badge tone="accent">High priority</Badge>
            )}
          </div>
        </div>
        <div className="text-right text-[13px] text-arepo-muted">
          <div className="font-tabular text-[15px] font-semibold text-arepo-ink">
            {formatPercent(card.probability, 0)}
          </div>
          <div>{card.outcome ?? "leading"}</div>
        </div>
      </div>

      <Link
        href={href}
        className="focus-ring mt-3 rounded-md font-medium leading-snug text-arepo-ink hover:text-arepo-accentActive"
      >
        {card.question}
      </Link>

      {card.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {card.tags.map((t) => (
            <Link
              key={t.label}
              href={`/methodology#${t.methodology_anchor}`}
              title={t.explanation}
              className="focus-ring inline-flex items-center rounded-full bg-arepo-surface2 px-2.5 py-0.5 text-[11px] font-medium text-arepo-ink2 hover:bg-arepo-accentTint hover:text-arepo-accentActive"
            >
              {t.label}
            </Link>
          ))}
        </div>
      )}

      <p className="mt-3 flex-1 text-[13px] leading-relaxed text-arepo-muted">{card.explanation}</p>

      <div className="mt-4 flex items-center justify-between border-t border-arepo-border pt-3 text-[12px] text-arepo-muted">
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className={LIQ_TONE[card.liquidity_quality] ?? "text-arepo-muted"}>
            {card.liquidity_quality} liquidity
          </span>
          <span>{timeLeft(card.time_remaining_hours)}</span>
          <span>{card.n_families} evidence</span>
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
