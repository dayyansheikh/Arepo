"use client";

import { useMode } from "@/lib/mode-context";
import { useStatus } from "@/lib/use-status";
import { formatDurationSeconds } from "@/lib/format";

type Tone = "good" | "warn" | "bad";

const TONE_DOT: Record<Tone, string> = {
  good: "bg-arepo-pos",
  warn: "bg-arepo-warn",
  bad: "bg-arepo-neg",
};

/**
 * Map the data-source (CLOB REST / cache / replay) state to a truthful API label.
 * Returns null when the state is not yet known, so the chip shows a neutral
 * "Checking" placeholder rather than a bare "Unknown".
 */
function apiState(state: string | undefined): { label: string; tone: Tone } | null {
  switch ((state ?? "").toLowerCase()) {
    case "ok":
    case "healthy":
    case "connected":
      return { label: "Connected", tone: "good" };
    case "connecting":
    case "updating":
    case "degraded":
    case "delayed":
      return { label: "Delayed", tone: "warn" };
    case "down":
    case "error":
    case "disconnected":
      return { label: "Offline", tone: "bad" };
    default:
      return null; // unknown -> do not surface a confusing "Unknown"
  }
}

/**
 * Compact, truthful data-connectivity readout for the active mode: whether Arepo can
 * retrieve current market data (API), and how long ago it last refreshed (only when
 * that age is actually known). The real-time WebSocket feed is not part of this
 * read-only deployment, so it is deliberately not shown rather than reported as
 * "Unknown". Green is used only when the API is genuinely connected.
 */
export function StatusChip() {
  const { mode } = useMode();
  const { status, error } = useStatus(mode);

  const api = apiState(status?.rest.state);
  const age = status?.data_age_seconds ?? null;

  // A live connection error takes precedence over any last-known status: show ONE clear, unmissable
  // "API disconnected" state rather than a stale green chip (final runtime acceptance §7).
  if (error) {
    return (
      <div
        className="hidden items-center gap-1.5 rounded-control border border-arepo-neg/40 bg-arepo-neg/10 px-3 py-1.5 text-[12px] font-medium text-arepo-neg md:flex"
        role="status"
        data-testid="api-disconnected"
        aria-label="API disconnected"
        title="Arepo cannot reach its API right now. It keeps retrying with backoff and reconnects automatically."
      >
        <span className={`h-1.5 w-1.5 flex-none rounded-full ${TONE_DOT.bad}`} aria-hidden="true" />
        API disconnected
      </div>
    );
  }

  if (!status || !api) {
    return (
      <div className="hidden items-center rounded-control border border-arepo-border bg-arepo-surface px-3 py-1.5 text-[12px] text-arepo-muted md:flex">
        Checking…
      </div>
    );
  }

  return (
    <div
      className="hidden items-center gap-2 rounded-control border border-arepo-border bg-arepo-surface px-3 py-1.5 text-[12px] font-tabular md:flex"
      role="group"
      data-testid="api-connected"
      aria-label="Data connectivity"
      title={
        age != null
          ? `API ${api.label}; market data last refreshed ${formatDurationSeconds(age)} ago.`
          : `API ${api.label}: whether Arepo can retrieve current market data.`
      }
    >
      <span className="flex items-center gap-1.5" aria-label={`API ${api.label}`}>
        <span
          className={`h-1.5 w-1.5 flex-none rounded-full ${TONE_DOT[api.tone]}`}
          aria-hidden="true"
        />
        <span className="text-arepo-muted" aria-hidden="true">
          API
        </span>
        <span className="font-medium text-arepo-ink2" aria-hidden="true">
          {api.label}
        </span>
      </span>
      {age != null && (
        <span
          className="flex items-center gap-1.5 border-l border-arepo-border pl-2 text-arepo-muted"
          aria-label={`Updated ${formatDurationSeconds(age)} ago`}
        >
          <span aria-hidden="true">Updated {formatDurationSeconds(age)} ago</span>
        </span>
      )}
    </div>
  );
}
