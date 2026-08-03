import { Badge } from "./ui";

const TONE: Record<string, "good" | "limited" | "poor" | "neutral"> = {
  good: "good",
  limited: "limited",
  poor: "poor",
};

/** Data-quality pill (GOOD / LIMITED / POOR). The word carries the meaning. */
export function DataQualityBadge({ quality }: { quality: string }) {
  return <Badge tone={TONE[quality] ?? "neutral"}>{quality}</Badge>;
}
