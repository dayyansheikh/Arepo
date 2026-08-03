import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Neutral research-information panel. Calm grey, never warning or error styling
 * (spec section 6): Arepo red is reserved for selected controls, active
 * navigation and genuine signal emphasis, not for general information. Used under
 * page titles to keep the "research tool, not advice" framing visible.
 */
export function DisclaimerBanner({
  children,
  learnMoreHref = "/methodology",
}: {
  children?: ReactNode;
  learnMoreHref?: string;
}) {
  return (
    <div className="flex items-start gap-2.5 rounded-card border border-arepo-border bg-arepo-surface2 px-4 py-3 text-[14px] leading-relaxed text-arepo-ink2">
      <svg
        aria-hidden="true"
        viewBox="0 0 20 20"
        className="mt-0.5 h-4 w-4 flex-none text-arepo-muted"
        fill="currentColor"
      >
        <path
          fillRule="evenodd"
          d="M10 2a8 8 0 100 16 8 8 0 000-16zm.75 6.75a.75.75 0 00-1.5 0v4.5a.75.75 0 001.5 0v-4.5zM10 6.75a.9.9 0 100-1.8.9.9 0 000 1.8z"
          clipRule="evenodd"
        />
      </svg>
      <span>
        {children ??
          "Arepo is a read-only research tool. It surfaces statistical patterns in public prediction markets for investigation. It is not trading advice and does not predict outcomes."}{" "}
        <Link
          href={learnMoreHref}
          className="font-medium text-arepo-ink underline decoration-arepo-borderStrong underline-offset-2 hover:decoration-arepo-ink"
        >
          Read the methodology
        </Link>
        .
      </span>
    </div>
  );
}
