"use client";

import { useMode } from "@/lib/mode-context";
import { useStatus } from "@/lib/use-status";
import { formatDurationSeconds } from "@/lib/format";

const STATE_COLOR: Record<string, string> = {
  ok: "bg-arepo-pos",
  healthy: "bg-arepo-pos",
  degraded: "bg-[#B8791F]",
  down: "bg-arepo-neg",
  error: "bg-arepo-neg",
};

function dotColor(state: string | undefined): string {
  if (!state) return "bg-arepo-muted";
  return STATE_COLOR[state.toLowerCase()] ?? "bg-arepo-muted";
}

/**
 * Compact REST / WebSocket / data-age readout. The data mode itself lives in the
 * ModeSelector; this reports source health for the active mode.
 */
export function StatusChip() {
  const { mode } = useMode();
  const { status, error } = useStatus(mode);

  return (
    <div
      className="hidden items-center gap-3 rounded-control border border-arepo-border px-3 py-1.5 text-xs text-arepo-muted font-tabular sm:flex"
      title="Data source health for the current mode"
    >
      {status ? (
        <>
          <span className="flex items-center gap-1">
            <span
              className={`h-1.5 w-1.5 rounded-full ${dotColor(status.rest.state)}`}
              aria-hidden="true"
            />
            REST
          </span>
          <span className="flex items-center gap-1">
            <span
              className={`h-1.5 w-1.5 rounded-full ${dotColor(status.websocket.state)}`}
              aria-hidden="true"
            />
            WS
          </span>
          <span>age {formatDurationSeconds(status.data_age_seconds)}</span>
        </>
      ) : error ? (
        <span className="text-arepo-neg">status unavailable</span>
      ) : (
        <span>checking…</span>
      )}
    </div>
  );
}
