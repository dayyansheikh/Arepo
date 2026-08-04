"use client";

import Link from "next/link";
import { useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getOpportunityBoard } from "@/lib/api";
import type { BoardView, OpportunityBoard } from "@/lib/types";
import { OpportunityCardView } from "@/components/OpportunityCardView";
import { CardGridSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PageHeader } from "@/components/ui";

// Selectivity (spec §4): the default board shows only markets with a usable directional view, so
// neutral markets never dominate. Other views are available; Explore holds the full neutral set.
const VIEWS: { id: BoardView; label: string }[] = [
  { id: "directional", label: "Directional only" },
  { id: "strongest", label: "Strongest views" },
  { id: "inconclusive", label: "Inconclusive" },
  { id: "all", label: "All screened" },
];

// Time-to-close horizons (spec §5): focus on short-term opportunities without hiding the board.
const HORIZONS = [
  { id: "all", label: "All", hours: Infinity },
  { id: "7d", label: "≤ 7 days", hours: 24 * 7 },
  { id: "3d", label: "≤ 3 days", hours: 24 * 3 },
  { id: "24h", label: "≤ 24 hours", hours: 24 },
] as const;

type HorizonId = (typeof HORIZONS)[number]["id"];

function isView(v: string | null): v is BoardView {
  return v === "directional" || v === "strongest" || v === "inconclusive" || v === "all";
}

export default function OpportunityBoardPage() {
  const { mode } = useMode();
  const router = useRouter();
  const params = useSearchParams();

  // View and horizon are read from the URL so Back/Forward/refresh/shared links restore them.
  const view: BoardView = isView(params.get("view")) ? (params.get("view") as BoardView) : "directional";
  const horizon: HorizonId =
    (HORIZONS.find((h) => h.id === params.get("horizon"))?.id as HorizonId) ?? "all";

  const setParam = useCallback(
    (key: string, value: string, dflt: string) => {
      const next = new URLSearchParams(params.toString());
      if (value === dflt) next.delete(key);
      else next.set(key, value);
      const qs = next.toString();
      router.replace(qs ? `/?${qs}` : "/", { scroll: false });
    },
    [params, router]
  );

  const { data, loading, error } = useAsync<OpportunityBoard>(
    () => getOpportunityBoard(mode, view),
    [mode, view]
  );

  const maxHours = HORIZONS.find((h) => h.id === horizon)?.hours ?? Infinity;
  const cards = (data?.cards ?? []).filter((c) => {
    if (maxHours === Infinity) return true;
    return c.time_remaining_hours !== null && c.time_remaining_hours <= maxHours;
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Opportunities"
        lead="The markets where Arepo currently has a usable directional hypothesis. Each card leads with what the evidence favours, why, and how reliable that view is. Neutral markets are kept in Explore, not forced onto this board. This is a research ranking, not expected profit."
      />

      <DisclaimerBanner>
        Arepo ranks market situations worth investigating. It is not trading advice and does not
        predict outcomes.
      </DisclaimerBanner>

      {/* How selective Arepo is right now (spec §4). */}
      {data && (
        <p className="text-[13.5px] text-arepo-ink2">
          Arepo screened <strong>{data.screened_count}</strong> markets;{" "}
          <strong>{data.directional_count}</strong> currently meet the evidence and quality
          requirements for a directional view.
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Board view">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              type="button"
              aria-pressed={view === v.id}
              onClick={() => setParam("view", v.id, "directional")}
              className={`focus-ring rounded-full border px-3 py-1 text-[12.5px] font-medium transition-colors ${
                view === v.id
                  ? "border-arepo-accent bg-arepo-accentTint text-arepo-accentActive"
                  : "border-arepo-border bg-arepo-surface text-arepo-muted hover:text-arepo-ink"
              }`}
            >
              {v.label}
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

      <div
        className="flex flex-wrap items-center gap-1.5"
        role="group"
        aria-label="Filter by time to close"
      >
        <span className="mr-1 text-[12px] text-arepo-muted">Closing:</span>
        {HORIZONS.map((h) => (
          <button
            key={h.id}
            type="button"
            aria-pressed={horizon === h.id}
            onClick={() => setParam("horizon", h.id, "all")}
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

      {loading && <CardGridSkeleton count={9} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && cards.length === 0 && (
        <EmptyState
          message={
            view === "directional"
              ? "Arepo has no usable directional view right now. Try 'All screened', widen the horizon, or explore all markets."
              : "No markets match this view and horizon. Try a different view."
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
