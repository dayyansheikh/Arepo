"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMode } from "@/lib/mode-context";
import type { DataMode } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { getMarket } from "@/lib/api";
import { formatCurrencyCompact, formatDate } from "@/lib/format";
import { OutcomePanel } from "@/components/OutcomePanel";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { SignalItem } from "@/components/SignalItem";
import { ModelView } from "@/components/ModelView";
import { MarketSignalHistory } from "@/components/MarketSignalHistory";
import { MetricHelp } from "@/components/MetricHelp";
import { SectionTitle, Disclose } from "@/components/ui";
import { EmptyState } from "@/components/ErrorState";
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

const VALID_MODES: DataMode[] = ["live", "cached", "replay"];

/**
 * Compact market-route error (spec §3.13, §4). Never a large blank page: a bordered card that
 * states the searched market and requested mode and offers a way forward (open in Live, retry,
 * back to Explore). The footer follows it naturally because the card is short and the shell no
 * longer forces a tall min-height.
 */
function MarketRouteError({
  id,
  mode,
  kind,
  message,
  onRetry,
}: {
  id: string;
  mode: DataMode;
  kind: "not-found" | "error";
  message?: string;
  onRetry: () => void;
}) {
  const router = useRouter();
  return (
    <div className="mx-auto max-w-lg rounded-card border border-arepo-border bg-arepo-surface p-6 text-center shadow-arepo-sm">
      <p className="font-display text-lg font-semibold text-arepo-ink">
        {kind === "not-found" ? "We could not open this market" : "This market failed to load"}
      </p>
      <p className="mt-2 text-[14px] leading-relaxed text-arepo-muted">
        {kind === "not-found" ? (
          <>
            Arepo could not resolve market <span className="font-tabular">{id}</span> in the{" "}
            {SOURCE_LABEL[mode] ?? mode} view. It may not exist, or it may live in another data
            source.
          </>
        ) : (
          (message ?? "The request failed.")
        )}
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
        {mode !== "live" && (
          <button
            type="button"
            onClick={() => router.replace(`/markets/${encodeURIComponent(id)}?mode=live`)}
            className="focus-ring rounded-md bg-arepo-accent px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-arepo-accentHover"
          >
            Open in Live
          </button>
        )}
        <button
          type="button"
          onClick={onRetry}
          className="focus-ring rounded-md border border-arepo-border px-3 py-1.5 text-[13px] font-medium text-arepo-ink hover:bg-arepo-surface2"
        >
          Retry
        </button>
        <Link
          href="/markets"
          className="focus-ring rounded-md border border-arepo-border px-3 py-1.5 text-[13px] font-medium text-arepo-ink hover:bg-arepo-surface2"
        >
          Return to search
        </Link>
      </div>
    </div>
  );
}

export default function MarketDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const { mode: globalMode } = useMode();
  const searchParams = useSearchParams();

  // An explicit ?mode= in the URL (set by search results, saved markets and alerts) is the
  // market's own source context and wins over the globally-selected interface mode (spec §3), so
  // a live search result opens the live market even while Replay is selected. The backend also
  // resolves canonically, so opening still works if no mode is given.
  const urlMode = searchParams.get("mode");
  const mode: DataMode = VALID_MODES.includes(urlMode as DataMode)
    ? (urlMode as DataMode)
    : globalMode;

  // undefined = let the server pick its default ("all"); once the reader picks
  // a range explicitly we keep requesting that one until it stops applying.
  const [range, setRange] = useState<string | undefined>(undefined);
  const [reloadKey, setReloadKey] = useState(0);
  const retry = () => setReloadKey((k) => k + 1);
  const { data, loading, error, notFound } = useAsync(
    () => getMarket(id, mode, range),
    [id, mode, range, reloadKey]
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
    return <MarketRouteError id={id} mode={mode} kind="not-found" onRetry={retry} />;
  }

  if (error) {
    return <MarketRouteError id={id} mode={mode} kind="error" message={error} onRetry={retry} />;
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

      <MarketSignalHistory marketId={market.id} />

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
