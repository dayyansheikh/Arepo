"use client";

import { useMode } from "@/lib/mode-context";
import { useStatus } from "@/lib/use-status";
import { formatDurationSeconds } from "@/lib/format";

type Tone = "good" | "warn" | "bad" | "neutral" | "muted";

const TONE_DOT: Record<Tone, string> = {
  good: "bg-arepo-pos",
  warn: "bg-arepo-warn",
  bad: "bg-arepo-neg",
  neutral: "bg-arepo-muted",
  muted: "bg-arepo-border",
};

/** Map a raw source state to a plain-English label + tone (never colour alone). */
function connectivity(state: string | undefined): { label: string; tone: Tone } {
  switch ((state ?? "").toLowerCase()) {
    case "ok":
    case "healthy":
    case "connected":
      return { label: "Connected", tone: "good" };
    case "connecting":
    case "updating":
      return { label: "Updating", tone: "warn" };
    case "degraded":
    case "delayed":
      return { label: "Delayed", tone: "warn" };
    case "down":
    case "error":
    case "disconnected":
      return { label: "Offline", tone: "bad" };
    default:
      return { label: "Unknown", tone: "neutral" };
  }
}

/** One labelled connectivity item: dot (tone) + name + state word. */
function Item({
  name,
  state,
  tone,
  title,
}: {
  name: string;
  state: string;
  tone: Tone;
  title: string;
}) {
  return (
    <span
      className="flex items-center gap-1.5"
      title={title}
      aria-label={`${name}: ${state}`}
    >
      <span className={`h-1.5 w-1.5 flex-none rounded-full ${TONE_DOT[tone]}`} aria-hidden="true" />
      <span className="text-arepo-muted" aria-hidden="true">
        {name}
      </span>
      <span className="font-medium text-arepo-ink2" aria-hidden="true">
        {state}
      </span>
    </span>
  );
}

/**
 * Plain-English data-connectivity readout for the active mode. Shows whether Arepo
 * can retrieve current market data (API), whether real-time updates are connected
 * (Live feed), and how long ago data last refreshed (Updated). Live feed is only
 * meaningful in Live mode; in Cached and Replay it reads "Not available".
 */
export function StatusChip() {
  const { mode } = useMode();
  const { status, error } = useStatus(mode);

  const api = connectivity(status?.rest.state);
  const feed = connectivity(status?.websocket.state);
  const liveApplies = mode === "live";

  return (
    <div
      className="hidden items-center gap-3.5 rounded-control border border-arepo-border bg-arepo-surface px-3 py-1.5 text-[12px] font-tabular md:flex"
      role="group"
      aria-label="Data connectivity"
    >
      {status ? (
        <>
          <Item
            name="API"
            state={api.label}
            tone={api.tone}
            title="API: whether Arepo can retrieve current market data."
          />
          <Item
            name="Live feed"
            state={liveApplies ? feed.label : "Not available"}
            tone={liveApplies ? feed.tone : "muted"}
            title={
              liveApplies
                ? "Live feed: whether real-time updates are connected."
                : "Live feed: real-time updates apply only in Live mode."
            }
          />
          <span
            className="flex items-center gap-1.5"
            title="Updated: how long ago market data last refreshed."
            aria-label={
              status.data_age_seconds != null
                ? `Updated ${formatDurationSeconds(status.data_age_seconds)} ago`
                : "Update time not available"
            }
          >
            <span className="text-arepo-muted" aria-hidden="true">
              Updated
            </span>
            <span className="font-medium text-arepo-ink2" aria-hidden="true">
              {status.data_age_seconds != null
                ? `${formatDurationSeconds(status.data_age_seconds)} ago`
                : "n/a"}
            </span>
          </span>
        </>
      ) : error ? (
        <span className="text-arepo-muted">Status unavailable</span>
      ) : (
        <span className="text-arepo-muted">Checking…</span>
      )}
    </div>
  );
}
