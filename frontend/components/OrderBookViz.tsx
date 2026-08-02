import { formatCurrencyCompact, formatNumber } from "@/lib/format";

/**
 * Small depth/imbalance visualization: a horizontal bar split at center,
 * with the bid side (positive imbalance) filled teal and the ask side
 * (negative imbalance) filled coral. book_imbalance is expected in [-1, 1].
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
      <div className="flex items-center justify-between text-xs text-muted-fg font-mono font-tabular">
        <span>Ask side</span>
        <span>Bid side</span>
      </div>
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-astro-light-border/60 dark:bg-astro-border/60">
        <div className="absolute left-1/2 top-0 h-full w-px bg-astro-light-border dark:bg-astro-border" />
        <div
          className="absolute top-0 h-full bg-astro-negative"
          style={{ right: "50%", width: `${askWidth}%` }}
        />
        <div
          className="absolute top-0 h-full bg-astro-positive"
          style={{ left: "50%", width: `${bidWidth}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs font-mono font-tabular text-muted-fg">
        <span>imbalance {imbalance === null ? "—" : formatNumber(imbalance, 2)}</span>
        <span>near-mid depth {formatCurrencyCompact(depth)}</span>
      </div>
    </div>
  );
}
