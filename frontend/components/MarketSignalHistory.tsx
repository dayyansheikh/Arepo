"use client";

import { useAsync } from "@/lib/use-async";
import { getMarketSignalHistory } from "@/lib/api";
import { StrengthBar } from "@/components/StrengthBar";
import { trajectoryTone } from "@/lib/signal-lab";
import { SectionTitle } from "@/components/ui";

/**
 * Market-detail signal-history section (final-completion prompt B8). Renders the stored strength,
 * direction, rank and Research Priority history across complete scans plus the current trajectory,
 * with an accessible table. Strength history is a score history, never a probability history.
 */
function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB");
}

function ttc(hours: number | null): string {
  if (hours == null) return "n/a";
  if (hours < 48) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

export function MarketSignalHistory({ marketId }: { marketId: string }) {
  const { data, loading } = useAsync(() => getMarketSignalHistory(marketId), [marketId]);

  if (loading) {
    return (
      <section className="space-y-3" data-testid="market-signal-history">
        <SectionTitle>Signal history</SectionTitle>
        <p className="text-[13px] text-arepo-muted">Loading signal history…</p>
      </section>
    );
  }
  if (!data || !data.has_history) {
    return (
      <section className="space-y-3" data-testid="market-signal-history">
        <SectionTitle>Signal history</SectionTitle>
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
          No stored signal history for this market yet. History accumulates as the scheduled complete
          scans record this market over time; the browser never scans.
        </p>
      </section>
    );
  }

  const t = data.trajectory;
  const tone = t ? trajectoryTone(t.label) : null;
  const latest = data.snapshots[data.snapshots.length - 1];

  return (
    <section className="space-y-4" data-testid="market-signal-history">
      <SectionTitle>Signal history</SectionTitle>

      {t && (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px]">
          <span className={`inline-flex items-center gap-1.5 font-semibold ${
            tone?.tone === "up" ? "text-arepo-pos"
              : tone?.tone === "down" ? "text-arepo-neg"
                : tone?.tone === "flat" ? "text-arepo-ink2" : "text-arepo-muted"
          }`}>
            <span aria-hidden="true">{tone?.glyph}</span>
            {t.label}
          </span>
          {t.strength_change_prev != null && (
            <span className="text-arepo-ink2">
              {t.strength_change_prev > 0 ? "+" : ""}
              {Math.round(t.strength_change_prev * 100)} points since the previous scan
            </span>
          )}
          {t.consecutive_same_direction >= 2 && (
            <span className="text-arepo-muted">
              Direction unchanged for {t.consecutive_same_direction} consecutive scans
            </span>
          )}
        </div>
      )}

      {latest && (
        <div className="max-w-md">
          <div className="mb-1 text-[12px] text-arepo-muted">Current strength</div>
          <StrengthBar value={latest.strength} />
        </div>
      )}

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-arepo-muted">
        {t?.first_detected && <span>First detected {fmtTime(t.first_detected)}</span>}
        {t?.last_updated && <span>Last updated {fmtTime(t.last_updated)}</span>}
        <span>{data.snapshots.length} recorded scans</span>
        {t?.rank_change != null && t.rank_change !== 0 && (
          <span>Rank moved {t.rank_change > 0 ? "up" : "down"} {Math.abs(t.rank_change)}</span>
        )}
        {t?.research_priority_change != null && t.research_priority_change !== 0 && (
          <span>
            Research Priority {t.research_priority_change > 0 ? "+" : ""}
            {t.research_priority_change}
          </span>
        )}
      </div>

      {/* Accessible table alternative for the strength/direction/rank history. */}
      <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-[13px]" data-testid="history-table">
            <caption className="sr-only">
              Signal history for this market across complete scans: time, strength (0 to 100),
              direction, bucket rank, Research Priority and time remaining.
            </caption>
            <thead>
              <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
                <th scope="col" className="px-3 py-2.5 font-semibold">Scan time</th>
                <th scope="col" className="px-3 py-2.5 font-semibold">Strength</th>
                <th scope="col" className="px-3 py-2.5 font-semibold">Direction</th>
                <th scope="col" className="px-3 py-2.5 font-semibold">Bucket rank</th>
                <th scope="col" className="px-3 py-2.5 font-semibold">Research Priority</th>
                <th scope="col" className="px-3 py-2.5 font-semibold">Left</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-arepo-border font-tabular">
              {[...data.snapshots].reverse().map((s) => (
                <tr key={`${s.scan_id}`}>
                  <td className="px-3 py-2 font-sans">{fmtTime(s.captured_at)}</td>
                  <td className="px-3 py-2">{Math.round(s.strength * 100)}</td>
                  <td className="px-3 py-2 font-sans">
                    {s.direction === "up" ? "Up" : s.direction === "down" ? "Down" : "n/a"}
                  </td>
                  <td className="px-3 py-2">{s.rank_in_bucket ?? "-"}</td>
                  <td className="px-3 py-2">{s.research_priority}</td>
                  <td className="px-3 py-2">{ttc(s.time_remaining_hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="max-w-reading text-[12px] leading-relaxed text-arepo-muted">
        Strength history is a history of the stored anomaly score, not of probability. A rising score
        does not mean the outcome became more likely.
      </p>
    </section>
  );
}
