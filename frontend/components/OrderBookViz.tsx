import { formatCurrencyCompact, formatNumber } from "@/lib/format";

/**
 * Small depth/imbalance visualization: a horizontal bar split at the midpoint.
 * A positive imbalance fills the bid side, a negative one the ask side. The two
 * sides use distinct neutral hues and are always labelled, so colour is never
 * the only cue. `imbalance` is expected in [-1, 1].
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

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[11px] text-arepo-muted">
        <span>Ask side</span>
        <span>Bid side</span>
      </div>
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-arepo-surface2">
        <div className="absolute left-1/2 top-0 h-full w-px bg-arepo-borderStrong" />
        <div
          className="absolute top-0 h-full bg-arepo-series2"
          style={{ right: "50%", width: `${askWidth}%` }}
        />
        <div
          className="absolute top-0 h-full bg-arepo-pos"
          style={{ left: "50%", width: `${bidWidth}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-[11px] font-tabular text-arepo-muted">
        <span>imbalance {imbalance === null ? "–" : formatNumber(imbalance, 2)}</span>
        <span>near-mid depth {formatCurrencyCompact(depth)}</span>
      </div>
    </div>
  );
}
