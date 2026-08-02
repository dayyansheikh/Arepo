"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getMarket } from "@/lib/api";
import { formatCurrencyCompact, formatDate } from "@/lib/format";
import { OutcomePanel } from "@/components/OutcomePanel";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { SignalItem } from "@/components/SignalItem";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { SkeletonBlock } from "@/components/Skeletons";

export default function MarketDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const { mode } = useMode();
  const { data, loading, error, notFound } = useAsync(() => getMarket(id, mode), [id, mode]);
  const [visibleOutcomes, setVisibleOutcomes] = useState<string[]>([]);

  useEffect(() => {
    if (data) {
      setVisibleOutcomes(data.market.outcomes.map((o) => o.name));
    }
  }, [data]);

  if (loading) {
    return (
      <div className="space-y-6">
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

  function toggleOutcome(name: string) {
    setVisibleOutcomes((current) =>
      current.includes(name) ? current.filter((n) => n !== name) : [...current, name]
    );
  }

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
          {market.category && (
            <span className="rounded-full border border-astro-light-border dark:border-astro-border px-2 py-0.5">
              {market.category}
            </span>
          )}
          <span className="uppercase tracking-wide">{market.status}</span>
          {market.tags.map((tag) => (
            <span key={tag} className="rounded-full border border-astro-light-border dark:border-astro-border px-2 py-0.5">
              {tag}
            </span>
          ))}
        </div>
        <h1 className="text-2xl font-semibold leading-snug">{market.question}</h1>
        {market.description && <p className="text-sm text-muted-fg">{market.description}</p>}
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs font-mono font-tabular text-muted-fg">
          <span>Volume {formatCurrencyCompact(market.volume)}</span>
          <span>24h volume {formatCurrencyCompact(market.volume_24hr)}</span>
          <span>Liquidity {formatCurrencyCompact(market.liquidity)}</span>
          <span>Ends {formatDate(market.end_date)}</span>
          <span>Source: {market.data_source}</span>
        </div>
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">
            Price history
          </h2>
          <div className="flex flex-wrap gap-2">
            {market.outcomes.map((o) => (
              <button
                key={o.name}
                type="button"
                onClick={() => toggleOutcome(o.name)}
                aria-pressed={visibleOutcomes.includes(o.name)}
                className={`focus-ring rounded-full border px-2.5 py-1 text-xs transition-colors ${
                  visibleOutcomes.includes(o.name)
                    ? "border-astro-brass text-astro-brass"
                    : "border-astro-light-border dark:border-astro-border text-muted-fg"
                }`}
              >
                {o.name}
              </button>
            ))}
          </div>
        </div>
        <div className="panel p-4">
          <PriceHistoryChart
            priceHistory={market.price_history}
            series={market.outcomes
              .filter((o) => visibleOutcomes.includes(o.name))
              .map((o) => ({ key: o.token_id, label: o.name }))}
          />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">Outcomes</h2>
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
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">Signals</h2>
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

      <section className="panel p-4 space-y-1">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">Limitations</h2>
        <p className="text-sm text-muted-fg">{market.limitations}</p>
        <p className="text-xs text-muted-fg">
          Probabilities shown are implied by market prices, not verified truths — see{" "}
          <a href="/methodology" className="text-astro-brass hover:underline">
            Methodology
          </a>{" "}
          for caveats.
        </p>
      </section>
    </div>
  );
}
