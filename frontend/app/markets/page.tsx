"use client";

import { useEffect, useState } from "react";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getMarkets } from "@/lib/api";
import { MarketCardView } from "@/components/MarketCardView";
import { CardGridSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";

const PAGE_SIZE = 20;

const SORT_OPTIONS: { value: "volume" | "volume_24hr" | "liquidity" | "end_date"; label: string }[] = [
  { value: "volume", label: "Volume" },
  { value: "volume_24hr", label: "24h volume" },
  { value: "liquidity", label: "Liquidity" },
  { value: "end_date", label: "End date" },
];

export default function MarketsPage() {
  const { mode } = useMode();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<(typeof SORT_OPTIONS)[number]["value"]>("volume");
  const [offset, setOffset] = useState(0);

  // Debounce the free-text search so we don't refetch on every keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setOffset(0);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const { data, loading, error } = useAsync(
    () =>
      getMarkets({
        mode,
        search: search || undefined,
        category: category || undefined,
        status: status || undefined,
        sort,
        limit: PAGE_SIZE,
        offset,
      }),
    [mode, search, category, status, sort, offset]
  );

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Markets</h1>
        <p className="mt-1 text-sm text-muted-fg">
          Browse and filter markets by category, status, and sort order.
        </p>
      </div>

      <form
        className="panel flex flex-wrap items-end gap-4 p-4"
        onSubmit={(e) => e.preventDefault()}
        role="search"
      >
        <div className="flex flex-col gap-1">
          <label htmlFor="search" className="text-xs font-medium text-muted-fg">
            Search
          </label>
          <input
            id="search"
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search markets…"
            className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border bg-transparent px-3 py-1.5 text-sm min-w-[200px]"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="category" className="text-xs font-medium text-muted-fg">
            Category
          </label>
          <input
            id="category"
            type="text"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setOffset(0);
            }}
            placeholder="Any"
            className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border bg-transparent px-3 py-1.5 text-sm w-32"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="status" className="text-xs font-medium text-muted-fg">
            Status
          </label>
          <input
            id="status"
            type="text"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setOffset(0);
            }}
            placeholder="Any"
            className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border bg-transparent px-3 py-1.5 text-sm w-32"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="sort" className="text-xs font-medium text-muted-fg">
            Sort by
          </label>
          <select
            id="sort"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as typeof sort);
              setOffset(0);
            }}
            className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border bg-transparent px-3 py-1.5 text-sm"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </form>

      {loading && <CardGridSkeleton count={8} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && data.markets.length === 0 && (
        <EmptyState message="No markets match these filters." />
      )}

      {!loading && data && data.markets.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.markets.map((m) => (
              <MarketCardView key={m.id} market={m} />
            ))}
          </div>

          <nav className="flex items-center justify-between text-sm" aria-label="Pagination">
            <span className="text-muted-fg font-mono font-tabular">
              {total.toLocaleString()} markets — page {page} of {pageCount}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border px-3 py-1.5 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border px-3 py-1.5 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </nav>
        </>
      )}
    </div>
  );
}
