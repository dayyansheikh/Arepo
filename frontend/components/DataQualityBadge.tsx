const STYLES: Record<string, string> = {
  good: "bg-astro-positive/15 text-astro-positive border-astro-positive/30",
  limited: "bg-astro-brass/15 text-astro-brass border-astro-brass/30",
  poor: "bg-astro-negative/15 text-astro-negative border-astro-negative/30",
};

export function DataQualityBadge({ quality }: { quality: string }) {
  const style = STYLES[quality] ?? "bg-astro-muted/15 text-muted-fg border-astro-border";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-mono uppercase tracking-wide ${style}`}
      title={`Data quality: ${quality}`}
    >
      {quality}
    </span>
  );
}
