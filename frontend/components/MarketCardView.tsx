import Link from "next/link";
import type { MarketCard } from "@/lib/types";
import { formatCurrencyCompact, formatPercent, formatSignedPercent } from "@/lib/format";
import { StrengthMeter } from "./StrengthMeter";

export function MarketCardView({ market }: { market: MarketCard }) {
  return (
    <Link
      href={`/markets/${encodeURIComponent(market.id)}`}
      className="focus-ring panel flex flex-col gap-3 p-4 transition-colors hover:border-astro-brass/50"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug line-clamp-2">{market.question}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
        {market.category && (
          <span className="rounded-full border border-astro-light-border dark:border-astro-border px-2 py-0.5">
            {market.category}
          </span>
        )}
        <span className="uppercase tracking-wide">{market.status}</span>
      </div>

      <div className="mt-auto grid grid-cols-2 gap-x-3 gap-y-2 font-mono text-xs font-tabular">
        <div>
          <div className="text-muted-fg">Top outcome</div>
          <div className="text-sm">
            {market.top_outcome ?? "—"} {formatPercent(market.top_probability)}
          </div>
        </div>
        <div>
          <div className="text-muted-fg">Volume</div>
          <div className="text-sm">{formatCurrencyCompact(market.volume)}</div>
        </div>
        <div>
          <div className="text-muted-fg">Spread</div>
          <div className="text-sm">{formatPercent(market.spread, 2)}</div>
        </div>
        <div>
          <div className="text-muted-fg">Movement</div>
          <div className="text-sm">{formatSignedPercent(market.abs_movement, 1)}</div>
        </div>
      </div>

      {market.signal_strength !== null && (
        <div className="border-t border-astro-light-border dark:border-astro-border pt-2">
          <div className="text-xs text-muted-fg mb-1">Signal strength</div>
          <StrengthMeter strength={market.signal_strength} />
        </div>
      )}
    </Link>
  );
}
