"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getMarkets } from "@/lib/api";
import type { MarketCard } from "@/lib/types";
import { formatDurationSeconds } from "@/lib/format";
import { MarketCardView } from "@/components/MarketCardView";
import { CardGridSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { Disclose, SectionLabel } from "@/components/ui";

const MODE_LABEL: Record<string, string> = {
  live: "Live",
  cached: "Cached",
  replay: "Replay",
};

// How many markets to pull from the API per request, and the step by which
// "Load more" grows that window. Deliberately larger than a typical page size
// because the signal-strength, probability and time-to-close filters below
// run client-side over whatever this window returns.
const FETCH_SIZE = 48;
const FETCH_STEP = 48;

// A broad, unfiltered sample used only to discover which categories exist so
// the Category dropdown never invents options the data doesn't have.
const CATEGORY_SAMPLE_SIZE = 300;

type ApiSort = "volume" | "volume_24hr" | "liquidity" | "end_date";
type UiSort = "signal" | "volume" | "ending" | "newest";

const SORT_OPTIONS: { value: UiSort; label: string }[] = [
  { value: "signal", label: "Signal strength" },
  { value: "volume", label: "Volume" },
  { value: "ending", label: "Ending soonest" },
  { value: "newest", label: "Newest" },
];

// The backend only sorts by volume, volume_24hr, liquidity or end_date; there
// is no server-side "by signal strength" or "by creation date" ordering. For
// "Signal strength" and "Newest" we fetch in a sane default order and then
// resort client-side (see compareSignalDesc / compareEndDateDesc below).
const API_SORT_FOR_UI: Record<UiSort, ApiSort> = {
  signal: "volume",
  volume: "volume",
  ending: "end_date",
  newest: "volume",
};

type SignalRange = "any" | "high" | "medium" | "low";
const SIGNAL_OPTIONS: { value: SignalRange; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "high", label: "High (70+)" },
  { value: "medium", label: "Medium (40–69)" },
  { value: "low", label: "Low (<40)" },
];

type ProbRange = "any" | "under25" | "mid" | "over75";
const PROB_OPTIONS: { value: ProbRange; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "under25", label: "Under 25%" },
  { value: "mid", label: "25% to 75%" },
  { value: "over75", label: "Over 75%" },
];

type TimeRange = "any" | "week" | "month" | "later";
const TIME_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "week", label: "Closing this week" },
  { value: "month", label: "Closing this month" },
  { value: "later", label: "Later" },
];

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Any" },
  { value: "active", label: "Active" },
  { value: "closed", label: "Closed" },
  { value: "resolved", label: "Resolved" },
  { value: "archived", label: "Archived" },
];

/** Signal strength is stored 0..1 (StrengthMeter/MarketCardView read it that
 * way directly); the 70 / 40 breakpoints from the brief are on the 0-100
 * display scale, so compare against 0.70 / 0.40 here. */
function matchesSignalRange(market: MarketCard, range: SignalRange): boolean {
  if (range === "any") return true;
  if (market.signal_strength === null) return false;
  if (range === "high") return market.signal_strength >= 0.7;
  if (range === "medium") return market.signal_strength >= 0.4 && market.signal_strength < 0.7;
  return market.signal_strength < 0.4;
}

function matchesProbRange(market: MarketCard, range: ProbRange): boolean {
  if (range === "any") return true;
  if (market.top_probability === null) return false;
  if (range === "under25") return market.top_probability < 0.25;
  if (range === "mid") return market.top_probability >= 0.25 && market.top_probability <= 0.75;
  return market.top_probability > 0.75;
}

/** Buckets are relative to now and mutually exclusive. A market whose close
 * date has already passed, or which has no end date at all, matches "Any"
 * only: we don't guess at a close date the data doesn't give us. */
function matchesTimeRange(market: MarketCard, range: TimeRange, nowMs: number): boolean {
  if (range === "any") return true;
  if (!market.end_date) return false;
  const end = new Date(market.end_date).getTime();
  if (Number.isNaN(end)) return false;
  const diffDays = (end - nowMs) / 86_400_000;
  if (diffDays < 0) return false;
  if (range === "week") return diffDays <= 7;
  if (range === "month") return diffDays > 7 && diffDays <= 30;
  return diffDays > 30;
}

function compareSignalDesc(a: MarketCard, b: MarketCard): number {
  if (a.signal_strength === null && b.signal_strength === null) return 0;
  if (a.signal_strength === null) return 1;
  if (b.signal_strength === null) return -1;
  return b.signal_strength - a.signal_strength;
}

/** Approximates "Newest" by furthest-out close date, since MarketCard carries
 * no creation timestamp to sort by. Markets with no end date sort last. */
function compareEndDateDesc(a: MarketCard, b: MarketCard): number {
  const at = a.end_date ? new Date(a.end_date).getTime() : null;
  const bt = b.end_date ? new Date(b.end_date).getTime() : null;
  if (at === null && bt === null) return 0;
  if (at === null) return 1;
  if (bt === null) return -1;
  return bt - at;
}

function FilterField({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[12px] font-medium text-arepo-muted">
        {label}
      </label>
      {children}
    </div>
  );
}

