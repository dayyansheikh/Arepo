"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getFacets, getMarkets, searchMarkets } from "@/lib/api";
import type { MarketSearchResponse } from "@/lib/types";
import type { MarketCard } from "@/lib/types";
import { formatDurationSeconds, titleCase } from "@/lib/format";
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

/** Sport and competition aren't query parameters on the markets list endpoint,
 * so both filter client-side over whatever the current fetch window returned,
 * the same way signal strength, probability and time to close already do. */
function matchesSport(market: MarketCard, sport: string): boolean {
  if (!sport) return true;
  return market.sport === sport;
}

function matchesCompetition(market: MarketCard, competition: string): boolean {
  if (!competition) return true;
  return market.competition === competition;
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
  const [sport, setSport] = useState("");
  const [competition, setCompetition] = useState("");

  // Full-universe keyword search (calls the backend public-search, not just loaded markets).
  const [universeInput, setUniverseInput] = useState("");
  const [universeQuery, setUniverseQuery] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setUniverseQuery(universeInput.trim()), 350);
    return () => clearTimeout(t);
  }, [universeInput]);
  const universe = useAsync<MarketSearchResponse | null>(
    () => (universeQuery ? searchMarkets(universeQuery) : Promise.resolve(null)),
    [universeQuery]
  );
  const searching = universeQuery.length > 0;

  // Advanced, demoted: free-text search over the loaded browse set, debounced as before.
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

  // Fetched once per mode, independent of the active filters. Built dynamically
  // from real normalised market data so the dropdowns never invent options the
  // data doesn't have.
  const { data: facets } = useAsync(() => getFacets(mode), [mode]);

  const categories = useMemo(() => facets?.categories ?? [], [facets]);
  const sports = useMemo(() => facets?.sports ?? [], [facets]);
  const competitions = useMemo(() => facets?.competitions ?? [], [facets]);
  // "unknown" is a genuine backend enum value for markets with no resolved
  // status, but it isn't a status a person picks from a dropdown.
  const statuses = useMemo(
    () => (facets?.statuses ?? []).filter((s) => s.toLowerCase() !== "unknown"),
    [facets]
  );

  // A filter dropdown a person can no longer act on (its value disappeared
  // from this mode's facets, e.g. after switching data mode) resets itself
  // rather than silently filtering out every market.
  useEffect(() => {
    if (category && !categories.includes(category)) setCategory("");
  }, [category, categories]);
  useEffect(() => {
    if (status && !statuses.includes(status)) setStatus("");
  }, [status, statuses]);
  useEffect(() => {
    if (sport && !sports.includes(sport)) setSport("");
  }, [sport, sports]);
  useEffect(() => {
    if (competition && !competitions.includes(competition)) setCompetition("");
  }, [competition, competitions]);

  const markets = useMemo(() => {
    if (!data) return [];
    const now = Date.now();
    let list = data.markets.filter(
      (m) =>
        matchesSignalRange(m, signalRange) &&
        matchesProbRange(m, probRange) &&
        matchesTimeRange(m, timeRange, now) &&
        matchesSport(m, sport) &&
        matchesCompetition(m, competition)
    );
    if (uiSort === "signal") {
      list = [...list].sort(compareSignalDesc);
    } else if (uiSort === "newest") {
      list = [...list].sort(compareEndDateDesc);
    }
    return list;
  }, [data, signalRange, probRange, timeRange, sport, competition, uiSort]);

  const fetchedCount = data?.markets.length ?? 0;
  const totalMatches = data?.total ?? 0;
  const hasMore = fetchedCount < totalMatches;
  const narrowedByClientFilters = fetchedCount > 0 && markets.length < fetchedCount;

  const hasActiveFilters =
    category !== "" ||
    status !== "" ||
    signalRange !== "any" ||
    probRange !== "any" ||
    timeRange !== "any" ||
    sport !== "" ||
    competition !== "" ||
    searchInput !== "";

  function clearFilters() {
    setCategory("");
    setStatus("");
    setSignalRange("any");
    setProbRange("any");
    setTimeRange("any");
    setSport("");
    setCompetition("");
    setSearchInput("");
    setSearch("");
  }

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div>
          <h1 className="display-title text-[30px] sm:text-[34px]">Explore Markets</h1>
          <p className="mt-2 max-w-reading text-[15px] leading-relaxed text-arepo-ink2">
            Search the whole Polymarket universe by keyword, company or ticker, or browse with
            the filters below.
          </p>
        </div>

        <div className="relative max-w-xl">
          <input
            type="search"
            value={universeInput}
            onChange={(e) => setUniverseInput(e.target.value)}
            placeholder="Search all markets (e.g. Microsoft, MSFT, election)"
            aria-label="Search all markets"
            className="focus-ring w-full rounded-control border border-arepo-borderStrong bg-arepo-surface px-4 py-2.5 text-[15px] text-arepo-ink placeholder:text-arepo-muted"
          />
        </div>

        {!searching && data?.status && (
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

      {searching && (
        <section className="space-y-3">
          <SectionLabel>Search results</SectionLabel>
          {universe.loading && <CardGridSkeleton count={4} />}
          {!universe.loading && universe.error && <ErrorState message={universe.error} />}
          {!universe.loading && universe.data && (
            <>
              <p className="text-[13px] text-arepo-muted">
                {universe.data.note}
                {universe.data.expanded_terms.length > 1 && (
                  <> Also searched: {universe.data.expanded_terms.slice(1).join(", ")}.</>
                )}{" "}
                <span className="text-arepo-muted">Source: {universe.data.provenance}</span>
              </p>
              {universe.data.markets.length > 0 && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {universe.data.markets.map((m) => (
                    <MarketCardView key={m.id} market={m} />
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      )}

      {!searching && (
        <>
      <div className="panel space-y-4 p-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {categories.length > 0 && (
            <FilterField id="filter-category" label="Category">
              <select
                id="filter-category"
                className="select-arepo"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </FilterField>
          )}

          {sports.length > 0 && (
            <FilterField id="filter-sport" label="Sport">
              <select
                id="filter-sport"
                className="select-arepo"
                value={sport}
                onChange={(e) => setSport(e.target.value)}
              >
                <option value="">All sports</option>
                {sports.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </FilterField>
          )}

          {competitions.length > 0 && (
            <FilterField id="filter-competition" label="Competition">
              <select
                id="filter-competition"
                className="select-arepo"
                value={competition}
                onChange={(e) => setCompetition(e.target.value)}
              >
                <option value="">All competitions</option>
                {competitions.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </FilterField>
          )}

          <FilterField id="filter-status" label="Status">
            <select
              id="filter-status"
              className="select-arepo"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">Any</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {titleCase(s)}
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

        <div className="flex flex-wrap items-end justify-between gap-4">
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

          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="btn btn-ghost -mb-0.5"
            >
              Clear filters
            </button>
          )}
        </div>
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
          <div className="space-y-3">
            <EmptyState
              message={
                hasActiveFilters
                  ? "No markets match the current filters. Try widening the signal strength, probability or time-to-close range, or clearing the other filters."
                  : "No markets are available right now."
              }
            />
            {hasActiveFilters && (
              <div className="flex justify-center">
                <button type="button" onClick={clearFilters} className="btn btn-secondary">
                  Clear filters
                </button>
              </div>
            )}
          </div>
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
        </>
      )}
    </div>
  );
}
