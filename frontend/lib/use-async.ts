"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  notFound: boolean;
  /** True while the API appears to be waking up (cold start) rather than genuinely failing. */
  coldStart: boolean;
}

/**
 * Runs an async fetcher whenever `deps` change, tracking loading/error state
 * and guarding against out-of-order responses (a slow earlier request
 * resolving after a newer one has already landed).
 */
export function useAsync<T>(fetcher: () => Promise<T>, deps: React.DependencyList): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null,
    notFound: false,
    coldStart: false,
  });
  const requestId = useRef(0);

  useEffect(() => {
    const id = ++requestId.current;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    // Cold-start retries ride out a free-host (Render Free) wake-up, ~30–60s. Bounded so a genuine
    // extended outage eventually shows a real error rather than "connecting" forever (spec §13).
    let coldRetries = 0;
    const MAX_COLD_RETRIES = 10; // ~50s at 5s spacing
    setState((prev) => ({ ...prev, loading: true, error: null }));

    const run = () => {
      fetcher()
        .then((data) => {
          if (requestId.current !== id) return;
          setState({ data, loading: false, error: null, notFound: false, coldStart: false });
        })
        .catch((err: unknown) => {
          if (requestId.current !== id) return;
          const message = err instanceof Error ? err.message : "Something went wrong";
          const notFound = err instanceof ApiError && err.notFound;
          const coldStart = err instanceof ApiError && err.coldStart;
          if (coldStart && coldRetries < MAX_COLD_RETRIES) {
            // Restrained "connecting" state; ErrorState renders this as a calm cold-start message.
            coldRetries += 1;
            setState({
              data: null,
              loading: false,
              error: "Connecting to Arepo data… The server may be waking up.",
              notFound: false,
              coldStart: true,
            });
            retryTimer = setTimeout(run, 5000);
            return;
          }
          setState({ data: null, loading: false, error: message, notFound, coldStart: false });
        });
    };
    run();

    return () => {
      if (retryTimer) clearTimeout(retryTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
