"use client";

import { useMode } from "@/lib/mode-context";
import { useStatus } from "@/lib/use-status";
import { formatDurationSeconds } from "@/lib/format";

const STATE_COLOR: Record<string, string> = {
  ok: "bg-astro-positive",
  healthy: "bg-astro-positive",
  degraded: "bg-astro-brass",
  down: "bg-astro-negative",
  error: "bg-astro-negative",
};

function dotColor(state: string | undefined): string {
  if (!state) return "bg-astro-muted";
  return STATE_COLOR[state.toLowerCase()] ?? "bg-astro-muted";
}

const MODE_LABEL: Record<string, string> = {
  live: "LIVE",
  cached: "CACHED",
  replay: "REPLAY",
};

export function StatusChip() {
  const { mode } = useMode();
  const { status, error } = useStatus(mode);

  return (
    <div
      className="flex items-center gap-3 rounded-instrument border border-astro-light-border dark:border-astro-border px-3 py-1.5 text-xs font-mono font-tabular"
      title="Data source status"
    >
      <span
        className={`inline-flex items-center rounded px-1.5 py-0.5 font-semibold tracking-wide ${
          mode === "live"
            ? "bg-astro-positive/15 text-astro-positive"
            : "bg-astro-brass/15 text-astro-brass"
        }`}
      >
        {MODE_LABEL[mode] ?? mode.toUpperCase()}
      </span>
      {status ? (
        <>
          <span className="flex items-center gap-1 text-muted-fg">
            <span className={`h-1.5 w-1.5 rounded-full ${dotColor(status.rest.state)}`} aria-hidden="true" />
            REST
          </span>
          <span className="flex items-center gap-1 text-muted-fg">
            <span className={`h-1.5 w-1.5 rounded-full ${dotColor(status.websocket.state)}`} aria-hidden="true" />
            WS
          </span>
          <span className="text-muted-fg">
            age {formatDurationSeconds(status.data_age_seconds)}
          </span>
        </>
      ) : error ? (
        <span className="text-astro-negative">status unavailable</span>
      ) : (
        <span className="text-muted-fg">checking…</span>
      )}
    </div>
  );
}
