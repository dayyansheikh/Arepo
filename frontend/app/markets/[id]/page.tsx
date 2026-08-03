"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getMarket } from "@/lib/api";
import { formatCurrencyCompact, formatDate } from "@/lib/format";
import { OutcomePanel } from "@/components/OutcomePanel";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { SignalItem } from "@/components/SignalItem";
import { MetricHelp } from "@/components/MetricHelp";
import { SectionTitle } from "@/components/ui";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { SkeletonBlock } from "@/components/Skeletons";

// Plain-English label for where this market's data came from.
const SOURCE_LABEL: Record<string, string> = {
  live: "Live",
  cached: "Cached",
  replay: "Replay",
};
const SOURCE_HELP: Record<string, string> = {
  live: "Fetched just now from the public Polymarket API.",
  cached: "Most recent stored copy, served without a live call.",
  replay: "A fixed demonstration dataset, not live markets.",
};

export default function MarketDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const { mode } = useMode();
  const { data, loading, error, notFound } = useAsync(() => getMarket(id, mode), [id, mode]);

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonBlock className="h-4 w-40" />
        <SkeletonBlock className="h-8 w-2/3" />
        <SkeletonBlock className="h-4 w-1/3" />
        <SkeletonBlock className="h-72 w-full" />
      </div>
    );
  }

  if (notFound) {
    return <ErrorState title="Market not found" message="This market does not exist in the current mode." />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!data) return null;

  const { market } = data;

  // The chart's first series renders in Arepo red, so put the market's
  // leading outcome (highest implied probability) first.
  const chartOutcomes = [...market.outcomes].sort(
    (a, b) => (b.implied_probability ?? -1) - (a.implied_probability ?? -1)
  );

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] text-arepo-muted">
          <Link href="/markets" className="focus-ring hover:text-arepo-ink">
            Markets
          </Link>
          {market.category && (
            <>
              <span aria-hidden="true">/</span>
              <span>{market.category}</span>
            </>
          )}
        </nav>

        <h1 className="display-title max-w-reading text-[28px] leading-tight sm:text-[32px]">
          {market.question}
        </h1>

        <div className="flex flex-wrap gap-x-10 gap-y-3 border-b border-arepo-border pb-6">
          <div>
            <div className="text-[13px] text-arepo-muted">Volume</div>
            <div className="font-tabular text-[15px] font-semibold text-arepo-ink">
              {formatCurrencyCompact(market.volume)}
            </div>
          </div>
          <div>
            <div className="text-[13px] text-arepo-muted">24h volume</div>
            <div className="font-tabular text-[15px] font-semibold text-arepo-ink">
              {formatCurrencyCompact(market.volume_24hr)}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1 text-[13px] text-arepo-muted">
              <MetricHelp metric="liquidity" />
            </div>
            <div className="font-tabular text-[15px] font-semibold text-arepo-ink">
              {formatCurrencyCompact(market.liquidity)}
            </div>
          </div>
          <div>
            <div className="text-[13px] text-arepo-muted">Ends</div>
            <div className="font-tabular text-[15px] font-semibold text-arepo-ink">
              {formatDate(market.end_date)}
            </div>
          </div>
          <div>
            <div className="text-[13px] text-arepo-muted">Source</div>
            <div
              className="text-[15px] font-semibold text-arepo-ink"
              title={SOURCE_HELP[market.data_source] ?? undefined}
            >
              {SOURCE_LABEL[market.data_source] ?? market.data_source}
            </div>
          </div>
        </div>
      </div>

      <section className="space-y-3">
        <SectionTitle>Price history</SectionTitle>
        <div className="panel p-5">
          <PriceHistoryChart
            priceHistory={market.price_history}
            series={chartOutcomes.map((o) => ({ key: o.token_id, label: o.name }))}
          />
        </div>
      </section>

      <section className="space-y-3">
        <SectionTitle>Outcomes</SectionTitle>
        {market.outcomes.length === 0 ? (
          <EmptyState message="No outcome data available." />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {market.outcomes.map((o) => (
              <OutcomePanel key={o.token_id} outcome={o} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <SectionTitle>Signals</SectionTitle>
        {market.signals.length === 0 ? (
          <EmptyState message="No signals detected for this market." />
        ) : (
          <div className="space-y-3">
            {market.signals.map((s, i) => (
              <SignalItem key={`${s.kind}-${s.token_id}-${i}`} signal={s} />
            ))}
          </div>
        )}
      </section>

      <section className="panel space-y-2 p-5">
        <SectionTitle>Limitations</SectionTitle>
        <p className="text-[15px] leading-relaxed text-arepo-ink2">{market.limitations}</p>
        <p className="text-[13px] text-arepo-muted">
          Probabilities shown are implied by market prices, not verified truths. See{" "}
          <Link href="/methodology" className="text-arepo-accentActive hover:text-arepo-accentHover">
            Methodology
          </Link>{" "}
          for caveats.
        </p>
      </section>
    </div>
  );
}
