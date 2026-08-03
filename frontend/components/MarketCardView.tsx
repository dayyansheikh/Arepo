import Link from "next/link";
import type { MarketCard } from "@/lib/types";
import { formatPercent, formatSignedPercent, titleCase } from "@/lib/format";
import { StrengthMeter } from "./StrengthMeter";
import { Badge, StatusDot } from "./ui";

/**
 * Reduced-density market card. Per the brief it shows only question, category
 * and status, the leading outcome and probability, recent movement, and signal
 * strength. Secondary statistics (volume, spread, order-book detail) live on the
 * market detail page.
 */
export function MarketCardView({ market }: { market: MarketCard }) {
  const active = market.status?.toLowerCase() === "active";
  return (
    <Link
      href={`/markets/${encodeURIComponent(market.id)}`}
      className="focus-ring group flex flex-col gap-3.5 rounded-card border border-arepo-border bg-arepo-surface p-5 shadow-arepo-sm transition-all hover:border-arepo-accentBorder hover:shadow-arepo-hover"
    >
      <div className="flex flex-wrap items-center gap-2">
        {market.category && (
          <Badge tone="neutral">{market.category}</Badge>
        )}
        <StatusDot
          label={titleCase(market.status)}
          tone={active ? "active" : "neutral"}
        />
      </div>

      {(market.sport || market.competition) && (
        <div className="-mt-2 text-[11px] text-arepo-muted">
          {[market.sport, market.competition].filter(Boolean).join(" · ")}
        </div>
      )}

      <h3 className="min-h-[2.75rem] text-[15px] font-semibold leading-snug text-arepo-ink line-clamp-2">
        {market.question}
      </h3>

      <div className="flex gap-6">
        <div>
          <div className="mb-0.5 text-[11px] text-arepo-muted">Leading outcome</div>
          <div className="font-tabular text-sm font-semibold text-arepo-ink">
            {market.top_outcome ?? "—"}
            {market.top_probability !== null && (
              <span className="text-arepo-muted">
                {" · "}
                {formatPercent(market.top_probability)}
              </span>
            )}
          </div>
        </div>
        <div>
          <div className="mb-0.5 text-[11px] text-arepo-muted">Movement</div>
          <div className="font-tabular text-sm font-semibold text-arepo-ink">
            {formatSignedPercent(market.abs_movement, 1)}
          </div>
        </div>
      </div>

      {market.signal_strength !== null && (
        <div className="border-t border-arepo-border pt-3">
          <div className="mb-1.5 text-[11px] text-arepo-muted">Signal strength</div>
          <StrengthMeter strength={market.signal_strength} />
        </div>
      )}

      <span
        aria-hidden="true"
        className="text-[13px] font-medium text-arepo-muted transition-colors group-hover:text-arepo-accent"
      >
        View details &rarr;
      </span>
    </Link>
  );
}
