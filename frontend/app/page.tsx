"use client";

import Link from "next/link";
import { useState } from "react";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getOpportunityBoard } from "@/lib/api";
import type { OpportunityBoard } from "@/lib/types";
import { OpportunityCardView } from "@/components/OpportunityCardView";
import { CardGridSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PageHeader } from "@/components/ui";

// Time-to-close horizons (spec §5): let a user focus on short-term opportunities closing within
// a week without hiding the full board.
const HORIZONS = [
  { id: "all", label: "All", hours: Infinity },
  { id: "7d", label: "Closing ≤ 7 days", hours: 24 * 7 },
  { id: "3d", label: "Closing ≤ 3 days", hours: 24 * 3 },
  { id: "24h", label: "Closing ≤ 24 hours", hours: 24 },
] as const;

type HorizonId = (typeof HORIZONS)[number]["id"];

export default function OpportunityBoardPage() {
  const { mode } = useMode();
  const [horizon, setHorizon] = useState<HorizonId>("all");
  const { data, loading, error } = useAsync<OpportunityBoard>(
    () => getOpportunityBoard(mode),
    [mode]
  );

  const maxHours = HORIZONS.find((h) => h.id === horizon)?.hours ?? Infinity;
  const cards = (data?.cards ?? []).filter((c) => {
    if (maxHours === Infinity) return true;
    // Keep only markets with a known close time within the window (short-term focus).
    return c.time_remaining_hours !== null && c.time_remaining_hours <= maxHours;
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Opportunities"
        lead="The markets that deserve a closer look today. Each card leads with what the evidence currently favours, why, and how reliable that view is, then links to the full analysis. This is a research ranking, not expected profit."
      />

      <DisclaimerBanner>
        Arepo ranks market situations worth investigating. It is not trading advice and does not
        predict outcomes.
      </DisclaimerBanner>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex flex-wrap items-center gap-1.5"
          role="group"
          aria-label="Filter by time to close"
        >
          {HORIZONS.map((h) => (
            <button
              key={h.id}
              type="button"
              aria-pressed={horizon === h.id}
              onClick={() => setHorizon(h.id)}
              className={`focus-ring rounded-full border px-3 py-1 text-[12.5px] font-medium transition-colors ${
                horizon === h.id
                  ? "border-arepo-accent bg-arepo-accentTint text-arepo-accentActive"
                  : "border-arepo-border bg-arepo-surface text-arepo-muted hover:text-arepo-ink"
              }`}
            >
              {h.label}
            </button>
          ))}
        </div>
        <Link
          href="/markets"
          className="focus-ring text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover"
        >
          Explore all markets &rarr;
        </Link>
      </div>

      {data && (
        <p className="text-[13px] text-arepo-muted">
          {data.note} Considered {data.universe_considered} markets.
          {horizon !== "all" &&
            ` Showing ${cards.length} of ${data.cards.length} that close within this window.`}
        </p>
      )}

      {loading && <CardGridSkeleton count={9} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && cards.length === 0 && (
        <EmptyState
          message={
            horizon === "all"
              ? "No markets are standing out right now. Check back later or explore all markets."
              : "No standout markets close within this window. Try a longer horizon."
          }
        />
      )}

      {!loading && data && cards.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((card) => (
            <OpportunityCardView key={`${card.market_id}-${card.token_id}`} card={card} />
          ))}
        </div>
      )}
    </div>
  );
}
