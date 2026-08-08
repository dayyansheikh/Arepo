"use client";

import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import { useUrlState } from "@/lib/use-url-state";
import { getOpportunities, type ScanSignalRow } from "@/lib/api";
import {
  cardTrajectoryLabel,
  consecutivePhrase,
  friendlyEvidence,
  priorityBand,
  strengthPhrase,
  timeToCloseLabel,
  trajectoryTone,
} from "@/lib/signal-lab";
import { directionLabel, DIRECTION_TONE_CLASS } from "@/lib/directional";
import { ListSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { StrengthBar } from "@/components/StrengthBar";
import { InfoChip } from "@/components/InfoChip";
import { PageHeader, SectionTitle } from "@/components/ui";

// Public closing-window filters (prompt B1). Values map to the API's cumulative windows.
const WINDOWS = [
  { id: "all", label: "All within 30 days" },
  { id: "within_6h", label: "Next 6 hours" },
  { id: "within_24h", label: "Later today" },
  { id: "within_7d", label: "This week" },
  { id: "within_30d", label: "This month" },
] as const;

export default function OpportunitiesPage() {
  const [window, setWindow] = useUrlState("window", "all");
  const { data, loading, error } = useAsync(() => getOpportunities(window, 20), [window]);

  return (
    <div className="space-y-8" data-testid="opportunities-page">
      <div className="space-y-3">
        <PageHeader
          title="Opportunities"
          lead="Arepo's public shortlist: the strongest directional signals across active markets closing within 30 days. The full universe is analysed; this shows the top 20."
        />
        <DisclaimerBanner />
      </div>

      <section className="flex flex-wrap items-end justify-between gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-arepo-ink2">Closing window</span>
          <select
            data-testid="window-select"
            className="select-arepo w-64"
            value={window}
            onChange={(e) => setWindow(e.target.value)}
            aria-label="Closing window"
          >
            {WINDOWS.map((w) => (
              <option key={w.id} value={w.id}>
                {w.label}
              </option>
            ))}
          </select>
        </label>
        {data?.freshness && <FreshnessBadge freshness={data.freshness} />}
      </section>

      {loading && <ListSkeleton rows={6} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && !data.has_scan && (
        <EmptyState message="No complete market scan has been recorded yet. The scheduled backend refresh performs the scan; the browser only reads stored results." />
      )}
      {!loading && data && data.has_scan && (
        <>
          {/* Delayed-refresh fallback copy (prompt B1): the latest complete scan is always used. */}
          {data.freshness && data.freshness.state !== "fresh" && (
            <p className="text-[13px] text-arepo-warnText" data-testid="delayed-notice">
              Live refresh is delayed. Showing the most recent complete update ({data.freshness.updated_phrase.toLowerCase()}).
            </p>
          )}
          <section className="space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <SectionTitle>{data.window_label}</SectionTitle>
              <span className="text-[13px] text-arepo-muted" data-testid="denominator">
                {data.denominator}
              </span>
            </div>
            {data.rows.length === 0 ? (
              <EmptyState message="No directional signals in this closing window right now. Try a wider window." />
            ) : (
              <div className="space-y-3" data-testid="opportunity-list">
                {data.rows.map((r, i) => (
                  <OpportunityCard key={`${r.market_id}-${r.token_id}`} row={r} rank={i + 1} />
                ))}
              </div>
            )}
          </section>
          <p className="max-w-reading text-[12px] leading-relaxed text-arepo-muted">
            Opportunities is the public shortlist. Signal Lab shows every directional signal in the
            complete eligible universe. Strength measures how unusual the market behaviour is; it is
            not a probability, and a stronger signal does not mean the outcome is more likely.
          </p>
        </>
      )}
    </div>
  );
}

function OpportunityCard({ row, rank }: { row: ScanSignalRow; rank: number }) {
  const t = row.trajectory;
  const tone = trajectoryTone(t.label);
  const trajLabel = cardTrajectoryLabel(t.label);
  const toneClass =
    tone.tone === "up"
      ? "text-arepo-pos"
      : tone.tone === "down"
        ? "text-arepo-neg"
        : tone.tone === "flat"
          ? "text-arepo-ink2"
          : "text-arepo-muted";
  const consec = consecutivePhrase(t);
  return (
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-5" data-testid="opportunity-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-tabular text-[13px] text-arepo-muted">#{rank}</span>
            <Link
              href={`/markets/${encodeURIComponent(row.market_id)}`}
              className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
            >
              {row.market_question}
            </Link>
          </div>
          <p className="mt-0.5 text-[13px] text-arepo-muted">
            Closes {timeToCloseLabel(row.time_remaining_hours)}
          </p>
        </div>
        <div className="text-right text-[13px] text-arepo-ink2">
          {/* Same directional-call vocabulary as every other surface. */}
          {(() => {
            const d = directionLabel(row.direction, row.outcome_name);
            return (
              <span
                className={`font-medium ${DIRECTION_TONE_CLASS[d.tone]}`}
                title="Arepo's directional call: which way this outcome has been repricing. Not a probability, not good or bad."
              >
                <span aria-hidden="true">{d.glyph}</span> {d.text}
              </span>
            );
          })()}
        </div>
      </div>

      <div className="mt-3">
        <StrengthBar value={row.strength} />
      </div>

      <p className="mt-2 text-[14px] text-arepo-ink2" data-testid="strength-phrase">
        {strengthPhrase(row.strength, t)}.{" "}
        {trajLabel && (
          <>
            <span className={`font-medium ${toneClass}`}>
              <span aria-hidden="true">{tone.glyph} </span>
              {trajLabel}
            </span>
            .{" "}
          </>
        )}
        {consec ? `${consec}.` : ""}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <InfoChip
          label={`Priority: ${priorityBand(row.research_priority).label}`}
          desc={priorityBand(row.research_priority).desc}
          tone={priorityBand(row.research_priority).tone}
        />
        {row.evidence_families.map((key) => {
          const e = friendlyEvidence(key);
          return <InfoChip key={key} label={e.label} desc={e.desc} />;
        })}
        <Link
          href={`/markets/${encodeURIComponent(row.market_id)}`}
          className="focus-ring text-[12px] underline hover:text-arepo-ink"
        >
          Market detail
        </Link>
      </div>
    </div>
  );
}
