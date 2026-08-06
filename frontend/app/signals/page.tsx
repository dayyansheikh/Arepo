"use client";

import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import { useUrlState } from "@/lib/use-url-state";
import { getScanStatus, getScanSignals, type ScanSignalRow } from "@/lib/api";
import {
  BUCKET_OPTIONS,
  SCOPE_OPTIONS,
  consecutivePhrase,
  eligibleHeadline,
  strengthPhrase,
  timeToCloseLabel,
  trajectoryTone,
  type Bucket,
  type Scope,
} from "@/lib/signal-lab";
import { ListSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PageHeader, SectionTitle, Disclose, Badge } from "@/components/ui";

export default function SignalLabPage() {
  // Signals come FIRST (prompt section 10): the explanation is a collapsed disclosure below.
  const [bucket, setBucket] = useUrlState("bucket", "closing_1_7d");
  const [scope, setScope] = useUrlState("scope", "public");

  const statusState = useAsync(() => getScanStatus(), []);
  const signalsState = useAsync(
    () => getScanSignals(bucket, scope, scope === "public" ? 10 : 500),
    [bucket, scope],
  );
  const status = statusState.data;
  const signals = signalsState.data;

  return (
    <div className="space-y-8" data-testid="signal-lab">
      <div className="space-y-3">
        <PageHeader
          title="Signal Lab"
          lead="Arepo discovers every active market, analyses all those closing within 30 days, and ranks them. The public list shows the top ten; the full universe is analysed and preserved."
        />
        <DisclaimerBanner />
      </div>

      {/* Scan status strip: raw discovered, eligible analysed, directional found, last scan. */}
      <section
        className="rounded-card border border-arepo-border bg-arepo-surface2 p-4"
        data-testid="scan-status"
      >
        {statusState.loading && <ListSkeleton rows={2} />}
        {!statusState.loading && statusState.error && (
          <ErrorState message={statusState.error} />
        )}
        {!statusState.loading && status && !status.has_scan && (
          <p className="text-[14px] text-arepo-muted">{status.note}</p>
        )}
        {!statusState.loading && status && status.has_scan && (
          <div className="space-y-2">
            <p className="text-[15px] font-medium text-arepo-ink" data-testid="eligible-headline">
              {eligibleHeadline(status)}
            </p>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-[13px] text-arepo-muted">
              <span>
                Last complete scan{" "}
                {status.started_at
                  ? new Date(status.started_at).toLocaleString("en-GB")
                  : "unknown"}
              </span>
              <span>Pages fetched {status.pages_fetched}</span>
              <span>
                Pagination{" "}
                {status.pagination_complete ? "complete" : "incomplete (see note)"}
              </span>
            </div>
            {!status.pagination_complete && status.pagination_reason && (
              <p className="text-[12px] leading-relaxed text-arepo-warnText">
                {status.pagination_reason}
              </p>
            )}
            <p className="text-[12px] leading-relaxed text-arepo-muted">
              Leaving this page open does not scan. The scheduled backend refresh discovers and
              analyses the universe; the browser only reads stored results.
            </p>
          </div>
        )}
      </section>

      {/* Controls: closing universe + scope. */}
      <section className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-arepo-ink2">Closing universe</span>
          <select
            data-testid="bucket-select"
            className="select-arepo w-64"
            value={bucket}
            onChange={(e) => setBucket(e.target.value)}
            aria-label="Closing-time universe"
          >
            {BUCKET_OPTIONS.map((b) => (
              <option key={b.id} value={b.id}>
                {b.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-arepo-ink2">Signals shown</span>
          <select
            data-testid="scope-select"
            className="select-arepo w-56"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            aria-label="Signal scope"
          >
            {SCOPE_OPTIONS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      {/* The actual signals, first useful viewport. */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionTitle>Signals</SectionTitle>
          {signals && signals.has_scan && (
            <span className="text-[13px] text-arepo-muted" data-testid="coverage-caption">
              {signals.coverage_caption}
            </span>
          )}
        </div>

        {signalsState.loading && <ListSkeleton rows={6} />}
        {!signalsState.loading && signalsState.error && (
          <ErrorState message={signalsState.error} />
        )}
        {!signalsState.loading && signals && (!signals.has_scan || signals.rows.length === 0) && (
          <EmptyState
            message={
              !signals.has_scan
                ? "No complete scan has been recorded yet."
                : "No qualifying signals in this closing window. Try another window or scope."
            }
          />
        )}
        {!signalsState.loading && signals && signals.rows.length > 0 && (
          <div className="space-y-3">
            {signals.rows.map((r) => (
              <SignalCard key={`${r.market_id}-${r.token_id}`} row={r} />
            ))}
          </div>
        )}
      </section>

      {/* Explanation moved into a collapsed disclosure (prompt section 10). */}
      <Disclose summary="How Signal Lab works">
        <div className="max-w-reading space-y-4 pt-1 text-[14px] leading-relaxed text-arepo-ink2">
          <p>
            A signal fires when a market&apos;s recent price, spread, volume and order-book behaviour
            look statistically unusual compared with its own history. The composite anomaly score
            combines several of these into one 0 to 100 reading. Strength measures how unusual the
            behaviour is; it is not a probability, not accuracy and not a forecast of the outcome.
          </p>
          <p>
            Arepo discovers the complete active market universe through full pagination, keeps every
            market closing within 30 days, analyses all of them, and ranks each closing-time window.
            The public list shows only the top ten, but the full universe is analysed and preserved
            for research, so ten is a display limit and never the number of markets scanned.
          </p>
          <p>
            A strengthening signal means only that the stored strength score increased over the
            comparison period. It does not mean the outcome became more likely or that a trade would
            be profitable. See the{" "}
            <Link
              href="/methodology#signal-strength"
              className="focus-ring font-medium text-arepo-accentActive hover:text-arepo-accentHover"
            >
              methodology
            </Link>{" "}
            for the full derivation.
          </p>
        </div>
      </Disclose>
    </div>
  );
}

function SignalCard({ row }: { row: ScanSignalRow }) {
  const t = row.trajectory;
  const tone = trajectoryTone(t.label);
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
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-5" data-testid="signal-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-tabular text-[13px] text-arepo-muted">
              #{row.rank_in_bucket ?? "-"}
            </span>
            <Link
              href={`/markets/${encodeURIComponent(row.market_id)}?mode=live`}
              className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
            >
              {row.market_question}
            </Link>
          </div>
          <p className="mt-0.5 text-[13px] text-arepo-muted">
            {row.outcome_name}
            {row.direction ? ` · direction ${row.direction}` : ""} ·{" "}
            {timeToCloseLabel(row.time_remaining_hours)}
          </p>
        </div>
        <div className="text-right">
          <span className={`inline-flex items-center gap-1.5 text-[13px] font-semibold ${toneClass}`}>
            <span aria-hidden="true">{tone.glyph}</span>
            {t.label}
          </span>
        </div>
      </div>

      <p className="mt-3 text-[14px] text-arepo-ink2" data-testid="strength-phrase">
        {strengthPhrase(row.strength, t)}.
        {consec ? ` ${consec}.` : ""}
      </p>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[12px] text-arepo-muted">
        {row.public_top_ten ? (
          <Badge tone="accent">Public top ten</Badge>
        ) : (
          <Badge tone="neutral">Shadow directional</Badge>
        )}
        <span>Research Priority {row.research_priority}</span>
        <span>Confidence {Math.round(row.confidence * 100)}%</span>
        {row.overall_rank_30d != null && <span>Overall 30d rank #{row.overall_rank_30d}</span>}
        {t.first_detected && (
          <span>First detected {new Date(t.first_detected).toLocaleString("en-GB")}</span>
        )}
        {row.evidence_families.length > 0 && (
          <span>Evidence: {row.evidence_families.join(", ")}</span>
        )}
      </div>
    </div>
  );
}
