"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import { useUrlState } from "@/lib/use-url-state";
import {
  getBacktest,
  getCohort,
  getCohortProvenance,
  getCohortWeeks,
  getHistoricalScreen,
  getReplayDataStatus,
} from "@/lib/api";
import type {
  BaselineComparison,
  BacktestEvent,
  CohortDetail,
  CohortEntry,
  CohortWeek,
  HistoricalEntry,
  HistoricalScreen,
  ProvenanceInfo,
} from "@/lib/types";
import {
  formatPercent,
  formatPrice,
  formatSignedPercent,
  formatZScore,
  formatDate,
} from "@/lib/format";
import { friendlyComponentName } from "@/lib/signal-labels";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PageHeader, SectionTitle, Disclose, StatTile, Badge } from "@/components/ui";
import { MetricHelp } from "@/components/MetricHelp";

type View = "movement" | "resolution";

function money(v: number | null | undefined): string {
  if (v === null || v === undefined) return "n/a";
  const sign = v < 0 ? "-" : "";
  return `${sign}$${Math.abs(v).toFixed(2)}`;
}

export default function ReplayPage() {
  const weeksState = useAsync(() => getCohortWeeks(), []);
  const provenanceState = useAsync<ProvenanceInfo>(() => getCohortProvenance(), []);
  const weeks = weeksState.data;

  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    if (weeks && weeks.length > 0 && selected === null) {
      setSelected(`${weeks[0].iso_year}-${weeks[0].iso_week}`);
    }
  }, [weeks, selected]);

  const activeWeek: CohortWeek | undefined = useMemo(() => {
    if (!weeks || selected === null) return undefined;
    return weeks.find((w) => `${w.iso_year}-${w.iso_week}` === selected);
  }, [weeks, selected]);

  const cohortState = useAsync<CohortDetail | null>(
    () =>
      activeWeek
        ? getCohort(activeWeek.iso_year, activeWeek.iso_week)
        : Promise.resolve(null),
    [activeWeek?.iso_year, activeWeek?.iso_week]
  );

  const [view, setView] = useState<View>("movement");
  // Default to the reconstructed "last week's opportunities" (real, honest) rather than the
  // prospective cohort list, which currently holds only labelled synthetic demo data and showed a
  // stale cohort as if it were current (spec §14, §19). The mode persists in the URL.
  const [mode, setMode] = useUrlState("replay", "historical") as [
    "historical" | "prospective",
    (v: string) => void,
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Replay"
        lead="If you had opened Arepo at a past cut-off and followed its top directional opportunities, what happened next? The default reconstructs those opportunities from only the data available at the time. A separate prospective record freezes each week's real selections and tracks them forward."
      />

      <DisclaimerBanner>
        Replay is a research record, not trading advice, and past behaviour does not predict
        future results.
      </DisclaimerBanner>

      {/* Reconstructed "last week's opportunities" (default) vs the prospective frozen record. */}
      <div
        className="inline-flex rounded-control border border-arepo-border bg-arepo-surface p-0.5"
        role="tablist"
        aria-label="Replay mode"
      >
        {(
          [
            ["historical", "Last week's opportunities"],
            ["prospective", "Prospective record"],
          ] as ["historical" | "prospective", string][]
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={mode === key}
            onClick={() => setMode(key)}
            className={`focus-ring rounded-[8px] px-3.5 py-1.5 text-[14px] font-medium transition-colors ${
              mode === key
                ? "bg-arepo-accentTint text-arepo-accentActive"
                : "text-arepo-muted hover:text-arepo-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* The three Replay data provenances (spec §20). They are never combined into one headline
          performance number. */}
      <Disclose summary="What Prospective, Reconstructed and Synthetic mean">
        <dl className="max-w-reading space-y-2 text-[13px] leading-relaxed text-arepo-muted">
          <div>
            <dt className="font-semibold text-arepo-ink2">Prospective</dt>
            <dd>Signals genuinely recorded and frozen at the time, then tracked forward. The only
              real long-term performance record.</dd>
          </div>
          <div>
            <dt className="font-semibold text-arepo-ink2">Reconstructed</dt>
            <dd>Signals rebuilt later using only information that existed at the historical cut-off
              (price-only, since historical order books were never stored). Illustrative, not a
              track record.</dd>
          </div>
          <div>
            <dt className="font-semibold text-arepo-ink2">Synthetic</dt>
            <dd>Demonstration data only, for testing and teaching. Never mixed into any real
              performance figure.</dd>
          </div>
        </dl>
      </Disclose>

      {mode === "historical" && <HistoricalView />}

      {mode === "prospective" && (
        <>
      {weeksState.loading && <ListSkeleton rows={5} />}
      {!weeksState.loading && weeksState.error && <ErrorState message={weeksState.error} />}

      {!weeksState.loading && weeks && weeks.length === 0 && (
        <EmptyState
          message={
            "No cohorts have been recorded yet. Prospective tracking begins at the first " +
            "run of the weekly evaluation, then a frozen cohort appears here each week."
          }
        />
      )}

      {weeks && weeks.length > 0 && (
        <>
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-[13px] font-medium text-arepo-ink2">Week</span>
              <select
                className="select-arepo w-56"
                value={selected ?? ""}
                onChange={(e) => setSelected(e.target.value)}
              >
                {weeks.map((w) => (
                  <option key={w.label} value={`${w.iso_year}-${w.iso_week}`}>
                    {w.label}
                    {w.provenance_class !== "prospective"
                      ? ` (${w.provenance_class})`
                      : ""}
                  </option>
                ))}
              </select>
            </label>
            {activeWeek && (
              <p className="text-[13px] text-arepo-muted">
                Cut-off {formatDate(activeWeek.cutoff_at)} ·{" "}
                {activeWeek.frozen ? "frozen" : "provisional"} ·{" "}
                {activeWeek.actual_size} of {activeWeek.target_size} slots
              </p>
            )}
          </div>

          {activeWeek && activeWeek.provenance_class !== "prospective" && (
            <ProvenanceNotice week={activeWeek} note={cohortState.data?.summary.note} />
          )}

          {cohortState.loading && <ListSkeleton rows={5} />}
          {!cohortState.loading && cohortState.error && (
            <ErrorState message={cohortState.error} />
          )}

          {!cohortState.loading && cohortState.data && (
            <CohortView detail={cohortState.data} view={view} setView={setView} />
          )}
        </>
      )}

      <Disclose summary="Show the signal backtest (demonstration dataset)">
        <BacktestDemo />
      </Disclose>
        </>
      )}

      {provenanceState.data && <ProvenanceFootnote info={provenanceState.data} />}
    </div>
  );
}

function ProvenanceNotice({ week, note }: { week: CohortWeek; note?: string | null }) {
  const label =
    week.provenance_class === "synthetic" ? "Synthetic demonstration" : "Reconstructed";
  return (
    <div className="flex items-start gap-2.5 rounded-card border border-arepo-border bg-arepo-surface2 px-4 py-3 text-[14px] leading-relaxed text-arepo-ink2">
      <span className="mt-0.5 inline-flex flex-none items-center rounded-full bg-arepo-ink/8 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-arepo-ink2">
        {label}
      </span>
      <span>
        {note ??
          "This cohort is a demonstration, not real prospective performance, and is never mixed into real statistics."}
      </span>
    </div>
  );
}

function CohortView({
  detail,
  view,
  setView,
}: {
  detail: CohortDetail;
  view: View;
  setView: (v: View) => void;
}) {
  const s = detail.summary;
  return (
    <div className="space-y-8">
      <p className="max-w-reading text-[16px] leading-relaxed text-arepo-ink">
        {s.plain_summary}
      </p>

      {/* View switch */}
      <div
        className="inline-flex rounded-control border border-arepo-border bg-arepo-surface p-0.5"
        role="tablist"
        aria-label="Evaluation view"
      >
        {(
          [
            ["movement", "Price movement"],
            ["resolution", "Final resolution"],
          ] as [View, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={view === key}
            onClick={() => setView(key)}
            className={`focus-ring rounded-[8px] px-3.5 py-1.5 text-[14px] font-medium transition-colors ${
              view === key
                ? "bg-arepo-accentTint text-arepo-accentActive"
                : "text-arepo-muted hover:text-arepo-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {view === "movement" ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <StatTile label="Signals selected" value={String(s.selected)} />
          <StatTile label="Moved as expected" value={String(s.moved_expected)} />
          <StatTile label="Moved against" value={String(s.moved_against)} />
          <StatTile label="Flat" value={String(s.moved_flat ?? 0)} />
          <StatTile label="Pending" value={String(s.movement_pending)} />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Signals selected" value={String(s.selected)} />
          <StatTile label="Resolved correct" value={String(s.resolved_correct)} />
          <StatTile label="Resolved incorrect" value={String(s.resolved_incorrect)} />
          <StatTile label="Unresolved" value={String(s.unresolved)} />
        </div>
      )}
      <p className="-mt-4 text-[13px] text-arepo-muted">
        {view === "movement"
          ? `Price movement is measured at the ${s.movement_horizon} horizon after the freeze. A move in the signalled direction counts as expected; it is not a claim of profitability.`
          : "Final resolution counts a signal as correct only when the selected outcome ultimately resolved true. Unresolved markets stay pending."}
      </p>

      <section className="space-y-3">
        <SectionTitle>Selected signals</SectionTitle>
        <div className="space-y-3">
          {detail.entries.map((e) => (
            <EntryRow key={`${e.market_id}-${e.token_id}`} entry={e} view={view} />
          ))}
          {detail.entries.length === 0 && (
            <EmptyState message="No signals qualified for this week." />
          )}
        </div>
      </section>

      <Portfolio detail={detail} />
    </div>
  );
}

function Verdict({ tone, label }: { tone: "good" | "bad" | "pending"; label: string }) {
  const icon =
    tone === "good" ? "✓" : tone === "bad" ? "✗" : "•";
  const cls =
    tone === "good"
      ? "text-arepo-pos"
      : tone === "bad"
        ? "text-arepo-neg"
        : "text-arepo-muted";
  return (
    <span className={`inline-flex items-center gap-1.5 text-[13px] font-semibold ${cls}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}

function movementVerdict(e: CohortEntry): { tone: "good" | "bad" | "pending"; label: string } {
  const mc = e.evaluation?.movement_correct;
  if (mc === true) return { tone: "good", label: "Moved as expected" };
  if (mc === false) return { tone: "bad", label: "Moved against" };
  return { tone: "pending", label: "Pending" };
}

function resolutionVerdict(e: CohortEntry): { tone: "good" | "bad" | "pending"; label: string } {
  if (!e.evaluation?.resolved) return { tone: "pending", label: "Pending resolution" };
  return e.evaluation.resolution_correct
    ? { tone: "good", label: "Resolved correct" }
    : { tone: "bad", label: "Resolved incorrect" };
}

function EntryRow({ entry, view }: { entry: CohortEntry; view: View }) {
  const v = view === "movement" ? movementVerdict(entry) : resolutionVerdict(entry);
  const laterPrice =
    entry.forward.find((f) => f.horizon === "24h")?.price ??
    entry.forward.find((f) => f.horizon === "7d")?.price ??
    entry.forward.find((f) => f.horizon === "1h")?.price ??
    null;

  return (
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-tabular text-[13px] text-arepo-muted">#{entry.rank}</span>
            <span className="font-medium text-arepo-ink">{entry.market_question}</span>
          </div>
          <p className="mt-0.5 text-[13px] text-arepo-muted">
            Selected outcome: {entry.outcome_name}
            {entry.direction ? ` · expected to move ${entry.direction}` : ""}
          </p>
        </div>
        <Verdict tone={v.tone} label={v.label} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-[13px] sm:grid-cols-4">
        <Field label="Entry price" value={formatPrice(entry.entry_price)} />
        <Field
          label={view === "movement" ? "Later price" : "Latest price"}
          value={formatPrice(laterPrice)}
        />
        <Field
          label="Signal strength"
          value={formatPercent(entry.strength, 0)}
        />
        <Field label="Data coverage" value={capitalise(entry.data_quality)} />
      </div>

      <Disclose summary="Why this qualified" className="mt-3">
        <div className="space-y-3 pt-1 text-[14px] leading-relaxed text-arepo-ink2">
          <p>
            This signal cleared the weekly thresholds: valid market status, at least
            limited data coverage, a usable entry price, and a signal strength of{" "}
            {formatPercent(entry.strength, 0)} (confidence {formatPercent(entry.confidence, 0)}).
            {entry.lookback_size
              ? ` It was measured over a lookback of ${entry.lookback_size} observations.`
              : ""}
          </p>
          {entry.component_scores.length > 0 && (
            <div>
              <p className="font-semibold text-arepo-ink">What contributed</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {entry.component_scores.map((c) => (
                  <li key={c.name}>
                    {friendlyComponentName(c.name)}
                    {c.normalized_value !== null
                      ? `: ${formatSignedPercent(c.normalized_value, 0)}`
                      : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {entry.resolution?.resolved && (
            <p>
              Final resolution: {entry.resolution.resolved_outcome ?? "resolved"} (
              {view === "resolution" && entry.evaluation
                ? entry.evaluation.resolution_correct
                  ? "the selected outcome won"
                  : "the selected outcome did not win"
                : "recorded"}
              ).
            </p>
          )}
        </div>
      </Disclose>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-arepo-muted">{label}</div>
      <div className="font-tabular font-medium text-arepo-ink">{value}</div>
    </div>
  );
}

function Portfolio({ detail }: { detail: CohortDetail }) {
  const p = detail.portfolio;
  return (
    <section className="space-y-3">
      <SectionTitle>Hypothetical portfolio</SectionTitle>
      <p className="max-w-reading text-[14px] leading-relaxed text-arepo-muted">
        A simulation only, using a fixed stake per signal. It is not real trading and not
        evidence of future profitability. {p.spread_assumption}
      </p>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Stake per signal" value={money(p.stake_per_signal)} />
        <StatTile label="Total allocated" value={money(p.total_allocated)} />
        <StatTile label="Realised value" value={money(p.realised_value)} />
        <StatTile label="Unrealised value" value={money(p.unrealised_value)} />
        <StatTile label="Pending value" value={money(p.pending_value)} />
        <StatTile
          label="Completed return"
          value={money(p.completed_return)}
          emphasis
        />
      </div>
      <p className="text-[13px] text-arepo-muted">
        {p.completed_positions} completed position(s), {p.pending_positions} still open or
        pending.
      </p>

      <Disclose summary="Show the positions">
        <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-[13px]">
              <thead>
                <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
                  <th className="px-4 py-3 font-semibold">Market</th>
                  <th className="px-4 py-3 font-semibold">Outcome</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Entry</th>
                  <th className="px-4 py-3 font-semibold">Exit</th>
                  <th className="px-4 py-3 font-semibold">Value</th>
                  <th className="px-4 py-3 font-semibold">Return</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-arepo-border font-tabular">
                {p.positions.map((pos) => (
                  <tr key={pos.rank}>
                    <td className="px-4 py-2.5 font-sans text-arepo-ink">
                      {pos.market_question}
                    </td>
                    <td className="px-4 py-2.5 font-sans">{pos.outcome_name}</td>
                    <td className="px-4 py-2.5 font-sans">
                      <Badge tone={pos.status === "completed" ? "good" : "neutral"}>
                        {pos.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">{formatPrice(pos.entry_price)}</td>
                    <td className="px-4 py-2.5">{formatPrice(pos.exit_price)}</td>
                    <td className="px-4 py-2.5">{money(pos.value)}</td>
                    <td className="px-4 py-2.5">{money(pos.pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Disclose>
    </section>
  );
}

function ProvenanceFootnote({ info }: { info: ProvenanceInfo }) {
  return (
    <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
      {info.note}{" "}
      {info.first_prospective_week
        ? `Prospective tracking began in ${info.first_prospective_week}.`
        : "Prospective tracking has not started yet."}{" "}
      Calculation version {info.calculation_version}. See the{" "}
      <Link href="/methodology" className="underline hover:text-arepo-ink">
        methodology
      </Link>{" "}
      for the full evaluation rules.
    </p>
  );
}

function capitalise(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

// ---------------------------------------------------------------------------------------
// Historical reconstructed retrospective (a separate, clearly-labelled analysis mode).
// ---------------------------------------------------------------------------------------
const HISTORICAL_PERIODS = [
  { days: 1, label: "24 hours ago" },
  { days: 3, label: "3 days ago" },
  { days: 7, label: "7 days ago" },
  { days: 14, label: "14 days ago" },
  { days: 30, label: "30 days ago" },
];

const CLOSING_LENSES = [
  { id: "all", label: "All horizons", hours: Infinity },
  { id: "7d", label: "Closed within 7 days", hours: 24 * 7 },
  { id: "3d", label: "Closed within 3 days", hours: 24 * 3 },
  { id: "24h", label: "Closed within 24 hours", hours: 24 },
] as const;

function HistoricalView() {
  const [cutoffStr, setCutoff] = useUrlState("cutoff", "7");
  const [lens, setLens] = useUrlState("closing", "all");
  const days = Number(cutoffStr) || 7;
  const { data, loading, error } = useAsync<HistoricalScreen>(
    () => getHistoricalScreen(days),
    [days]
  );
  const maxHours = CLOSING_LENSES.find((l) => l.id === lens)?.hours ?? Infinity;

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2.5 rounded-card border border-arepo-border bg-arepo-surface2 px-4 py-3 text-[14px] leading-relaxed text-arepo-ink2">
        <span className="mt-0.5 inline-flex flex-none items-center rounded-full bg-arepo-ink/8 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-arepo-ink2">
          Reconstructed analysis
        </span>
        <span>
          This reconstructs the composite anomaly signal at a past cut-off using only the real
          price history up to that moment, then measures what actually happened afterwards. It is
          a research screen, separate from the prospective frozen-weekly track record, and is
          never mixed into it.
        </span>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-arepo-ink2">Cut-off</span>
          <select
            className="select-arepo w-44"
            value={String(days)}
            onChange={(e) => setCutoff(e.target.value)}
          >
            {HISTORICAL_PERIODS.map((p) => (
              <option key={p.days} value={p.days}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
        {/* Closing-soon lens (spec §16): filter the reconstructed rows by how soon they closed
            after the cut-off. Near-close markets are not implied to be better. */}
        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-arepo-ink2">Closing lens</span>
          <select
            className="select-arepo w-56"
            value={lens}
            onChange={(e) => setLens(e.target.value)}
          >
            {CLOSING_LENSES.map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        {loading && (
          <p className="text-[13px] text-arepo-muted">
            Reconstructing from real price history. This can take a moment.
          </p>
        )}
      </div>

      {loading && <ListSkeleton rows={6} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && <HistoricalResult screen={data} maxHours={maxHours} />}

      <ReplayDataStatusSection />
    </div>
  );
}

/** Replay data status (spec §18): what has actually been recorded, and the honest answer to
 * "does leaving the website open increase the sample?" (no - the backend collectors must run). */
function ReplayDataStatusSection() {
  const { data } = useAsync(() => getReplayDataStatus(), []);
  if (!data) return null;
  const rows: [string, string][] = [
    ["Collectors", data.collector_recent ? "Recently active" : "No recent collection"],
    [
      "Last collection",
      data.last_collection_at ? new Date(data.last_collection_at).toLocaleString("en-GB") : "none",
    ],
    ["Snapshot interval", `${Math.round(data.snapshot_interval_seconds / 60)} min (scheduled)`],
    ["Stored snapshots", String(data.microstructure_snapshots_stored)],
    ["Prospective cohorts", String(data.prospective_cohorts)],
    ["Weekly cohorts (all)", String(data.weekly_cohorts_total)],
    [
      "Recorded cut-offs",
      data.oldest_cutoff
        ? `${new Date(data.oldest_cutoff).toLocaleDateString("en-GB")} to ${
            data.newest_cutoff ? new Date(data.newest_cutoff).toLocaleDateString("en-GB") : "?"
          }`
        : "none yet",
    ],
  ];
  return (
    <Disclose summary="Replay data status: does leaving the site open increase the sample?">
      <div className="space-y-3">
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">{data.note}</p>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-arepo-border py-1">
              <dt className="text-[13px] text-arepo-muted">{k}</dt>
              <dd className="text-[13px] font-medium text-arepo-ink2">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </Disclose>
  );
}

function pct(hit: number | null): string {
  return hit === null ? "n/a" : `${Math.round(hit * 100)}%`;
}

/** Arepo vs simple causal baselines over the same reconstructed sample (spec §6). */
function BaselineTable({ comparison }: { comparison: BaselineComparison }) {
  const rows = [
    { key: "arepo", score: comparison.arepo, highlight: true },
    ...Object.entries(comparison.baselines).map(([key, score]) => ({
      key,
      score,
      highlight: false,
    })),
  ];
  return (
    <section className="space-y-2">
      <SectionTitle>Arepo vs simple baselines</SectionTitle>
      <p className="text-[13px] text-arepo-muted">
        Directional correctness over the same reconstructed markets. Markets that stayed flat over
        24 hours are shown separately and excluded from every predictor&apos;s hit rate, so a market
        that did not move is never booked as a directional miss. Any edge must beat these baselines;
        on this sample the differences are not statistically meaningful.
      </p>
      <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-[13px]">
            <thead>
              <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
                <th className="px-4 py-2.5 font-semibold">Method</th>
                <th className="px-4 py-2.5 font-semibold">Correct</th>
                <th className="px-4 py-2.5 font-semibold">Flat</th>
                <th className="px-4 py-2.5 font-semibold">Hit rate</th>
                <th className="px-4 py-2.5 font-semibold">95% interval</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-arepo-border">
              {rows.map(({ key, score, highlight }) => (
                <tr key={key} className={highlight ? "bg-arepo-accentTint/40" : ""}>
                  <td className="px-4 py-2 font-medium text-arepo-ink">{score.name}</td>
                  <td className="px-4 py-2 text-arepo-ink2">
                    {score.correct}/{score.evaluated}
                  </td>
                  <td className="px-4 py-2 font-tabular text-arepo-muted">{score.flat ?? 0}</td>
                  <td className="px-4 py-2 font-tabular text-arepo-ink2">{pct(score.hit_rate)}</td>
                  <td className="px-4 py-2 font-tabular text-arepo-muted">
                    {pct(score.ci95[0])} to {pct(score.ci95[1])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function HistoricalResult({
  screen,
  maxHours = Infinity,
}: {
  screen: HistoricalScreen;
  maxHours?: number;
}) {
  // The closing lens filters which reconstructed rows are shown by their time-to-close at the
  // cut-off; the funnel counts above still describe the full reconstruction (spec §16, §17).
  const shownEntries =
    maxHours === Infinity
      ? screen.entries
      : screen.entries.filter(
          (e) => e.time_remaining_hours != null && e.time_remaining_hours <= maxHours
        );
  if (screen.selected === 0) {
    return (
      <EmptyState
        message={
          "No markets had enough real, moving price history to reconstruct a signal for this " +
          "cut-off. See the limitations below."
        }
      />
    );
  }
  return (
    <div className="space-y-6">
      <p className="max-w-reading text-[16px] leading-relaxed text-arepo-ink">
        {screen.plain_summary}
      </p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatTile label="Signals reconstructed" value={String(screen.selected)} />
        <StatTile label="Moved as expected (24h)" value={String(screen.moved_expected_24h)} />
        <StatTile label="Moved against (24h)" value={String(screen.moved_against_24h)} />
        <StatTile label="Flat (24h)" value={String(screen.moved_flat_24h)} />
        <StatTile label="Not evaluable (24h)" value={String(screen.pending_24h)} />
      </div>
      {/* Reconstruction funnel (spec §6.7): make the small sample transparent, not hidden. */}
      <div className="-mt-2 rounded-card border border-arepo-border bg-arepo-surface2 px-4 py-3 text-[13px] text-arepo-ink2">
        <span className="font-medium text-arepo-ink">How the top five were reconstructed: </span>
        {screen.candidates_total} outcomes existed at the cut-off; {screen.had_price_data} had
        historical price data; {screen.eligible} passed eligibility (enough history, near-mid entry,
        strong enough signal); {screen.directional} received a directional view; top{" "}
        {screen.selected} shown. Signal Lab can show more signals now than Replay reconstructs
        because historical order books, wallet and trade-flow history do not exist for a past
        cut-off, some markets did not exist then, and current metadata cannot be used
        retrospectively.
      </div>

      {/* Inconclusive banner: a tiny sample is never presented as proof (spec §6). */}
      {screen.sample_verdict === "inconclusive" && (
        <div className="flex items-start gap-2 rounded-card border border-arepo-warn/30 bg-arepo-warn/10 px-4 py-3 text-[13px] leading-relaxed text-arepo-warnText">
          <span aria-hidden="true">⚠</span>
          <span>
            This sample is too small to be evidence of skill. A hit rate on a handful of markets is
            statistically inconclusive (its 95% interval spans most of 0 to 100%). Treat it as an
            illustration of the method, not proof that Arepo has an edge.
          </span>
        </div>
      )}

      {screen.baseline_comparison && <BaselineTable comparison={screen.baseline_comparison} />}

      <section className="space-y-3">
        <SectionTitle>Reconstructed signals</SectionTitle>
        <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-[13px]">
              <thead>
                <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
                  <th className="px-4 py-3 font-semibold">Market</th>
                  <th className="px-4 py-3 font-semibold">Signal</th>
                  <th className="px-4 py-3 font-semibold">Strength</th>
                  <th className="px-4 py-3 font-semibold">Entry</th>
                  <th className="px-4 py-3 font-semibold">24h move</th>
                  <th className="px-4 py-3 font-semibold">Outcome (24h)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-arepo-border">
                {shownEntries.map((e) => (
                  <HistoricalRow key={`${e.market_id}-${e.token_id}`} entry={e} />
                ))}
              </tbody>
            </table>
          </div>
          {shownEntries.length === 0 && (
            <p className="px-4 py-3 text-[13px] text-arepo-muted">
              None of the {screen.selected} reconstructed opportunities closed within this window.
              Try a longer closing lens.
            </p>
          )}
        </div>
      </section>

      <Disclose summary="Assumptions and limitations">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wide text-arepo-ink">
              Assumptions
            </p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-arepo-muted">
              {screen.assumptions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wide text-arepo-ink">
              Limitations
            </p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-arepo-muted">
              {screen.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </div>
        </div>
      </Disclose>
    </div>
  );
}

function HistoricalRow({ entry }: { entry: HistoricalEntry }) {
  const move24 = entry.forward.find((f) => f.horizon === "24h")?.movement ?? null;
  // Flat-aware verdict (spec §10/§11): a market that did not move is shown as "Flat", never as a
  // red directional miss. Falls back to the boolean for older payloads without outcome_24h.
  const outcome =
    entry.outcome_24h ??
    (entry.direction_correct_24h === true
      ? "correct"
      : entry.direction_correct_24h === false
        ? "incorrect"
        : "pending");
  const verdict =
    outcome === "correct"
      ? { tone: "good" as const, label: "As expected" }
      : outcome === "incorrect"
        ? { tone: "bad" as const, label: "Against" }
        : outcome === "flat"
          ? { tone: "pending" as const, label: "Flat (no move)" }
          : { tone: "pending" as const, label: "Not evaluable" };
  return (
    <tr>
      <td className="px-4 py-2.5">
        <Link
          href={`/markets/${encodeURIComponent(entry.market_id)}?mode=live`}
          className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
        >
          {entry.market_question}
        </Link>
        <div className="text-[12px] text-arepo-muted">{entry.outcome_name}</div>
        {/* Everything below is AS IT WAS at the cut-off (spec §14): Research Priority and
            confidence at the time, and the scheduled close known then. */}
        <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] text-arepo-muted">
          <span>RP {entry.research_priority} at cut-off</span>
          <span>·</span>
          <span>confidence {formatPercent(entry.confidence, 0)}</span>
          {entry.close_at && (
            <>
              <span>·</span>
              <span>closes {new Date(entry.close_at).toLocaleDateString("en-GB")}</span>
            </>
          )}
          {entry.time_remaining_hours != null && (
            <>
              <span>·</span>
              <span>
                {entry.time_remaining_hours < 48
                  ? `${Math.round(entry.time_remaining_hours)}h`
                  : `${Math.round(entry.time_remaining_hours / 24)}d`}{" "}
                left at cut-off
              </span>
            </>
          )}
        </div>
      </td>
      <td className="px-4 py-2.5 font-tabular">
        {entry.direction === "up" && <span className="text-arepo-pos">Up</span>}
        {entry.direction === "down" && <span className="text-arepo-neg">Down</span>}
        {!entry.direction && <span className="text-arepo-muted">n/a</span>}
      </td>
      <td className="px-4 py-2.5 font-tabular">{formatPercent(entry.strength, 0)}</td>
      <td className="px-4 py-2.5 font-tabular">{formatPrice(entry.entry_price)}</td>
      <td className="px-4 py-2.5 font-tabular">
        {move24 === null ? "n/a" : formatSignedPercent(move24, 1)}
      </td>
      <td className="px-4 py-2.5">
        <Verdict tone={verdict.tone} label={verdict.label} />
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------------------
// Preserved deterministic signal backtest (a demonstration dataset, not live markets).
// ---------------------------------------------------------------------------------------
const HORIZON_OPTIONS = [5, 10, 20];
const DEBOUNCE_MS = 300;

function BacktestDemo() {
  const [strengthInput, setStrengthInput] = useState(0.6);
  const [moveInput, setMoveInput] = useState(0.03);
  const [horizon, setHorizon] = useState(5);
  const [strengthThreshold, setStrengthThreshold] = useState(strengthInput);
  const [moveThreshold, setMoveThreshold] = useState(moveInput);

  useEffect(() => {
    const t = setTimeout(() => setStrengthThreshold(strengthInput), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [strengthInput]);
  useEffect(() => {
    const t = setTimeout(() => setMoveThreshold(moveInput), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [moveInput]);

  const { data, loading, error } = useAsync(
    () => getBacktest({ strength_threshold: strengthThreshold, move_threshold: moveThreshold, horizon }),
    [strengthThreshold, moveThreshold, horizon]
  );

  return (
    <div className="space-y-5 pt-2">
      <p className="max-w-reading text-[14px] leading-relaxed text-arepo-muted">
        This runs against a fixed sample dataset, not live markets, with a look-ahead-safe
        window. It demonstrates how to evaluate a signal. It is not evidence of predictive
        advantage and is separate from the prospective cohorts above.
      </p>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div className="space-y-2">
          <label htmlFor="bt-strength" className="flex items-center justify-between text-[13px] font-medium text-arepo-ink">
            <span className="flex items-center gap-1">
              Minimum signal strength
              <MetricHelp metric="threshold" showTerm={false} />
            </span>
            <span className="font-tabular text-arepo-accentActive">{formatPercent(strengthInput, 0)}</span>
          </label>
          <input id="bt-strength" type="range" min={0} max={1} step={0.01} value={strengthInput}
            onChange={(e) => setStrengthInput(Number(e.target.value))} className="slider-arepo" />
        </div>
        <div className="space-y-2">
          <label htmlFor="bt-move" className="flex items-center justify-between text-[13px] font-medium text-arepo-ink">
            <span className="flex items-center gap-1">
              Required later movement
              <MetricHelp metric="movement" showTerm={false} />
            </span>
            <span className="font-tabular text-arepo-accentActive">{formatPercent(moveInput, 1)}</span>
          </label>
          <input id="bt-move" type="range" min={0} max={0.1} step={0.005} value={moveInput}
            onChange={(e) => setMoveInput(Number(e.target.value))} className="slider-arepo" />
        </div>
        <div className="space-y-2">
          <label htmlFor="bt-horizon" className="flex items-center gap-1 text-[13px] font-medium text-arepo-ink">
            How far ahead to check
            <MetricHelp metric="evaluation-horizon" showTerm={false} />
          </label>
          <select id="bt-horizon" className="select-arepo" value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}>
            {HORIZON_OPTIONS.map((h) => (
              <option key={h} value={h}>{h} frames</option>
            ))}
          </select>
        </div>
      </div>

      {loading && <ListSkeleton rows={4} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <StatTile label="Sample size" value={String(data.sample_size)} />
            <StatTile label="Evaluated" value={String(data.evaluated)} />
            <StatTile label="Hit rate" value={formatPercent(data.hit_rate)}
              help={<MetricHelp metric="hit-rate" showTerm={false} />} />
            <StatTile label="False positive rate" value={formatPercent(data.false_positive_rate)}
              help={<MetricHelp metric="false-positive-rate" showTerm={false} />} />
            <StatTile label="Average forward move" value={formatSignedPercent(data.avg_forward_move_directional)}
              help={<MetricHelp metric="average-forward-move" showTerm={false} />} />
            <StatTile label="Missing observations" value={String(data.missing_observations)} />
          </div>
          <Disclose summary="Show the tested signals">
            <BacktestTable events={data.events} />
          </Disclose>
        </>
      )}
    </div>
  );
}

function BacktestTable({ events }: { events: BacktestEvent[] }) {
  return (
    <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-[13px]">
          <thead>
            <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
              <th className="px-4 py-3 font-semibold">Market</th>
              <th className="px-4 py-3 font-semibold">Strength</th>
              <th className="px-4 py-3 font-semibold">Z-score</th>
              <th className="px-4 py-3 font-semibold">Direction</th>
              <th className="px-4 py-3 font-semibold">Entry</th>
              <th className="px-4 py-3 font-semibold">Forward</th>
              <th className="px-4 py-3 font-semibold">Followed through</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-arepo-border font-tabular">
            {events.map((ev, i) => (
              <tr key={`${ev.market_id}-${ev.token_id}-${i}`}>
                <td className="px-4 py-2.5 font-sans text-arepo-ink">{ev.market_id}</td>
                <td className="px-4 py-2.5">{formatPercent(ev.strength, 0)}</td>
                <td className="px-4 py-2.5">{formatZScore(ev.zscore)}</td>
                <td className="px-4 py-2.5 font-sans">
                  {ev.direction === "up" && <span className="text-arepo-pos">Up</span>}
                  {ev.direction === "down" && <span className="text-arepo-neg">Down</span>}
                  {!ev.direction && <span className="text-arepo-muted">n/a</span>}
                </td>
                <td className="px-4 py-2.5">{formatPrice(ev.entry_price)}</td>
                <td className="px-4 py-2.5">{formatPrice(ev.forward_price)}</td>
                <td className="px-4 py-2.5 font-sans">
                  {ev.followed_through === null ? (
                    <span className="text-arepo-muted">n/a</span>
                  ) : (
                    <Badge tone={ev.followed_through ? "good" : "neutral"}>
                      {ev.followed_through ? "Yes" : "No"}
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center font-sans text-arepo-muted">
                  No events matched these thresholds.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
