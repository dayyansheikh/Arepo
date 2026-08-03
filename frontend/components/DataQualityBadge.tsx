import { MetricHelp } from "./MetricHelp";

const TONE_CLASS: Record<string, string> = {
  good: "bg-arepo-pos/12 text-arepo-pos",
  limited: "bg-arepo-warn/12 text-arepo-warnText",
  poor: "bg-arepo-neg/12 text-arepo-neg",
};

const LABEL: Record<string, string> = {
  good: "Good",
  limited: "Limited",
  poor: "Poor",
};

function capitalise(value: string): string {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}

/**
 * Data-coverage pill, e.g. "Data coverage: Limited". The word always carries
 * the meaning (colour is never the only cue), and both the badge text and the
 * attached tooltip spell out "Data coverage: <band>" so the label is
 * self-explanatory without relying on colour.
 */
export function DataQualityBadge({ quality }: { quality: string }) {
  const label = LABEL[quality] ?? capitalise(quality);
  const tone = TONE_CLASS[quality] ?? "bg-arepo-surface2 text-arepo-muted";
  return (
    <span className="inline-flex items-center gap-1">
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${tone}`}
      >
        {`Data coverage: ${label}`}
      </span>
      <MetricHelp metric="data-coverage" showTerm={false} />
    </span>
  );
}
