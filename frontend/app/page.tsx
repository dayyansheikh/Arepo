"use client";

import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getOverview } from "@/lib/api";
import type { MarketCard } from "@/lib/types";
import { MarketCardView } from "@/components/MarketCardView";
import { SignalItem } from "@/components/SignalItem";
import { CardGridSkeleton, ListSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";

function MarketSection({ title, markets }: { title: string; markets: MarketCard[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">{title}</h2>
      {markets.length === 0 ? (
        <EmptyState message="No markets to show right now." />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {markets.map((m) => (
            <MarketCardView key={m.id} market={m} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function OverviewPage() {
  const { mode } = useMode();
  const { data, loading, error } = useAsync(() => getOverview(mode), [mode]);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="mt-1 text-sm text-muted-fg">
          A fixed reading of the market as of this instrument&apos;s last update. Screening
          heuristics only — not trading advice, not proof of anything.
        </p>
      </div>

      {loading && (
        <div className="space-y-10">
          <CardGridSkeleton />
          <CardGridSkeleton />
        </div>
      )}

      {!loading && error && <ErrorState message={error} />}

      {!loading && data && (
        <>
          <MarketSection title="Top movers" markets={data.top_movers} />
          <MarketSection title="Most active" markets={data.most_active} />
          <MarketSection title="Highest volume" markets={data.highest_volume} />
          <MarketSection title="Widest spreads" markets={data.widest_spreads} />

          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">
              Recent signals
            </h2>
            {data.recent_signals.length === 0 ? (
              <EmptyState message="No recent signals." />
            ) : (
              <div className="space-y-3">
                {data.recent_signals.map((s, i) => (
                  <SignalItem key={`${s.kind}-${s.token_id}-${i}`} signal={s} />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {!loading && !error && !data && <ListSkeleton />}
    </div>
  );
}
