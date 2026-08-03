"use client";

import Link from "next/link";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getOverview } from "@/lib/api";
import type { MarketCard } from "@/lib/types";
import { formatCurrencyCompact, formatDurationSeconds, formatPercent } from "@/lib/format";
import { MarketCardView } from "@/components/MarketCardView";
import { SignalItem } from "@/components/SignalItem";
import { CardGridSkeleton, ListSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { SectionTitle } from "@/components/ui";
import { StrengthMeter } from "@/components/StrengthMeter";

const MODE_LABEL: Record<string, string> = {
  live: "Live",
  cached: "Cached",
  replay: "Replay",
};

function CardGrid({ markets }: { markets: MarketCard[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {markets.map((m) => (
        <MarketCardView key={m.id} market={m} />
      ))}
    </div>
  );
}

/** Compact ranked list row: category, question, a metric value, strength. */
function MarketRow({ market, metric }: { market: MarketCard; metric: "volume" | "spread" }) {
  const value =
    metric === "volume"
      ? formatCurrencyCompact(market.volume)
      : formatPercent(market.spread, 2);
  return (
    <Link
      href={`/markets/${encodeURIComponent(market.id)}`}
      className="focus-ring flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-arepo-surface2"
    >
      <span className="min-w-0 flex-1 truncate text-sm font-medium text-arepo-ink">
        {market.question}
      </span>
      <span className="w-24 shrink-0 text-right font-tabular text-[13px] text-arepo-muted">
        {value}
      </span>
      <span className="w-28 shrink-0">
        {market.signal_strength !== null && <StrengthMeter strength={market.signal_strength} />}
      </span>
    </Link>
  );
}

function RankedList({
  title,
  markets,
  metric,
  seeAll,
}: {
  title: string;
  markets: MarketCard[];
  metric: "volume" | "spread";
  seeAll?: boolean;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <SectionTitle>{title}</SectionTitle>
        {seeAll && (
          <Link href="/markets" className="text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover">
            See all markets &rarr;
          </Link>
        )}
      </div>
      {markets.length === 0 ? (
        <EmptyState message="Nothing to show in this view right now." />
      ) : (
        <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface divide-y divide-arepo-border">
          {markets.slice(0, 6).map((m) => (
            <MarketRow key={`${title}-${m.id}`} market={m} metric={metric} />
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
      <div className="space-y-4">
        <div>
          <h1 className="display-title text-[30px] sm:text-[34px]">Overview</h1>
          <p className="mt-2 max-w-reading text-[15px] leading-relaxed text-arepo-ink2">
            A calm reading of the markets Arepo is watching right now: which are moving, which
            are busiest, and where its screening signals are firing.
          </p>
        </div>
        {data?.status && (
          <p className="text-[13px] text-arepo-muted">
            Showing{" "}
            <span className="font-medium text-arepo-ink">{MODE_LABEL[data.status.mode] ?? data.status.mode}</span>{" "}
            data, updated {formatDurationSeconds(data.status.data_age_seconds)} ago.
          </p>
        )}
        <DisclaimerBanner />
      </div>

      {loading && (
        <div className="space-y-10">
          <CardGridSkeleton count={8} />
          <ListSkeleton rows={5} />
        </div>
      )}

      {!loading && error && <ErrorState message={error} />}

      {!loading && data && (
        <>
          <section className="space-y-3">
            <div className="flex items-baseline justify-between">
              <SectionTitle>Top movers</SectionTitle>
              <span className="text-[13px] text-arepo-muted">Ranked by signal strength</span>
            </div>
            {data.top_movers.length === 0 ? (
              <EmptyState message="No market movement to report right now." />
            ) : (
              <CardGrid markets={data.top_movers} />
            )}
          </section>

          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <RankedList title="Most active" markets={data.most_active} metric="volume" seeAll />
            <RankedList title="Highest volume" markets={data.highest_volume} metric="volume" />
          </div>

          {data.widest_spreads.length > 0 && (
            <RankedList title="Widest spreads" markets={data.widest_spreads} metric="spread" />
          )}

          <section className="space-y-3">
            <SectionTitle>Recent signals</SectionTitle>
            {data.recent_signals.length === 0 ? (
              <EmptyState message="No signals have fired recently." />
            ) : (
              <div className="space-y-3">
                {data.recent_signals.slice(0, 5).map((s, i) => (
                  <SignalItem key={`${s.kind}-${s.token_id}-${i}`} signal={s} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
