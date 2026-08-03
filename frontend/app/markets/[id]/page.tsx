"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getMarket } from "@/lib/api";
import { formatCurrencyCompact, formatDate } from "@/lib/format";
import { OutcomePanel } from "@/components/OutcomePanel";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { SignalItem } from "@/components/SignalItem";
import { ModelView } from "@/components/ModelView";
import { MetricHelp } from "@/components/MetricHelp";
import { SectionTitle, Disclose } from "@/components/ui";
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

// Order the chart timeline options are offered in, and their button labels.
const RANGE_ORDER = ["1h", "6h", "24h", "7d", "all"];
const RANGE_LABEL: Record<string, string> = {
  "1h": "1H",
  "6h": "6H",
  "24h": "24H",
  "7d": "7D",
  all: "All",
};

export default function MarketDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const { mode } = useMode();

  // undefined = let the server pick its default ("all"); once the reader picks
  // a range explicitly we keep requesting that one until it stops applying.
  const [range, setRange] = useState<string | undefined>(undefined);
  const { data, loading, error, notFound } = useAsync(
    () => getMarket(id, mode, range),
    [id, mode, range]
  );

  // A range chosen for one market may not apply to another (e.g. a market
  // too young for "7d"). If the loaded market doesn't offer it, fall back to
  // the server's own default rather than keep requesting a stale range.
  useEffect(() => {
    if (data && range !== undefined && !data.market.available_ranges.includes(range)) {
      setRange(undefined);
    }
  }, [data, range]);

  // Only show the full-page skeleton on first load. A range change refetches
  // in the background with the previous market still on screen, so switching
  // ranges never flashes the whole page.
  if (loading && !data) {
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

  // Optimistic: reflect the just-clicked range immediately; once data lands
  // for a fresh market, fall back to what the server actually returned.
  const selectedRange = range ?? market.chart_range ?? "all";
  const rangeOptions = RANGE_ORDER.filter((r) => market.available_ranges.includes(r));
  const refetching = loading;

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
        <SectionTitle>Current model view</SectionTitle>
        <ModelView signals={market.signals} />
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionTitle>Price history</SectionTitle>
          {rangeOptions.length > 0 && (
            <div
              className="inline-flex rounded-control border border-arepo-border bg-arepo-surface p-0.5"
              role="tablist"
              aria-label="Chart timeline range"
            >
              {rangeOptions.map((r) => (
                <button
                  key={r}
                  type="button"
                  role="tab"
                  aria-selected={selectedRange === r}
                  onClick={() => setRange(r)}
                  disabled={refetching}
                  className={`focus-ring rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors disabled:cursor-wait ${
                    selectedRange === r
                      ? "bg-arepo-accentTint text-arepo-accentActive"
                      : "text-arepo-muted hover:text-arepo-ink"
                  }`}
                >
                  {RANGE_LABEL[r] ?? r}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className={`panel p-5 transition-opacity ${refetching ? "opacity-60" : ""}`}>
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
        <SectionTitle>Signal detail</SectionTitle>
        {market.signals.length === 0 ? (
          <EmptyState message="No signals detected for this market." />
        ) : (
          <Disclose summary={`Show the full per-signal breakdown (${market.signals.length})`}>
            <div className="space-y-3">
              {market.signals.map((s, i) => (
                <SignalItem key={`${s.kind}-${s.token_id}-${i}`} signal={s} />
              ))}
            </div>
          </Disclose>
        )}
      </section>

      <section className="space-y-2">
        <SectionTitle>Limitations</SectionTitle>
        <p className="text-[13px] text-arepo-muted">
          Probabilities shown are implied by market prices, not verified truths. See{" "}
          <Link href="/methodology" className="text-arepo-accentActive hover:text-arepo-accentHover">
            Methodology
          </Link>{" "}
          for caveats.
        </p>
        <Disclose summary="Show technical limitations for this market">
          <p className="text-[15px] leading-relaxed text-arepo-ink2">{market.limitations}</p>
        </Disclose>
      </section>
    </div>
  );
}
