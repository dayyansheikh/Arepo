"use client";

import { useMemo } from "react";
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
  CLOSING_PILLS,
  HORIZON_TABS,
  SCOPE_HELP,
  SCOPE_TABS,
  apiHorizon,
  apiScope,
  cohortSummaryLine,
  hitRateSentence,
  horizonAvailability,
  horizonTooltip,
  nextFreezeLine,
  nextFreezeLocal,
  pendingMessage,
  pickCohortForCategory,
  resultTitle,
  type ClosingPill,
  type HorizonTab,
  type ScopeTab,
} from "@/lib/replay-ux";
import { resultLabel } from "@/lib/replay";
import { directionLabel, DIRECTION_TONE_CLASS } from "@/lib/directional";
import { formatPrice } from "@/lib/format";
import { StrengthBar } from "@/components/StrengthBar";
import { CategoryFilterRow } from "@/components/CategoryFilterRow";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";
import { PageHeader, SectionTitle, Disclose, Badge } from "@/components/ui";
import { ALL_CATEGORY, type CategoryFilter } from "@/lib/categories";

function dt(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString("en-GB") : "unknown";
}

export default function ReplayPage() {
  const cohortsState = useAsync<ReplayCohortList>(() => getReplayCohorts(), []);
  const list = cohortsState.data;

  const [horizonRaw, setHorizon] = useUrlState("h", "6h");
  const [closing, setClosing] = useUrlState("closing", "all");
  const [scopeRaw, setScope] = useUrlState("scope", "public");
  const [category, setCategory] = useUrlState("category", ALL_CATEGORY);
  const [manualCohort, setManualCohort] = useUrlState("cohort", "");
  const horizon = horizonRaw as HorizonTab;
  const scope = scopeRaw as ScopeTab;

  const now = useMemo(() => new Date(), []);
  const picked = useMemo(
    () => pickCohortForCategory(list, horizon, category, now),
    [list, horizon, category, now],
  );
  const newest = list?.cohorts?.[0];

  const manualId = manualCohort ? Number(manualCohort) : null;
  const cohort: ReplayCohort | undefined =
    (manualId != null ? list?.cohorts.find((c) => c.id === manualId) : undefined) ?? picked.cohort;
  const cohortId = cohort?.id ?? null;
  // The newest cohort is still collecting for this horizon while we show an older evaluated one.
  const newestIsCollecting =
    category === ALL_CATEGORY && !!newest && !!cohort && newest.id !== cohort.id && manualId == null;

  const resultsState = useAsync<ReplayResult | null>(
    () =>
      cohortId != null
        ? getReplayCohortResults(
            cohortId,
            apiHorizon(horizon),
            apiScope(scope),
            closing,
            category,
          )
        : Promise.resolve(null),
    [cohortId, horizon, closing, scope, category],
  );
  const result = resultsState.data;

  return (
    <div className="space-y-6" data-testid="replay-page">
      <PageHeader
        title="Replay"
        lead="How did Arepo Opportunities in this category perform?"
      />

      {cohortsState.loading && <ListSkeleton rows={5} />}
      {!cohortsState.loading && cohortsState.error && <ErrorState message={cohortsState.error} />}
      {!cohortsState.loading && list && !list.has_prospective && (
        <EmptyState message="No cohort has been frozen yet. Replay fills in once the scheduled backend jobs freeze a cohort and collect later prices." />
      )}

      {cohort && (
        <>
          {/* One subtle cohort line + collapsed mechanics. */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-arepo-muted">
            <span data-testid="cohort-line">{cohortSummaryLine(cohort)}</span>
            <span aria-hidden="true">·</span>
            <span
              data-testid="next-freeze"
              title="Cohorts freeze every 6 hours at 00:00 / 06:00 / 12:00 / 18:00 UTC. Live signals continue updating between freezes."
            >
              {nextFreezeLine(now)}
            </span>
            {newestIsCollecting && (
              <button
                type="button"
                className="focus-ring rounded text-arepo-accentActive hover:underline"
                onClick={() => newest && setManualCohort(String(newest.id))}
                data-testid="latest-cohort-link"
              >
                Latest cohort still collecting → view it
              </button>
            )}
            {manualId != null && (
              <button
                type="button"
                className="focus-ring rounded text-arepo-accentActive hover:underline"
                onClick={() => setManualCohort("")}
              >
                Back to latest evaluated
              </button>
            )}
          </div>
          <p className="text-[12px] text-arepo-muted">
            Live signals continue updating between freezes.
          </p>

          <div className="space-y-4" data-testid="primary-replay-controls">
            <div className="space-y-1.5">
              <div className="text-[12px] font-medium text-arepo-muted">Horizon</div>
              <HorizonTabs cohort={cohort} horizon={horizon} setHorizon={setHorizon} now={now} />
            </div>
            <CategoryFilterRow
              value={category}
              onChange={(next: CategoryFilter) => setCategory(next)}
            />
          </div>

          <div data-testid="more-filters">
            <Disclose summary="More filters">
              <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
                <PillRow
                  label="Closing"
                  options={CLOSING_PILLS}
                  value={closing}
                  onChange={setClosing}
                  testid="closing-pills"
                  help="Based on how long the market had left when Arepo recorded the signal."
                />
                <PillRow
                  label="Signals"
                  options={SCOPE_TABS}
                  value={scope}
                  onChange={setScope}
                  testid="scope-pills"
                  help={SCOPE_HELP[scope]}
                />
              </div>
            </Disclose>
          </div>

          <CohortControls list={list!} cohort={cohort} manualId={manualId} setManual={setManualCohort} />

          {resultsState.loading && <ListSkeleton rows={5} />}
          {!resultsState.loading && resultsState.error && (
            <ErrorState message={resultsState.error} />
          )}
          {!resultsState.loading && result && result.found && (
            <ResultsArea
              result={result}
              cohort={cohort}
              horizon={horizon}
              scope={scope}
              now={now}
              categoryCapableExists={picked.categoryCapable}
            />
          )}

          <CohortDetails cohort={cohort} result={result} now={now} />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------------------

function CohortControls({
  list,
  cohort,
  manualId,
  setManual,
}: {
  list: ReplayCohortList;
  cohort: ReplayCohort;
  manualId: number | null;
  setManual: (v: string) => void;
}) {
  if (list.cohorts.length <= 1) return null;
  return (
    <Disclose summary="Previous cohorts">
      <label className="flex flex-col gap-1.5">
        <span className="sr-only">Viewing cohort</span>
        <select
          data-testid="cohort-select"
          className="select-arepo w-96 max-w-full"
          value={manualId != null ? String(manualId) : String(cohort.id)}
          onChange={(e) => setManual(e.target.value)}
          aria-label="Viewing cohort"
        >
          {list.cohorts.map((c) => (
            <option key={c.id} value={String(c.id)}>
              {c.cadence_label} · frozen {dt(c.frozen_at)} · {c.universe_size} markets
            </option>
          ))}
        </select>
      </label>
    </Disclose>
  );
}

function HorizonTabs({
  cohort,
  horizon,
  setHorizon,
  now,
}: {
  cohort: ReplayCohort;
  horizon: HorizonTab;
  setHorizon: (v: string) => void;
  now: Date;
}) {
  return (
    <div
      className="inline-flex flex-wrap gap-1 rounded-control border border-arepo-border bg-arepo-surface p-0.5"
      role="tablist"
      aria-label="Evaluation horizon"
      data-testid="horizon-tabs"
    >
      {HORIZON_TABS.map((tab) => {
        const avail = horizonAvailability(cohort, tab.id, now);
        const pending = avail !== "evaluable";
        const active = horizon === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active}
            data-testid={`horizon-${tab.id}`}
            title={pending ? horizonTooltip(cohort, tab.id) : undefined}
            onClick={() => setHorizon(tab.id)}
            className={`focus-ring rounded-[8px] px-3 py-1.5 text-[14px] font-medium transition-colors ${
              active
                ? "bg-arepo-accentTint text-arepo-accentActive"
                : "text-arepo-muted hover:text-arepo-ink"
            }`}
          >
            {tab.label}
            {pending && <span className="ml-1 text-[11px] text-arepo-muted">· pending</span>}
          </button>
        );
      })}
    </div>
  );
}

function PillRow({
  label,
  options,
  value,
  onChange,
  testid,
  help,
}: {
  label: string;
  options: { id: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  testid: string;
  help?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[12px] font-medium text-arepo-muted">{label}</span>
      <div
        className="inline-flex flex-wrap gap-1 rounded-control border border-arepo-border bg-arepo-surface p-0.5"
        role="group"
        aria-label={label}
        data-testid={testid}
        title={help}
      >
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            aria-pressed={value === o.id}
            data-testid={`${testid}-${o.id}`}
            onClick={() => onChange(o.id)}
            className={`focus-ring rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors ${
              value === o.id
                ? "bg-arepo-accentTint text-arepo-accentActive"
                : "text-arepo-muted hover:text-arepo-ink"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// Result area
// ---------------------------------------------------------------------------------------

function ResultsArea({
  result,
  cohort,
  horizon,
  scope,
  now,
  categoryCapableExists,
}: {
  result: ReplayResult;
  cohort: ReplayCohort;
  horizon: HorizonTab;
  scope: ScopeTab;
  now: Date;
  categoryCapableExists: boolean;
}) {
  return (
    <div className="space-y-6">
      <section className="space-y-3" data-testid="result-block">
        <SectionTitle>{resultTitle(horizon)}</SectionTitle>
        {horizon === "close" ? (
          <FreezeToCloseResult result={result} />
        ) : horizon === "resolved" ? (
          <ResolutionResult result={result} />
        ) : (
          <RepricingResult result={result} cohort={cohort} horizon={horizon} now={now} />
        )}
      </section>

      {scope === "research" && <ResearchComparison result={result} />}

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionTitle>Individual markets</SectionTitle>
          <span className="text-[13px] text-arepo-muted" data-testid="row-caption">
            {result.shown} of {result.qualifying} shown
          </span>
        </div>
        {result.rows.length === 0 ? (
          <EmptyState
            message={
              result.category !== ALL_CATEGORY && result.category_metadata_available === 0
                ? categoryCapableExists
                  ? "Category metadata was not frozen for this legacy cohort, so Arepo will not invent a historical category. Try All or return to the automatic cohort."
                  : "No category-capable prospective cohort has been frozen yet. Arepo will not infer historical categories from current data; try All while the first prospective category cohort is collected."
                : "No signals in this set. Try another category, a wider closing window or a different horizon."
            }
          />
        ) : (
          <div className="space-y-2">
            {result.rows.map((r) => (
              <MarketRow key={`${r.market_id}-${r.token_id}`} r={r} horizon={horizon} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

/** The main visual focus: a big four-number result + a plain hit-rate sentence, OR a single clean
 * pending state (never six zero cards). */
function RepricingResult({
  result,
  cohort,
  horizon,
  now,
}: {
  result: ReplayResult;
  cohort: ReplayCohort;
  horizon: HorizonTab;
  now: Date;
}) {
  const c = result.headline;
  const avail = horizonAvailability(cohort, horizon, now);
  if (c.total > 0 && c.pending === c.total && avail !== "evaluable") {
    const msg = pendingMessage(cohort, horizon, c.total);
    return (
      <div
        className="rounded-card border border-arepo-border bg-arepo-surface2 px-5 py-6"
        data-testid="pending-state"
      >
        <p className="text-[16px] font-semibold text-arepo-ink">{msg.title}</p>
        <p className="mt-1 text-[14px] text-arepo-muted">{msg.detail}</p>
      </div>
    );
  }
  const hit = hitRateSentence(c);
  return (
    <div data-testid="repricing-result">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <BigStat label="Moved as expected" value={c.moved_expected} tone="good" />
        <BigStat label="Moved against" value={c.moved_against} tone="bad" />
        <BigStat label="No change" value={c.no_change} tone="flat" />
        <BigStat
          label={
            c.pending + c.unavailable + c.closed_before_horizon > 0
              ? "Pending / unavailable"
              : "Pending"
          }
          value={c.pending + c.unavailable + c.closed_before_horizon}
          tone="muted"
        />
      </div>
      {c.closed_before_horizon > 0 && (
        <p className="mt-2 text-[13px] text-arepo-muted">
          {c.closed_before_horizon} closed before this evaluation horizon.
        </p>
      )}
      {hit ? (
        <p className="mt-3 text-[15px] font-medium text-arepo-ink2" data-testid="hit-sentence">
          {hit}
        </p>
      ) : (
        <p className="mt-3 text-[14px] text-arepo-muted">
          No market in this set moved at this horizon, so no hit rate is shown.
        </p>
      )}
    </div>
  );
}

function FreezeToCloseResult({ result }: { result: ReplayResult }) {
  const f = result.freeze_to_close;
  if (!f) return <p className="text-[14px] text-arepo-muted">Freeze-to-close data unavailable.</p>;
  return (
    <div data-testid="freeze-to-close-result">
      <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
        Price movement from the freeze to the final valid observation before each market closes. A
        closed market may still be awaiting resolution.
      </p>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <BigStat label="Moved as expected" value={f.moved_expected} tone="good" />
        <BigStat label="Moved against" value={f.moved_against} tone="bad" />
        <BigStat label="No change" value={f.no_change} tone="flat" />
        <BigStat label="Closed, final" value={f.closed_final} tone="muted" />
        <BigStat label="Pending" value={f.pending} tone="muted" />
      </div>
    </div>
  );
}

function ResolutionResult({ result }: { result: ReplayResult }) {
  const r = result.resolution;
  return (
    <div data-testid="resolution-result">
      <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
        Whether the selected outcome finally resolved. Kept separate from price movement: a market can
        move as expected yet resolve the other way. Unresolved markets stay pending.
      </p>
      {!result.resolution_available && (
        <p className="mt-2 text-[13px] text-arepo-muted" data-testid="resolution-pending">
          None of these markets has resolved yet. Closed markets await resolution.
        </p>
      )}
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <BigStat label="Resolved correct" value={r.resolved_correct} tone="good" />
        <BigStat label="Resolved incorrect" value={r.resolved_incorrect} tone="bad" />
        <BigStat label="Unresolved" value={r.unresolved} tone="muted" />
        <BigStat label="Total" value={r.total} tone="flat" />
      </div>
    </div>
  );
}

function ResearchComparison({ result }: { result: ReplayResult }) {
  return (
    <section className="space-y-3" data-testid="research-comparison">
      <SectionTitle>Research comparison</SectionTitle>
      <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
        Public Opportunities versus the directional signals that were not selected (shadow). On a
        single cohort neither is claimed to outperform the other.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <SplitCard title="Opportunities (public)" c={result.public} />
        <SplitCard title="Shadow directional" c={result.shadow} />
        <SplitCard title="Combined" c={result.combined} emphasis />
      </div>
    </section>
  );
}

function BigStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "good" | "bad" | "flat" | "muted";
}) {
  const cls =
    tone === "good"
      ? "text-arepo-pos"
      : tone === "bad"
        ? "text-arepo-neg"
        : tone === "flat"
          ? "text-arepo-ink"
          : "text-arepo-muted";
  return (
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-4">
      <div className="mb-1 text-[12px] text-arepo-muted">{label}</div>
      <div className={`font-tabular text-3xl font-bold ${cls}`}>{value}</div>
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
        {c.total} directional{c.pending > 0 ? ` · ${c.pending} pending` : ""}
        {c.unavailable > 0 ? ` · ${c.unavailable} unavailable` : ""}
        {c.closed_before_horizon > 0
          ? ` · ${c.closed_before_horizon} closed before horizon`
          : ""}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// Concise market row with progressive disclosure
// ---------------------------------------------------------------------------------------

function MarketRow({ r, horizon }: { r: ReplayRow; horizon: HorizonTab }) {
  const label = resultLabel(
    horizon === "close"
      ? precloseState(r)
      : horizon === "resolved"
        ? resolutionState(r)
        : r.result_state,
  );
  const cls =
    label.tone === "good"
      ? "text-arepo-pos"
      : label.tone === "bad"
        ? "text-arepo-neg"
        : label.tone === "flat"
          ? "text-arepo-ink2"
          : "text-arepo-muted";
  const dir = directionLabel(r.direction, r.outcome_name);
  return (
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-4" data-testid="market-row">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Link
            href={`/markets/${encodeURIComponent(r.market_id)}`}
            className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
          >
            {r.market_question}
          </Link>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[13px] text-arepo-muted">
            <span
              className={`font-medium ${DIRECTION_TONE_CLASS[dir.tone]}`}
              title="Arepo's directional call: which way this outcome had been repricing when the signal was frozen. Not a probability, not good or bad."
            >
              <span aria-hidden="true">{dir.glyph}</span> {dir.text}
            </span>
            <span className="font-tabular">Strength {Math.round((r.strength ?? 0) * 100)}</span>
            <span className="font-tabular">
              {formatPrice(r.frozen_midpoint)}
              {" → "}
              {formatPrice(r.horizon_midpoint)}
            </span>
            {r.movement_pp != null && (
              <span className="font-tabular">
                {r.movement_pp > 0 ? "+" : ""}
                {r.movement_pp} pts
              </span>
            )}
          </div>
        </div>
        <span className={`inline-flex items-center gap-1.5 text-[13px] font-semibold ${cls}`}>
          <span aria-hidden="true">{label.glyph}</span>
          {label.label}
        </span>
      </div>

      <Disclose summary="View details" className="mt-2">
        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 pt-1 text-[13px] sm:grid-cols-3">
          <Detail label="Research Priority" value={String(r.research_priority)} />
          <Detail label="Confidence" value={`${Math.round((r.confidence ?? 0) * 100)}%`} />
          <Detail label="Role" value={r.role === "public_selection" ? "Opportunity" : "Shadow"} />
          <Detail label="Frozen bid / ask" value={`${formatPrice(r.frozen_midpoint)}`} />
          <Detail
            label="After costs (executable)"
            value={
              r.executable.available && r.executable.move != null
                ? `${r.executable.move > 0 ? "+" : ""}${(r.executable.move * 100).toFixed(1)} pp`
                : "unavailable"
            }
          />
          {r.freeze_to_close && (
            <Detail
              label="Freeze to close"
              value={
                r.freeze_to_close.movement != null
                  ? `${(r.freeze_to_close.movement * 100).toFixed(1)} pp (${r.freeze_to_close.state})`
                  : "pending"
              }
            />
          )}
          {r.evolution?.available && (
            <Detail
              label="Signal evolution"
              value={`${r.evolution.label} (${Math.round((r.evolution.later_strength ?? 0) * 100)})`}
            />
          )}
          <Detail
            label="Final resolution"
            value={
              r.resolution.resolved
                ? r.resolution.correct
                  ? "resolved to selected outcome"
                  : "resolved to a different outcome"
                : "closed, awaiting resolution"
            }
          />
        </div>
        <div className="mt-2">
          <StrengthBar value={r.strength ?? 0} />
        </div>
      </Disclose>
    </div>
  );
}

function precloseState(r: ReplayRow): string {
  const f = r.freeze_to_close;
  if (!f || f.result == null) return "pending";
  return f.result;
}

function resolutionState(r: ReplayRow): string {
  if (!r.resolution.resolved) return "pending";
  return r.resolution.correct ? "moved_expected" : "moved_against";
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-arepo-muted">{label}</div>
      <div className="font-tabular font-medium text-arepo-ink">{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// Cohort mechanics (collapsed by default)
// ---------------------------------------------------------------------------------------

function CohortDetails({
  cohort,
  result,
  now,
}: {
  cohort: ReplayCohort;
  result: ReplayResult | null;
  now: Date;
}) {
  const den = result?.denominators;
  const rows: [string, string][] = [
    ["Cadence", cohort.cadence_label],
    ["Scheduled cut-off", dt(cohort.scheduled_for)],
    ["Actually frozen", dt(cohort.frozen_at)],
    ["Lateness", cohort.late ? `${Math.round(cohort.lateness_minutes)} minutes` : "on time"],
    ["Next research freeze (your time)", nextFreezeLocal(now)],
    ["Evaluation starts from", dt(cohort.evaluation_origin_at)],
    ["Selection policy", result?.selection_policy ?? "-"],
    ["Full frozen universe", String(cohort.universe_size)],
  ];
  return (
    <Disclose summary="Cohort details" data-testid="cohort-details">
      <div className="space-y-3">
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-arepo-border py-1">
              <dt className="text-[13px] text-arepo-muted">{k}</dt>
              <dd className="font-tabular text-[13px] font-medium text-arepo-ink2">{v}</dd>
            </div>
          ))}
        </dl>
        {den && (
          <div className="text-[12px] text-arepo-muted">
            Denominators: {den.observations} observations · {den.unique_markets} unique markets ·{" "}
            {den.unique_events} unique events · {den.repeated_markets} repeated. Five-minute snapshots
            are history, not separate predictions.
          </div>
        )}
        <p className="max-w-reading text-[12px] leading-relaxed text-arepo-muted">
          Outcomes are measured from the actual freeze time, never the scheduled boundary. See the{" "}
          <Link href="/methodology" className="underline hover:text-arepo-ink">
            methodology
          </Link>{" "}
          for the full evaluation rules. Later signal changes never rewrite a frozen prediction.
        </p>
        <Badge tone="neutral">Research record, not trading advice</Badge>
      </div>
    </Disclose>
  );
}
