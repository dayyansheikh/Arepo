/**
 * Horizontal signal-strength bar, 0 to 100 (prompt B5). Strength is stored 0-1; shown as whole
 * points. Colour is never the only cue: the numeric value is always shown and the bar carries an
 * ARIA meter role with a text value, so it is fully accessible without colour.
 */
export function StrengthBar({ value }: { value: number }) {
  const points = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="flex items-center gap-3">
      <div
        role="meter"
        aria-valuenow={points}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Signal strength ${points} out of 100`}
        className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-arepo-surface2"
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-arepo-accent"
          style={{ width: `${points}%` }}
        />
      </div>
      <span className="font-tabular text-[13px] font-semibold text-arepo-ink">
        {points}
        <span className="text-arepo-muted"> / 100</span>
      </span>
    </div>
  );
}
