"use client";

import { useEffect, useState } from "react";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { useUrlState } from "@/lib/use-url-state";
import { getMarkets } from "@/lib/api";
import { formatDurationSeconds } from "@/lib/format";
import { ALL_CATEGORY, CATEGORY_FILTERS, type CategoryFilter } from "@/lib/categories";
import { CategoryFilterRow } from "@/components/CategoryFilterRow";
import { MarketCardView } from "@/components/MarketCardView";
import { CardGridSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { SectionLabel } from "@/components/ui";

const PAGE_SIZE = 48;

type Closing = "any" | "week" | "month" | "later";
type SignalSort = "signal_desc" | "signal_asc";

const CLOSING_OPTIONS: { value: Closing; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "week", label: "Closing this week" },
  { value: "month", label: "Closing this month" },
  { value: "later", label: "Later" },
];

const SORT_OPTIONS: { value: SignalSort; label: string }[] = [
  { value: "signal_desc", label: "Signal: high to low" },
  { value: "signal_asc", label: "Signal: low to high" },
];

export default function MarketsPage() {
  const { mode } = useMode();
  const [search, setSearch] = useUrlState("q");
  const [category, setCategory] = useUrlState("category", ALL_CATEGORY);
  const [closing, setClosing] = useUrlState("close", "any");
  const [sort, setSort] = useUrlState("sort", "signal_desc");
  const [searchInput, setSearchInput] = useState(search);
  const [limit, setLimit] = useState(PAGE_SIZE);

  useEffect(() => setSearchInput(search), [search]);
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), 350);
    return () => clearTimeout(timer);
    // URL setter identity changes after navigation; the input value is the real trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  useEffect(() => {
    setLimit(PAGE_SIZE);
  }, [search, category, closing, sort, mode]);

  useEffect(() => {
    if (!CATEGORY_FILTERS.includes(category as CategoryFilter)) setCategory(ALL_CATEGORY);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const { data, loading, error } = useAsync(
    () =>
      getMarkets({
        mode,
        search: search || undefined,
        category,
        closing: closing as Closing,
        sort: sort as SignalSort,
        limit,
        offset: 0,
      }),
    [mode, search, category, closing, sort, limit],
  );

  const markets = data?.markets ?? [];
  const hasMore = markets.length < (data?.total ?? 0);

  return (
    <div className="space-y-8" data-testid="explore-page">
      <div className="space-y-4">
        <div>
          <h1 className="display-title text-[30px] sm:text-[34px]">Explore Markets</h1>
          <p className="mt-2 max-w-reading text-[15px] leading-relaxed text-arepo-ink2">
            Search and rank the genuine market universe from Arepo&apos;s latest complete scan.
          </p>
        </div>

        <div className="max-w-xl">
          <label htmlFor="market-search" className="sr-only">Search markets</label>
          <input
            id="market-search"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search markets"
            aria-label="Search markets"
            className="focus-ring w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-4 py-2.5 text-[15px] text-arepo-ink placeholder:text-arepo-muted"
          />
        </div>

        {data?.status && (
          <p className="text-[13px] text-arepo-muted">
            Latest complete market set, updated {formatDurationSeconds(data.status.data_age_seconds)} ago.
          </p>
        )}
        <DisclaimerBanner />
      </div>

      <section className="space-y-4" data-testid="explore-controls">
        <CategoryFilterRow
          value={category}
          onChange={(next: CategoryFilter) => setCategory(next)}
        />
        <div className="flex flex-wrap gap-4">
          <label className="flex min-w-48 flex-col gap-1.5">
            <span className="text-[12px] font-medium text-arepo-muted">Time to close</span>
            <select
              className="select-arepo"
              value={closing}
              onChange={(event) => setClosing(event.target.value)}
              data-testid="closing-select"
            >
              {CLOSING_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="flex min-w-52 flex-col gap-1.5">
            <span className="text-[12px] font-medium text-arepo-muted">Sort by signal</span>
            <select
              className="select-arepo"
              value={sort}
              onChange={(event) => setSort(event.target.value)}
              data-testid="signal-sort-select"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionLabel>Results</SectionLabel>
          {!loading && !error && data && (
            <span className="font-tabular text-[13px] text-arepo-muted">
              {data.total.toLocaleString()} market{data.total === 1 ? "" : "s"}
            </span>
          )}
        </div>

        {loading && <CardGridSkeleton count={8} />}
        {!loading && error && <ErrorState message={error} />}
        {!loading && !error && data && markets.length === 0 && (
          <EmptyState message="No markets match this search, category and closing window." />
        )}
        {!loading && !error && markets.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {markets.map((market) => (
              <MarketCardView key={market.id} market={market} />
            ))}
          </div>
        )}
        {!loading && !error && hasMore && (
          <div className="flex justify-center pt-2">
            <button
              type="button"
              onClick={() => setLimit((current) => current + PAGE_SIZE)}
              className="btn btn-secondary"
            >
              Load more markets
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
