import { formatCurrencyCompact, formatNumber } from "@/lib/format";

/**
 * Depth/imbalance visualisation for the market-detail order book: a
 * horizontal bar split at the midpoint, filling towards the bid side when
 * resting size leans towards buyers and towards the ask side when it leans
 * towards sellers. Best bid, best ask, spread and midpoint already appear as
 * figures next to this component; the bar exists purely to make the
 * *imbalance* between the two sides easy to read at a glance. Colour is
 * never the only cue: both sides are labelled and the reading is paired with
 * a direction arrow, so the same information survives without colour.
 */
export function OrderBookViz({
  imbalance,
  depth,
}: {
  imbalance: number | null;
  depth: number | null;
}) {
  const clamped = imbalance === null ? 0 : Math.max(-1, Math.min(1, imbalance));
  const bidWidth = clamped > 0 ? clamped * 50 : 0;
  const askWidth = clamped < 0 ? -clamped * 50 : 0;
  const direction = clamped > 0.05 ? "up" : clamped < -0.05 ? "down" : null;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 items-baseline text-[11px] font-semibold">
        <span className="text-arepo-pos">Bids</span>
        <span className="text-center font-medium text-arepo-muted">Midpoint</span>
        <span className="text-right text-arepo-neg">Asks</span>
      </div>
      <div className="relative h-4 w-full overflow-hidden rounded-full bg-arepo-surface2 ring-1 ring-inset ring-arepo-border">
        <div
          className="absolute top-0 h-full bg-arepo-neg transition-[opacity] hover:opacity-90"
          style={{ right: "50%", width: `${askWidth}%` }}
        />
        <div
          className="absolute top-0 h-full bg-arepo-pos transition-[opacity] hover:opacity-90"
          style={{ left: "50%", width: `${bidWidth}%` }}
        />
        <div className="absolute left-1/2 top-0 h-full w-[2px] -translate-x-px bg-arepo-ink" />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-[11px] font-tabular text-arepo-muted">
        <span className="inline-flex items-center gap-1">
          Imbalance{" "}
          <span className="font-semibold text-arepo-ink">
            {imbalance === null ? "–" : formatNumber(imbalance, 2)}
          </span>
          {direction === "up" && (
            <span className="text-arepo-pos" aria-label="skewed towards bids">
              &#9650;
            </span>
          )}
          {direction === "down" && (
            <span className="text-arepo-neg" aria-label="skewed towards asks">
              &#9660;
            </span>
          )}
        </span>
        <span>
          Near-mid depth{" "}
          <span className="font-semibold text-arepo-ink">{formatCurrencyCompact(depth)}</span>
        </span>
      </div>
      <p className="text-[11px] leading-snug text-arepo-muted">
        Spread and midpoint are shown above; this bar shows how resting size splits between bids
        and asks near the midpoint.
      </p>
    </div>
  );
}
