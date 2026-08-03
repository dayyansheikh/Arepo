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
import { SectionLabel } from "@/components/ui";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { SkeletonBlock } from "@/components/Skeletons";

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

        <h1 className="max-w-reading text-[30px] font-semibold leading-tight tracking-[-0.01em] text-arepo-ink">
          {market.question}
        </h1>

        <div className="flex flex-wrap gap-x-10 gap-y-3 border-b border-arepo-border pb-6">
          <div>
            <div className="text-xs text-arepo-muted">Volume</div>
            <div className="font-tabular text-sm font-semibold text-arepo-ink">
              {formatCurrencyCompact(market.volume)}
            </div>
          </div>
          <div>
            <div className="text-xs text-arepo-muted">24h volume</div>
            <div className="font-tabular text-sm font-semibold text-arepo-ink">
              {formatCurrencyCompact(market.volume_24hr)}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1 text-xs text-arepo-muted">
              <MetricHelp metric="liquidity" />
            </div>
            <div className="font-tabular text-sm font-semibold text-arepo-ink">
              {formatCurrencyCompact(market.liquidity)}
            </div>
          </div>
          <div>
            <div className="text-xs text-arepo-muted">Ends</div>
            <div className="font-tabular text-sm font-semibold text-arepo-ink">
              {formatDate(market.end_date)}
            </div>
          </div>
          <div>
            <div className="text-xs text-arepo-muted">Source</div>
            <div className="font-tabular text-sm font-semibold text-arepo-ink">{market.data_source}</div>
          </div>
        </div>
      </div>

      <section className="space-y-3">
        <SectionLabel>Price history</SectionLabel>
        <div className="panel p-5">
          <PriceHistoryChart
            priceHistory={market.price_history}
            series={chartOutcomes.map((o) => ({ key: o.token_id, label: o.name }))}
          />
        </div>
      </section>

      <section className="space-y-3">
        <SectionLabel>Outcomes</SectionLabel>
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
        <SectionLabel>Signals</SectionLabel>
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

      <section className="panel space-y-1 p-5">
        <SectionLabel>Limitations</SectionLabel>
        <p className="text-sm leading-relaxed text-arepo-ink2">{market.limitations}</p>
        <p className="text-xs text-arepo-muted">
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
