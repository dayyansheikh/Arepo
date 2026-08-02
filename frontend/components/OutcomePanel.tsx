import type { OutcomeView } from "@/lib/types";
import { formatPercent, formatPrice, formatSignedPercent, formatZScore, formatCurrencyCompact } from "@/lib/format";
import { DataQualityBadge } from "./DataQualityBadge";
import { OrderBookViz } from "./OrderBookViz";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted-fg">{label}</div>
      <div className="text-sm font-mono font-tabular">{value}</div>
    </div>
  );
}

export function OutcomePanel({ outcome }: { outcome: OutcomeView }) {
  return (
    <div className="panel p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">{outcome.name}</h3>
        <div className="flex items-center gap-2">
          <DataQualityBadge quality={outcome.data_quality} />
          <span className="text-xs text-muted-fg font-mono font-tabular">
            confidence {formatPercent(outcome.confidence, 0)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Implied probability" value={formatPercent(outcome.implied_probability)} />
        <Stat label="Normalized" value={formatPercent(outcome.implied_probability_normalized)} />
        <Stat label="Best bid" value={formatPrice(outcome.best_bid)} />
        <Stat label="Best ask" value={formatPrice(outcome.best_ask)} />
        <Stat label="Midpoint" value={formatPrice(outcome.midpoint)} />
        <Stat label="Spread" value={formatPercent(outcome.spread, 2)} />
        <Stat label="Relative spread" value={formatPercent(outcome.relative_spread, 2)} />
        <Stat label="Rolling volatility" value={formatPercent(outcome.rolling_volatility, 2)} />
        <Stat label="1h movement" value={formatSignedPercent(outcome.movement_1h)} />
        <Stat label="Z-score" value={formatZScore(outcome.zscore)} />
        <Stat label="Volume" value={formatCurrencyCompact(outcome.volume)} />
        <Stat
          label="Signal strength"
          value={outcome.signal_strength === null ? "—" : formatPercent(outcome.signal_strength, 0)}
        />
      </div>

      <OrderBookViz imbalance={outcome.book_imbalance} depth={outcome.near_mid_depth} />
    </div>
  );
}
