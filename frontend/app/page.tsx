"use client";

import Link from "next/link";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getOpportunityBoard } from "@/lib/api";
import type { OpportunityBoard } from "@/lib/types";
import { OpportunityCardView } from "@/components/OpportunityCardView";
import { CardGridSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PageHeader } from "@/components/ui";

export default function OpportunityBoardPage() {
  const { mode } = useMode();
  const { data, loading, error } = useAsync<OpportunityBoard>(
    () => getOpportunityBoard(mode),
    [mode]
  );

  return (
    <div className="space-y-8">
      <PageHeader
        title="Opportunity Board"
        lead="The markets that deserve a closer look today, ranked by a transparent Research Priority score. Each card explains why it appears and links to the full analysis. This is a research ranking, not expected profit."
      />

      <DisclaimerBanner>
        Arepo ranks market situations worth investigating. It is not trading advice and does not
        predict outcomes.
      </DisclaimerBanner>

      <div className="flex flex-wrap items-center justify-between gap-3">
        {data && (
          <p className="text-[13px] text-arepo-muted">
            {data.note} Considered {data.universe_considered} markets.
          </p>
        )}
        <Link
          href="/markets"
          className="focus-ring text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover"
        >
          Explore all markets &rarr;
        </Link>
      </div>

      {loading && <CardGridSkeleton count={9} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && data.cards.length === 0 && (
        <EmptyState message="No markets are standing out right now. Check back later or explore all markets." />
      )}

      {!loading && data && data.cards.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.cards.map((card) => (
            <OpportunityCardView key={`${card.market_id}-${card.token_id}`} card={card} />
          ))}
        </div>
      )}
    </div>
  );
}
