import type { ReactNode } from "react";
import type { OutcomeView } from "@/lib/types";
import {
  formatPercent,
  formatPrice,
  formatSignedPercent,
  formatZScore,
  formatNumber,
  formatCurrencyCompact,
} from "@/lib/format";
import { DataQualityBadge } from "./DataQualityBadge";
import { OrderBookViz } from "./OrderBookViz";
import { MetricHelp } from "./MetricHelp";
import { Disclose } from "./ui";

function Stat({ label, value }: { label: ReactNode; value: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1 text-xs text-arepo-muted">{label}</div>
      <div className="font-tabular text-sm font-semibold text-arepo-ink">{value}</div>
    </div>
  );
}

/**
 * Outcome card for the market-detail page. Progressive disclosure: the six
 * headline numbers a reader wants first (probability, bid/ask, spread,
 * midpoint, recent movement) sit in the open 3-col grid; the more technical
 * readings (z-score, volatility, order-book detail, normalised probability,
 * relative spread) sit behind "Show advanced market data" alongside the
 * order-book visualisation.
 */
export function OutcomePanel({ outcome }: { outcome: OutcomeView }) {
  return (
    <div className="space-y-4 rounded-card border border-arepo-border bg-arepo-surface p-5 shadow-arepo-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-arepo-ink">{outcome.name}</h3>
        <div className="flex items-center gap-2">
          <DataQualityBadge quality={outcome.data_quality} />
          <span className="flex items-center gap-1 text-xs text-arepo-muted">
            <MetricHelp metric="confidence" showTerm={false} />
            confidence{" "}
            {formatPercent(outcome.reliability_confidence ?? outcome.confidence, 0)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <Stat
          label={<MetricHelp metric="implied-probability" />}
          value={formatPercent(outcome.implied_probability)}
        />
        <Stat label="Best bid" value={formatPrice(outcome.best_bid)} />
        <Stat label="Best ask" value={formatPrice(outcome.best_ask)} />
        <Stat label={<MetricHelp metric="spread" />} value={formatPercent(outcome.spread, 2)} />
        <Stat label={<MetricHelp metric="midpoint" />} value={formatPrice(outcome.midpoint)} />
        <Stat label="Recent movement" value={formatSignedPercent(outcome.recent_movement)} />
      </div>

      <Disclose summary="Show advanced market data">
        <div className="grid grid-cols-3 gap-3 sm:gap-4">
          <Stat label={<MetricHelp metric="z-score" />} value={formatZScore(outcome.zscore)} />
          <Stat
            label={<MetricHelp metric="rolling-volatility" />}
            value={formatPercent(outcome.rolling_volatility, 2)}
          />
          <Stat
            label={<MetricHelp metric="order-book-imbalance" />}
            value={outcome.book_imbalance === null ? "–" : formatNumber(outcome.book_imbalance, 2)}
          />
          <Stat
            label={<MetricHelp metric="near-mid-depth" />}
            value={formatCurrencyCompact(outcome.near_mid_depth)}
          />
          <Stat label="Normalised probability" value={formatPercent(outcome.implied_probability_normalized)} />
          <Stat label="Relative spread" value={formatPercent(outcome.relative_spread, 2)} />
        </div>
        <div className="mt-4">
          <OrderBookViz imbalance={outcome.book_imbalance} depth={outcome.near_mid_depth} />
        </div>
      </Disclose>
    </div>
  );
}
