import { Popover } from "@/components/Popover";

/**
 * An accessible chip that reveals a plain-English explanation on hover, focus or tap (the shared
 * Popover primitive opens on all three and closes on Escape/blur). Used for the human-readable
 * Priority, Confidence and Evidence chips so a new user can understand each term without leaving
 * the page.
 */
export function InfoChip({
  label,
  desc,
  tone = "neutral",
}: {
  label: string;
  desc: string;
  tone?: "neutral" | "high" | "med" | "low";
}) {
  const toneClass =
    tone === "high"
      ? "bg-arepo-accentTint text-arepo-accentActive"
      : tone === "low"
        ? "bg-arepo-surface2 text-arepo-muted"
        : "bg-arepo-surface2 text-arepo-ink2";
  return (
    <Popover
      label={`${label}. ${desc}`}
      triggerClassName={`focus-ring rounded-full px-2 py-0.5 text-[12px] font-medium ${toneClass}`}
      trigger={<span data-testid="info-chip">{label}</span>}
    >
      <p className="max-w-[260px] text-[12px] leading-relaxed text-arepo-ink2">{desc}</p>
    </Popover>
  );
}
