"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import { useUrlState } from "@/lib/use-url-state";
import {
  getReplayCohorts,
  getReplayCohortResults,
  type ReplayCohort,
  type ReplayCohortList,
  type ReplayCounts,
  type ReplayResult,
  type ReplayRow,
} from "@/lib/api";
import {
  CLOSING_OPTIONS,
  HORIZON_OPTIONS,
  SCOPE_OPTIONS,
  cadenceCopy,
  cohortById,
  headlineSentence,
  hitRateAmongMovedText,
  movementCoverageText,
  newestCohortForCadence,
  qualifyingCaption,
  resultLabel,
  type Horizon,
  type Scope,
} from "@/lib/replay";
import { formatPrice } from "@/lib/format";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PageHeader, SectionTitle, Disclose, StatTile, Badge } from "@/components/ui";

const MOVED_TOOLTIP =
  "Moved as expected means the selected outcome's midpoint moved in Arepo's stored direction over " +
  "the selected horizon. It does not mean the market finally resolved correctly or that a trade " +
  "would have been profitable.";

function dt(iso: string | null | undefined): string {
  if (!iso) return "unknown";
  return new Date(iso).toLocaleString("en-GB");
}

function timeToClose(hours: number | null): string {
  if (hours == null) return "unknown";
  if (hours < 48) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

export default function ReplayPage() {
  // Prospective-only: real predictions genuinely frozen before later prices became known. Any
  // legacy `?replay=` mode (reconstructed / synthetic / demo) is ignored and stripped so a removed
  // mode is never displayed (refinement prompt section 1).
  const [legacyMode, setLegacyMode] = useUrlState("replay", "");
  useEffect(() => {
    if (legacyMode) setLegacyMode("");
  }, [legacyMode, setLegacyMode]);

  const cohortsState = useAsync<ReplayCohortList>(() => getReplayCohorts(), []);
  const list = cohortsState.data;

  if (cohortsState.loading) {
    return (
      <div className="space-y-8" data-testid="replay-page">
        <ReplayIntro />
        <ListSkeleton rows={6} />
      </div>
    );
  }
  if (cohortsState.error) {
    return (
      <div className="space-y-8" data-testid="replay-page">
        <ReplayIntro />
        <ErrorState message={cohortsState.error} />
        <p className="text-[13px] text-arepo-muted">
          The Replay data could not be loaded. It will recover automatically when the API
          reconnects.
        </p>
      </div>
    );
  }
  if (!list || !list.has_prospective) {
    return (
      <div className="space-y-8" data-testid="replay-page">
        <ReplayIntro />
        <EmptyState
          message={
            "No prospective cohort has been frozen yet. Replay grows when scheduled backend jobs " +
            "freeze cohorts and collect later prices; once the first freeze runs, the real frozen " +
            "cohort, its timing and its results appear here. Leaving this page open does not " +
            "collect additional evidence."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="replay-page">
      <ReplayIntro />
      <ReplayBody list={list} />
    </div>
  );
}

function ReplayIntro() {
  return (
    <>
      <PageHeader
        title="Replay"
        lead="Real predictions genuinely frozen before later prices became known. Arepo records each research cohort at the moment it is frozen, then measures what happens next from that actual freeze time."
      />
      <DisclaimerBanner>
        Replay is a research record, not trading advice, and past behaviour does not predict future
        results.
      </DisclaimerBanner>
    </>
  );
}

function ReplayBody({ list }: { list: ReplayCohortList }) {
  const cadences = list.cadences;
  const [cadence, setCadence] = useUrlState("cadence", cadences[0]?.cadence ?? "6h");
  // The selected cohort id lives in the URL so direct navigation and refresh restore the exact
  // view. It defaults to the newest cohort of the selected cadence.
  const [cohortRaw, setCohort] = useUrlState("cohort", "");
  const [horizon, setHorizon] = useUrlState("h", "6h");
  const [closing, setClosing] = useUrlState("closing", "all");
  const [scope, setScope] = useUrlState("scope", "directional");

  // Resolve the effective cadence (must be one that really exists).
  const effectiveCadence =
    cadences.find((c) => c.cadence === cadence)?.cadence ?? cadences[0]?.cadence ?? "6h";
  const cohortsForCadence = list.cohorts.filter((c) => c.cadence === effectiveCadence);

  // Resolve the effective cohort: the URL value if it belongs to the cadence, else the newest.
  const urlCohortId = cohortRaw ? Number(cohortRaw) : null;
  const urlCohortValid = cohortsForCadence.some((c) => c.id === urlCohortId);
  const effectiveCohortId =
    (urlCohortValid ? urlCohortId : null) ??
    newestCohortForCadence(list, effectiveCadence)?.id ??
    list.default_cohort_id ??
    null;

  const cohort = cohortById(list, effectiveCohortId);

  const resultsState = useAsync<ReplayResult | null>(
    () =>
      effectiveCohortId != null
        ? getReplayCohortResults(
            effectiveCohortId,
            horizon === "final" ? "6h" : horizon,
            scope,
            closing,
          )
        : Promise.resolve(null),
    [effectiveCohortId, horizon, closing, scope],
  );

  const isFinal = horizon === "final";

  return (
    <div className="space-y-8">
      {/* 1 · Choose cohort cadence and freeze. */}
      <section className="space-y-4">
        <SectionTitle>Choose a frozen cohort</SectionTitle>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-arepo-ink2">Cohort cadence</span>
            <select
              data-testid="cohort-cadence"
              className="select-arepo w-48"
              value={effectiveCadence}
              onChange={(e) => {
                setCadence(e.target.value);
                setCohort(""); // reset to the newest cohort of the new cadence
              }}
            >
              {cadences.map((c) => (
                <option key={c.cadence} value={c.cadence}>
                  {c.label} ({c.count})
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-arepo-ink2">Freeze</span>
            <select
              data-testid="cohort-freeze"
              className="select-arepo w-80 max-w-full"
              value={effectiveCohortId != null ? String(effectiveCohortId) : ""}
              onChange={(e) => setCohort(e.target.value)}
            >
              {cohortsForCadence.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {freezeOptionLabel(c)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {cohort && <FreezeTimingBanner cohort={cohort} />}
        {cohort && (
          <p className="max-w-reading text-[14px] leading-relaxed text-arepo-ink2">
            {cadenceCopy(cohort.cadence)}
          </p>
        )}
      </section>

      {/* 2 + 3 · Choose market closing window and evaluation horizon. */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-arepo-ink2">Evaluation horizon</span>
            <select
              data-testid="horizon-select"
              className="select-arepo w-56"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
            >
              {HORIZON_OPTIONS.map((h) => {
                const evaluable = cohort?.available_horizons?.[h.id] ?? false;
                return (
                  <option key={h.id} value={h.id}>
                    {h.label}
                    {evaluable ? "" : " (pending)"}
                  </option>
                );
              })}
              <option value="final">
                Final resolution
                {cohort?.resolution_available ? "" : " (pending)"}
              </option>
            </select>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-arepo-ink2">Market closing window</span>
            <select
              data-testid="closing-filter"
              className="select-arepo w-96 max-w-full"
              value={closing}
              onChange={(e) => setClosing(e.target.value)}
            >
              {CLOSING_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-arepo-ink2">Signals shown</span>
            <select
              data-testid="scope-select"
              className="select-arepo w-96 max-w-full"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              {SCOPE_OPTIONS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="max-w-reading text-[12px] leading-relaxed text-arepo-muted">
          The closing window filters by how much time each market had left at the moment the cohort
          was frozen. Closing sooner does not mean the signal is stronger.
        </p>
      </section>

      {resultsState.loading && <ListSkeleton rows={6} />}
      {!resultsState.loading && resultsState.error && (
        <ErrorState message={resultsState.error} />
      )}
      {!resultsState.loading && resultsState.data && resultsState.data.found && (
        <ResultsView
          result={resultsState.data}
          horizon={horizon as Horizon | "final"}
          scope={scope as Scope}
          isFinal={isFinal}
        />
      )}
      {!resultsState.loading && resultsState.data && !resultsState.data.found && (
        <EmptyState message="This cohort is not available for Replay." />
      )}

      <p className="max-w-reading text-[12px] leading-relaxed text-arepo-muted">{list.note}</p>
    </div>
  );
}

function freezeOptionLabel(c: ReplayCohort): string {
  const sched = c.scheduled_for ? new Date(c.scheduled_for).toLocaleString("en-GB") : "unscheduled";
  const frozen = c.frozen_at ? new Date(c.frozen_at).toLocaleString("en-GB") : "not frozen";
  const late = c.late ? ` · ${Math.round(c.lateness_minutes)} min late` : "";
  return `Scheduled ${sched} · frozen ${frozen}${late}`;
}

/** Scheduled vs actual freeze, lateness, and evaluation origin in plain language (prompt §10). */
function FreezeTimingBanner({ cohort }: { cohort: ReplayCohort }) {
  const late = cohort.late && cohort.lateness_minutes > 0;
  const tone = late
    ? "border-arepo-warn/40 bg-arepo-warn/10 text-arepo-warnText"
    : "border-arepo-pos/30 bg-arepo-pos/10 text-arepo-ink";
  return (
    <div
      data-testid="freeze-timing-banner"
      className={`rounded-card border px-4 py-3 text-[14px] leading-relaxed ${tone}`}
    >
      <div className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
        <TimingLine k="Scheduled cut-off" v={dt(cohort.scheduled_for)} />
        <TimingLine k="Actually frozen" v={dt(cohort.frozen_at)} />
        <TimingLine
          k="Lateness"
          v={late ? `${Math.round(cohort.lateness_minutes)} minutes late` : "on time"}
        />
        <TimingLine k="Evaluation starts from" v={dt(cohort.evaluation_origin_at)} />
      </div>
      <p className="mt-2 text-[13px]">
        All later price measurements start from the actual freeze time, never the scheduled boundary.
      </p>
    </div>
  );
}

function TimingLine({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-arepo-border/40 py-0.5">
      <span className="text-[13px] font-medium">{k}</span>
      <span className="font-tabular text-[13px]">{v}</span>
    </div>
  );
}

function ResultsView({
  result,
  horizon,
  scope,
  isFinal,
}: {
  result: ReplayResult;
  horizon: Horizon | "final";
  scope: Scope;
  isFinal: boolean;
}) {
  if (isFinal) {
    return <FinalResolutionView result={result} scope={scope} />;
  }

  const c = result.headline;
  const horizonLabel = HORIZON_OPTIONS.find((h) => h.id === horizon)?.label ?? horizon;
  const hitRate = hitRateAmongMovedText(c);

  return (
    <div className="space-y-8">
      {/* 4 · The concise result. */}
      <section className="space-y-4" data-testid="did-move-section">
        <SectionTitle>Did the market move as expected?</SectionTitle>
        <p
          data-testid="headline-sentence"
          className="max-w-reading text-[16px] leading-relaxed text-arepo-ink"
        >
          {headlineSentence(c)}
        </p>
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
          Measured over the {horizonLabel} horizon from the actual freeze time. A move in the stored
          direction counts as expected; a market that did not move is not scored as a miss and stays
          in the denominator.
        </p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <StatTile label="Directional calls" value={String(c.total)} />
          <StatTile label="Moved as expected" value={String(c.moved_expected)} />
          <StatTile label="Moved against" value={String(c.moved_against)} />
          <StatTile label="No change" value={String(c.no_change)} />
          <StatTile label="Pending" value={String(c.pending)} />
          <StatTile label="Unavailable" value={String(c.unavailable)} />
        </div>

        <div className="flex flex-col gap-1.5 text-[13px] text-arepo-ink2">
          <p>{movementCoverageText(c)}</p>
          {hitRate ? (
            <p data-testid="hit-rate-among-moved" className="font-medium">
              {hitRate}
            </p>
          ) : (
            <p className="text-arepo-muted">
              No market in this set moved at this horizon, so no hit rate among moving markets is
              shown.
            </p>
          )}
        </div>

        {/* Public vs shadow split (prompt §6), always shown so neither is implied to outperform. */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SplitCard title="Public selections" c={result.public} />
          <SplitCard title="Shadow directional" c={result.shadow} />
          <SplitCard title="Combined directional" c={result.combined} emphasis />
        </div>
        <p className="text-[12px] leading-relaxed text-arepo-muted">
          Public and shadow are shown side by side; on a single cohort neither is claimed to
          outperform the other.
        </p>
      </section>

      {/* 5 · Inspect the top signals. */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionTitle>Market by market</SectionTitle>
          <span className="text-[13px] text-arepo-muted" data-testid="qualifying-caption">
            {qualifyingCaption(result.shown, result.qualifying, scope)}
          </span>
        </div>
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">{MOVED_TOOLTIP}</p>
        {result.rows.length === 0 ? (
          <EmptyState
            message={
              "No qualifying directional signals in this set. Try a wider closing window or a " +
              "different horizon."
            }
          />
        ) : (
          <MarketTable rows={result.rows} />
        )}
      </section>

      <MethodologySummary result={result} />
    </div>
  );
}

function SplitCard({
  title,
  c,
  emphasis = false,
}: {
  title: string;
  c: ReplayCounts;
  emphasis?: boolean;
}) {
  const hit = hitRateAmongMovedText(c);
  return (
    <div
      className={`rounded-card border p-4 ${
        emphasis
          ? "border-arepo-accentBorder bg-arepo-accentTint"
          : "border-arepo-border bg-arepo-surface"
      }`}
    >
      <div className="text-[13px] font-semibold text-arepo-ink">{title}</div>
      <div className="mt-1 font-tabular text-[14px] text-arepo-ink2">
        {c.moved_expected} expected · {c.moved_against} against · {c.no_change} no change
      </div>
      <div className="mt-1 text-[12px] text-arepo-muted">
        {c.total} directional
        {c.pending > 0 ? ` · ${c.pending} pending` : ""}
        {c.unavailable > 0 ? ` · ${c.unavailable} unavailable` : ""}
      </div>
      {hit && <div className="mt-1 text-[12px] text-arepo-muted">{hit}</div>}
    </div>
  );
}

function ResultBadge({ state }: { state: string }) {
  const { label, tone, glyph } = resultLabel(state);
  const cls =
    tone === "good"
      ? "text-arepo-pos"
      : tone === "bad"
        ? "text-arepo-neg"
        : tone === "flat"
          ? "text-arepo-ink2"
          : "text-arepo-muted";
  return (
    <span className={`inline-flex items-center gap-1.5 text-[13px] font-semibold ${cls}`}>
      <span aria-hidden="true">{glyph}</span>
      {label}
    </span>
  );
}

function MarketTable({ rows }: { rows: ReplayRow[] }) {
  return (
    <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-[13px]" data-testid="market-table">
          <caption className="sr-only">
            Market-by-market Replay results: frozen rank, market, selected outcome, role, Arepo
            direction, frozen midpoint, horizon midpoint, midpoint movement, executable result,
            time remaining at freeze, and result label.
          </caption>
          <thead>
            <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
              <th scope="col" className="px-3 py-3 font-semibold">#</th>
              <th scope="col" className="px-3 py-3 font-semibold">Market / outcome</th>
              <th scope="col" className="px-3 py-3 font-semibold">Role</th>
              <th scope="col" className="px-3 py-3 font-semibold">Direction</th>
              <th scope="col" className="px-3 py-3 font-semibold">Frozen mid</th>
              <th scope="col" className="px-3 py-3 font-semibold">Horizon mid</th>
              <th scope="col" className="px-3 py-3 font-semibold">Midpoint move</th>
              <th scope="col" className="px-3 py-3 font-semibold" title="Estimated result after spread and costs">
                After costs
              </th>
              <th scope="col" className="px-3 py-3 font-semibold">Left at freeze</th>
              <th scope="col" className="px-3 py-3 font-semibold">Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-arepo-border">
            {rows.map((r) => (
              <MarketRow key={`${r.market_id}-${r.token_id}`} r={r} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MarketRow({ r }: { r: ReplayRow }) {
  const roleLabel = r.role === "public_selection" ? "Public" : "Shadow";
  return (
    <tr data-testid="market-row">
      <td className="px-3 py-2.5 font-tabular text-arepo-muted">{r.rank ?? "–"}</td>
      <td className="px-3 py-2.5">
        <Link
          href={`/markets/${encodeURIComponent(r.market_id)}?mode=live`}
          className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
        >
          {r.market_question}
        </Link>
        <div className="text-[12px] text-arepo-muted">{r.outcome_name}</div>
      </td>
      <td className="px-3 py-2.5">
        <Badge tone="neutral">{roleLabel}</Badge>
      </td>
      <td className="px-3 py-2.5 font-tabular">
        {r.direction === "up" && <span className="text-arepo-pos">Up</span>}
        {r.direction === "down" && <span className="text-arepo-neg">Down</span>}
        {!r.direction && <span className="text-arepo-muted">n/a</span>}
      </td>
      <td className="px-3 py-2.5 font-tabular">{formatPrice(r.frozen_midpoint)}</td>
      <td className="px-3 py-2.5 font-tabular">{formatPrice(r.horizon_midpoint)}</td>
      <td className="px-3 py-2.5 font-tabular" title="Midpoint movement (percentage points)">
        {r.movement_pp == null ? "n/a" : `${r.movement_pp > 0 ? "+" : ""}${r.movement_pp} pp`}
      </td>
      <td className="px-3 py-2.5 font-tabular">
        {r.executable.available && r.executable.move != null ? (
          <span title="Estimated result after spread and costs">
            {`${r.executable.move > 0 ? "+" : ""}${(r.executable.move * 100).toFixed(1)} pp`}
          </span>
        ) : (
          <span
            className="text-arepo-muted"
            title="Executable result unavailable for this observation."
          >
            unavailable
          </span>
        )}
      </td>
      <td className="px-3 py-2.5 font-tabular">{timeToClose(r.time_remaining_hours)}</td>
      <td className="px-3 py-2.5">
        <ResultBadge state={r.result_state} />
      </td>
    </tr>
  );
}

function FinalResolutionView({ result, scope }: { result: ReplayResult; scope: Scope }) {
  const res = result.resolution;
  return (
    <div className="space-y-8">
      <section className="space-y-4" data-testid="did-move-section">
        <SectionTitle>What did the market finally resolve to?</SectionTitle>
        <p className="max-w-reading text-[14px] leading-relaxed text-arepo-ink2">
          Final resolution is kept separate from short-term repricing: a favourable short-term move
          is not a correct final-outcome forecast. A signal counts as correct here only when the
          market finally resolved to the selected outcome.
        </p>
        {!result.resolution_available && (
          <div className="rounded-card border border-arepo-border bg-arepo-surface2 px-4 py-3 text-[13px] leading-relaxed text-arepo-muted">
            None of these markets has resolved yet, so final resolution is pending for the whole
            cohort.
          </div>
        )}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Directional calls" value={String(res.total)} />
          <StatTile label="Resolved correct" value={String(res.resolved_correct)} />
          <StatTile label="Resolved incorrect" value={String(res.resolved_incorrect)} />
          <StatTile label="Unresolved" value={String(res.unresolved)} />
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionTitle>Market by market</SectionTitle>
          <span className="text-[13px] text-arepo-muted" data-testid="qualifying-caption">
            {qualifyingCaption(result.shown, result.qualifying, scope)}
          </span>
        </div>
        {result.rows.length === 0 ? (
          <EmptyState message="No qualifying directional signals in this set." />
        ) : (
          <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-[13px]" data-testid="market-table">
                <thead>
                  <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
                    <th scope="col" className="px-3 py-3 font-semibold">#</th>
                    <th scope="col" className="px-3 py-3 font-semibold">Market / outcome</th>
                    <th scope="col" className="px-3 py-3 font-semibold">Selected outcome</th>
                    <th scope="col" className="px-3 py-3 font-semibold">Final resolution</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-arepo-border">
                  {result.rows.map((r) => (
                    <tr key={`${r.market_id}-${r.token_id}`} data-testid="market-row">
                      <td className="px-3 py-2.5 font-tabular text-arepo-muted">{r.rank ?? "–"}</td>
                      <td className="px-3 py-2.5">
                        <Link
                          href={`/markets/${encodeURIComponent(r.market_id)}?mode=live`}
                          className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
                        >
                          {r.market_question}
                        </Link>
                      </td>
                      <td className="px-3 py-2.5">{r.outcome_name}</td>
                      <td className="px-3 py-2.5">
                        {r.resolution.resolved ? (
                          <span className="font-medium">
                            {r.resolution.correct === true
                              ? "Resolved to selected outcome"
                              : r.resolution.correct === false
                                ? "Resolved to a different outcome"
                                : `Resolved: ${r.resolution.resolved_outcome ?? "recorded"}`}
                          </span>
                        ) : (
                          <span className="text-arepo-muted">Pending resolution</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <MethodologySummary result={result} />
    </div>
  );
}

/** Cohort methodology summary (prompt §5): the observation and abstention-control counts live here,
 * never mixed into the directional result table. */
function MethodologySummary({ result }: { result: ReplayResult }) {
  const rc = result.role_counts;
  const rows: [string, string][] = [
    ["Full frozen universe", String(result.cohort.universe_size)],
    ["Public selections", String(rc.public_selection ?? 0)],
    ["Shadow directional", String(rc.shadow_directional ?? 0)],
    ["Observations (non-directional)", String(rc.observation ?? 0)],
    ["Abstention controls", String(rc.abstention_control ?? 0)],
    ["Model version", result.cohort.model_version],
  ];
  return (
    <Disclose summary="Cohort methodology and full role counts">
      <div className="space-y-3">
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
          The directional result above covers public and shadow directional signals only.
          Observation and abstention-control rows are part of the frozen universe for research but
          are never mixed into the directional result table.
        </p>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-arepo-border py-1">
              <dt className="text-[13px] text-arepo-muted">{k}</dt>
              <dd className="font-tabular text-[13px] font-medium text-arepo-ink2">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="max-w-reading text-[12px] leading-relaxed text-arepo-muted">{result.note}</p>
      </div>
    </Disclose>
  );
}
