"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { actionForResult, loadLabDashboard, type LabLoadResult } from "./api";
import { fixtureAllowed } from "./fixture-guard";
import type { LabDashboardResponse } from "./types";

export const POLL_MS = 60_000;
/** Focus + visibilitychange often fire together; ignore a refetch request inside this window. */
const MIN_REFETCH_GAP_MS = 5_000;

export interface LabDashboardState {
  data: LabDashboardResponse | null;
  /** Browser time (ms) when `data` arrived; used with server_time for freshness. */
  fetchedAt: number;
  loading: boolean;
  /** Message for the latest failed refresh (data, if any, is kept). */
  error: string | null;
  notFound: boolean;
  /** Set when a security-key unlock is needed (403 hardware_key_required); polling pauses. */
  locked: { keys: number } | null;
  isFixture: boolean;
}

/**
 * Polls GET /api/lab/dashboard every 60 s while the tab is visible, refetches on focus / when the
 * tab becomes visible, redirects to sign-in on 401 and reports 404 so the page can render the
 * standard not-found UI. In development only, `?fixture=1` swaps in a labelled fixture.
 */
export function useLabDashboard(): LabDashboardState & { refresh: () => void } {
  const router = useRouter();
  const [state, setState] = useState<LabDashboardState>({
    data: null,
    fetchedAt: 0,
    loading: true,
    error: null,
    notFound: false,
    locked: null,
    isFixture: false,
  });
  const lockedRef = useRef(false);
  const inFlight = useRef<AbortController | null>(null);
  const lastStart = useRef(0);
  const fixtureMode = useRef(false);
  const stopped = useRef(false);

  const load = useCallback(
    async (force = false) => {
      if (fixtureMode.current || stopped.current || (lockedRef.current && !force)) return;
      const now = Date.now();
      if (!force && now - lastStart.current < MIN_REFETCH_GAP_MS) return;
      lastStart.current = now;
      inFlight.current?.abort();
      const ctrl = new AbortController();
      inFlight.current = ctrl;
      let result: LabLoadResult;
      try {
        result = await loadLabDashboard(undefined, ctrl.signal);
      } catch {
        return; // aborted by a newer request or unmount
      }
      if (ctrl.signal.aborted) return;
      const action = actionForResult(result);
      if (action.type === "redirect") {
        stopped.current = true;
        router.replace(action.to);
        return;
      }
      if (action.type === "locked") {
        lockedRef.current = true;
        setState((s) => ({ ...s, loading: false, locked: { keys: action.keys } }));
        return;
      }
      lockedRef.current = false;
      if (action.type === "not_found") {
        stopped.current = true;
        setState((s) => ({ ...s, loading: false, notFound: true }));
        return;
      }
      if (action.type === "data") {
        setState({
          data: action.data,
          fetchedAt: Date.now(),
          loading: false,
          error: null,
          notFound: false,
          locked: null,
          isFixture: false,
        });
        return;
      }
      setState((s) => ({ ...s, loading: false, error: action.message }));
    },
    [router],
  );

  useEffect(() => {
    // Dev-only fixture. The literal NODE_ENV check lets the production build drop this branch and
    // the fixture chunk entirely; fixtureAllowed() refuses production as a second guard.
    if (process.env.NODE_ENV !== "production") {
      if (fixtureAllowed(process.env.NODE_ENV, window.location.search)) {
        fixtureMode.current = true;
        void import("./fixture").then((m) => {
          setState({
            data: m.buildLabFixture(Date.now()),
            fetchedAt: Date.now(),
            loading: false,
            error: null,
            notFound: false,
            locked: null,
            isFixture: true,
          });
        });
        return;
      }
    }

    void load(true);
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    const onFocus = () => void load();
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onFocus);
      inFlight.current?.abort();
    };
  }, [load]);

  const refresh = useCallback(() => void load(true), [load]);
  return { ...state, refresh };
}
