"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  notFound: boolean;
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
  });
  const requestId = useRef(0);

  useEffect(() => {
    const id = ++requestId.current;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    fetcher()
      .then((data) => {
        if (requestId.current !== id) return;
        setState({ data, loading: false, error: null, notFound: false });
      })
      .catch((err: unknown) => {
        if (requestId.current !== id) return;
        const message = err instanceof Error ? err.message : "Something went wrong";
        const notFound = err instanceof ApiError && err.notFound;
        setState({ data: null, loading: false, error: message, notFound });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
