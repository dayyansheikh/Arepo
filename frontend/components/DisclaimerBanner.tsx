import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Soft research-disclaimer callout. Neutral by default; used under page titles
 * to keep the "screening heuristic, not advice" framing visible without shouting.
 */
export function DisclaimerBanner({
  children,
  learnMoreHref = "/methodology",
}: {
  children?: ReactNode;
  learnMoreHref?: string;
}) {
  return (
    <div className="flex items-start gap-2 rounded-card border border-arepo-accentBorder bg-arepo-accentTint px-4 py-3 text-[13px] leading-relaxed text-arepo-accentActive">
      <span>
        {children ??
          "Arepo surfaces statistical patterns for research only. It is not trading advice and does not predict outcomes."}{" "}
        <Link href={learnMoreHref} className="underline hover:text-arepo-accentHover">
          Read the methodology
        </Link>
        .
      </span>
    </div>
  );
}
