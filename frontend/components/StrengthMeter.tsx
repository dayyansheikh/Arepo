/**
 * Horizontal meter for a 0..1 signal strength value, with an optional up/down
 * direction arrow. The fill is Arepo red (the signal colour); direction, when
 * given, tints the arrow only and is always paired with a glyph so colour is
 * never the sole cue. Purely presentational.
 */
export function StrengthMeter({
  strength,
  direction,
  className = "",
}: {
  strength: number;
  direction?: "up" | "down" | null;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(1, strength));
  const pct = Math.round(clamped * 100);

  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      role="meter"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Signal strength"
      title="Signal-intensity score (0–100), not a probability of being correct."
    >
      <div className="h-1.5 flex-1 min-w-16 overflow-hidden rounded-full bg-arepo-surface2">
        <div
          className="h-full rounded-full bg-arepo-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-tabular text-[13px] font-semibold text-arepo-accentActive tabular-nums min-w-[1.5rem] text-right">
        {pct}
      </span>
      {direction === "up" && (
        <span className="text-arepo-pos text-xs" aria-label="upward">
          &#9650;
        </span>
      )}
      {direction === "down" && (
        <span className="text-arepo-neg text-xs" aria-label="downward">
          &#9660;
        </span>
      )}
    </div>
  );
}
