"use client";

import { useEffect, useState } from "react";
import { getStatus } from "./api";
import type { DataMode, DataStatus } from "./types";

const POLL_MS = 30_000;

/** Polls /api/status for the given mode so the status chip stays fresh. */
export function useStatus(mode: DataMode): { status: DataStatus | null; error: string | null } {
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const result = await getStatus(mode);
        if (!cancelled) {
          setStatus(result);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load status");
        }
      }
      if (!cancelled) {
        timer = setTimeout(poll, POLL_MS);
      }
    }

    setStatus(null);
    void poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [mode]);

  return { status, error };
}
