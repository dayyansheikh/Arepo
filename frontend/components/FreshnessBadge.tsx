import type { Freshness } from "@/lib/api";

/**
 * Freshness indicator (prompt B6). Normally shows a quiet "Updated N minutes ago"; only when the
 * refresh is delayed or out of date does it warn. It describes how recently a COMPLETE market update
 * arrived, never signal quality, and never colour alone (the words carry the meaning + a tooltip).
 */
export function FreshnessBadge({ freshness }: { freshness: Freshness }) {
  const label =
    freshness.state === "fresh"
      ? freshness.updated_phrase
      : freshness.state === "refresh_delayed"
        ? `Refresh delayed · ${freshness.updated_phrase.toLowerCase()}`
        : `Out of date · ${freshness.updated_phrase.toLowerCase()}`;
  const cls =
    freshness.state === "fresh"
      ? "text-arepo-muted"
      : freshness.state === "refresh_delayed"
        ? "text-arepo-warnText"
        : "text-arepo-neg";
  return (
    <span
      data-testid="freshness"
      data-state={freshness.state}
      title={freshness.tooltip}
      className={`inline-flex items-center gap-1.5 text-[13px] ${cls}`}
    >
      <span aria-hidden="true">{freshness.state === "fresh" ? "●" : "▲"}</span>
      {label}
    </span>
  );
}
