/**
 * Horizontal meter for a 0..1 signal strength value, with an optional
 * up/down direction arrow. Purely presentational.
 */
export function StrengthMeter({
  strength,
  direction,
}: {
  strength: number;
  direction?: "up" | "down" | null;
}) {
  const clamped = Math.max(0, Math.min(1, strength));
  const pct = Math.round(clamped * 100);
  const color =
    direction === "up"
      ? "bg-astro-positive"
      : direction === "down"
        ? "bg-astro-negative"
        : "bg-astro-brass";

  return (
    <div className="flex items-center gap-2" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-astro-border/60">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-muted-fg font-tabular">{pct}</span>
      {direction === "up" && <span className="text-astro-positive text-xs">&#9650;</span>}
      {direction === "down" && <span className="text-astro-negative text-xs">&#9660;</span>}
    </div>
  );
}