export default function MarketsPage() {
  const { mode } = useMode();

  // Guided filters resolved by the API.
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [uiSort, setUiSort] = useState<UiSort>("volume");

  // Guided filters resolved client-side over the fetched window.
  const [signalRange, setSignalRange] = useState<SignalRange>("any");
  const [probRange, setProbRange] = useState<ProbRange>("any");
  const [timeRange, setTimeRange] = useState<TimeRange>("any");

  // Advanced, demoted: free-text search, debounced as before.
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [limit, setLimit] = useState(FETCH_SIZE);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setLimit(FETCH_SIZE);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Any server-side filter change starts the fetch window over.
  useEffect(() => {
    setLimit(FETCH_SIZE);
  }, [category, status, uiSort]);

  const apiSort = API_SORT_FOR_UI[uiSort];

  const { data, loading, error } = useAsync(
    () =>
      getMarkets({
        mode,
        search: search || undefined,
        category: category || undefined,
        status: status || undefined,
        sort: apiSort,
        limit,
        offset: 0,
      }),
    [mode, search, category, status, apiSort, limit]
  );

  // Fetched once per mode, independent of the active filters, purely to build
  // the Category dropdown from categories that actually occur in the data.
  const { data: categorySample } = useAsync(
    () => getMarkets({ mode, sort: "volume", limit: CATEGORY_SAMPLE_SIZE, offset: 0 }),
    [mode]
  );

  const categories = useMemo(() => {
    if (!categorySample) return [];
    const set = new Set<string>();
    for (const m of categorySample.markets) {
      if (m.category) set.add(m.category);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [categorySample]);

  const markets = useMemo(() => {
    if (!data) return [];
    const now = Date.now();
    let list = data.markets.filter(
      (m) =>
        matchesSignalRange(m, signalRange) &&
        matchesProbRange(m, probRange) &&
        matchesTimeRange(m, timeRange, now)
    );
    if (uiSort === "signal") {
      list = [...list].sort(compareSignalDesc);
    } else if (uiSort === "newest") {
      list = [...list].sort(compareEndDateDesc);
    }
    return list;
  }, [data, signalRange, probRange, timeRange, uiSort]);

  const fetchedCount = data?.markets.length ?? 0;
  const totalMatches = data?.total ?? 0;
  const hasMore = fetchedCount < totalMatches;
  const narrowedByClientFilters = fetchedCount > 0 && markets.length < fetchedCount;

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div>
          <h1 className="text-[30px] font-semibold tracking-[-0.01em] text-arepo-ink">Markets</h1>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-muted">
            Use the dropdowns to find markets by category, status, signal strength, leading
            probability or time to close.
          </p>
        </div>
        {data?.status && (
          <p className="text-[13px] text-arepo-muted">
            Showing{" "}
            <span className="font-medium text-arepo-ink">
              {MODE_LABEL[data.status.mode] ?? data.status.mode}
            </span>{" "}
            data, updated {formatDurationSeconds(data.status.data_age_seconds)} ago.
          </p>
        )}
        <DisclaimerBanner />
      </div>

      <div className="panel space-y-4 p-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <FilterField id="filter-category" label="Category">
            <select
              id="filter-category"
              className="select-arepo"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">Any</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField id="filter-status" label="Status">
            <select
              id="filter-status"
              className="select-arepo"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField id="filter-signal" label="Signal strength">
            <select
              id="filter-signal"
              className="select-arepo"
              value={signalRange}
              onChange={(e) => setSignalRange(e.target.value as SignalRange)}
            >
              {SIGNAL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField id="filter-probability" label="Probability">
            <select
              id="filter-probability"
              className="select-arepo"
              value={probRange}
              onChange={(e) => setProbRange(e.target.value as ProbRange)}
            >
              {PROB_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField id="filter-time" label="Time to close">
            <select
              id="filter-time"
              className="select-arepo"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
            >
              {TIME_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField id="filter-sort" label="Sort by">
            <select
              id="filter-sort"
              className="select-arepo"
              value={uiSort}
              onChange={(e) => setUiSort(e.target.value as UiSort)}
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FilterField>
        </div>

        <Disclose summary="Advanced: search by keyword">
          <div className="flex max-w-xs flex-col gap-1.5">
            <label htmlFor="market-search" className="text-[12px] font-medium text-arepo-muted">
              Search
            </label>
            <input
              id="market-search"
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by question or keyword…"
              className="focus-ring rounded-control border border-arepo-borderStrong bg-arepo-surface px-3 py-2 text-sm text-arepo-ink placeholder:text-arepo-muted"
            />
          </div>
        </Disclose>
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionLabel>Results</SectionLabel>
          {!loading && !error && (
            <span className="font-tabular text-[13px] text-arepo-muted">
              {markets.length.toLocaleString()} market{markets.length === 1 ? "" : "s"}
              {narrowedByClientFilters && ` of ${fetchedCount.toLocaleString()} loaded`}
            </span>
          )}
        </div>

        {loading && <CardGridSkeleton count={8} />}
        {!loading && error && <ErrorState message={error} />}
        {!loading && !error && data && markets.length === 0 && (
          <EmptyState message="No markets match these filters. Try widening the signal strength, probability or time-to-close range, or clearing the category and status filters." />
        )}

        {!loading && !error && markets.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {markets.map((m) => (
              <MarketCardView key={m.id} market={m} />
            ))}
          </div>
        )}

        {!loading && !error && hasMore && (
          <div className="flex justify-center pt-2">
            <button
              type="button"
              onClick={() => setLimit((l) => l + FETCH_STEP)}
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
