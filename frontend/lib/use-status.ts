"use client";

import { useEffect, useState } from "react";
import { ApiError, getStatus } from "./api";
import type { DataMode, DataStatus } from "./types";

/**
 * Shared, self-healing status poller (final runtime acceptance §7).
 *
 * The status chip and the degradation banner both need /api/status, and React StrictMode double-
 * mounts effects in development, so the naive one-poller-per-consumer approach produced up to four
 * independent request streams. When the backend was down, each stream retried at a fixed 30s cadence
 * and every failed fetch logged ERR_CONNECTION_REFUSED — flooding the console.
 *
 * This module keeps ONE poll loop per mode, shared by every subscriber:
 *   - a single in-flight request at a time (an AbortController cancels it on the last unsubscribe or
 *     when the mode changes, so navigating away never leaves a dangling request or rejection),
 *   - exponential backoff on failure (30s → capped at 5min) so a downed backend is polled sparsely
 *     rather than hammered, resetting to the base cadence the moment a request succeeds,
 *   - one shared { status, error } snapshot, so there is exactly one "API disconnected" state,
 *   - automatic recovery: the loop keeps running (slowly) while down and heals on the next success,
 *   - polling pauses while the tab is hidden and resumes (with an immediate poll) when it returns.
 *
 * All rejections are caught; aborts are ignored. Nothing here can produce an unhandled rejection.
 */
const BASE_MS = 30_000;
const MAX_BACKOFF_MS = 300_000;

interface Snapshot {
  status: DataStatus | null;
  error: string | null;
}

interface Store {
  snapshot: Snapshot;
  listeners: Set<() => void>;
  controller: AbortController | null;
  timer: ReturnType<typeof setTimeout> | null;
  failures: number;
  visibilityBound: boolean;
}

const stores = new Map<DataMode, Store>();

function getStore(mode: DataMode): Store {
  let s = stores.get(mode);
  if (!s) {
    s = {
      snapshot: { status: null, error: null },
      listeners: new Set(),
      controller: null,
      timer: null,
      failures: 0,
      visibilityBound: false,
    };
    stores.set(mode, s);
  }
  return s;
}

function emit(store: Store) {
  for (const l of store.listeners) l();
}

function setSnapshot(store: Store, next: Snapshot) {
  store.snapshot = next;
  emit(store);
}

function clearTimer(store: Store) {
  if (store.timer) {
    clearTimeout(store.timer);
    store.timer = null;
  }
}

function schedule(store: Store, mode: DataMode, delay: number) {
  clearTimer(store);
  if (store.listeners.size === 0) return; // no one is listening; go idle
  store.timer = setTimeout(() => void poll(store, mode), delay);
}

async function poll(store: Store, mode: DataMode) {
  if (store.listeners.size === 0) return;
  if (typeof document !== "undefined" && document.visibilityState === "hidden") {
    // Don't poll a hidden tab; visibilitychange will resume with an immediate poll.
    return;
  }
  store.controller?.abort();
  const controller = new AbortController();
  store.controller = controller;
  try {
    const result = await getStatus(mode, controller.signal);
    if (controller.signal.aborted) return;
    store.failures = 0;
    setSnapshot(store, { status: result, error: null });
    schedule(store, mode, BASE_MS);
  } catch (err) {
    if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) {
      return; // unmount/navigation — stay silent
    }
    store.failures += 1;
    const message =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Unable to load status";
    // Keep the last known status visible but surface the disconnected error alongside it.
    setSnapshot(store, { status: store.snapshot.status, error: message });
    const backoff = Math.min(MAX_BACKOFF_MS, BASE_MS * 2 ** (store.failures - 1));
    schedule(store, mode, backoff);
  }
}

function bindVisibility(store: Store, mode: DataMode) {
  if (store.visibilityBound || typeof document === "undefined") return;
  store.visibilityBound = true;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && store.listeners.size > 0) {
      void poll(store, mode); // resume immediately when the tab returns
    }
  });
}

function subscribe(mode: DataMode, listener: () => void): () => void {
  const store = getStore(mode);
  const firstListener = store.listeners.size === 0;
  store.listeners.add(listener);
  bindVisibility(store, mode);
  if (firstListener) {
    // Kick the loop off immediately for the first subscriber.
    void poll(store, mode);
  }
  return () => {
    store.listeners.delete(listener);
    if (store.listeners.size === 0) {
      clearTimer(store);
      store.controller?.abort();
      store.controller = null;
    }
  };
}

/** Polls /api/status for the given mode so the status chip and degradation banner stay fresh, using
 * a single shared, backoff-bounded, abortable poll loop (see module docstring). */
export function useStatus(mode: DataMode): { status: DataStatus | null; error: string | null } {
  const [snapshot, setLocal] = useState<Snapshot>(() => getStore(mode).snapshot);

  useEffect(() => {
    const store = getStore(mode);
    setLocal(store.snapshot);
    const unsubscribe = subscribe(mode, () => setLocal(store.snapshot));
    return unsubscribe;
  }, [mode]);

  return snapshot;
}
