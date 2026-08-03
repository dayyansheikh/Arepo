"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import {
  getBacktest,
  getCohort,
  getCohortProvenance,
  getCohortWeeks,
  getHistoricalScreen,
} from "@/lib/api";
import type {
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
  const [mode, setMode] = useState<"prospective" | "historical">("prospective");

  return (
    <div className="space-y-8">
      <PageHeader
        title="Replay"
        lead="If Arepo had selected these signals at the time, what happened afterwards? The prospective track record freezes each week's signals and tracks them forward with no hindsight. A separate historical analysis reconstructs signals over past price data."
      />

      <DisclaimerBanner>
        Replay is a research record, not trading advice, and past behaviour does not predict
        future results.
      </DisclaimerBanner>

      {/* Prospective (real, frozen weekly) vs Historical (reconstructed) analysis. */}
      <div
        className="inline-flex rounded-control border border-arepo-border bg-arepo-surface p-0.5"
        role="tablist"
        aria-label="Replay mode"
      >
        {(
          [
            ["prospective", "Prospective cohorts"],
            ["historical", "Historical analysis"],
          ] as ["prospective" | "historical", string][]
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
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Signals selected" value={String(s.selected)} />
          <StatTile label="Moved as expected" value={String(s.moved_expected)} />
          <StatTile label="Moved against" value={String(s.moved_against)} />
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
  { days: 7, label: "7 days ago" },
  { days: 14, label: "14 days ago" },
  { days: 30, label: "30 days ago" },
];

function HistoricalView() {
  const [days, setDays] = useState(7);
  const { data, loading, error } = useAsync<HistoricalScreen>(
    () => getHistoricalScreen(days),
    [days]
  );

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
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            {HISTORICAL_PERIODS.map((p) => (
              <option key={p.days} value={p.days}>
                {p.label}
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
      {!loading && data && <HistoricalResult screen={data} />}
    </div>
  );
}

function HistoricalResult({ screen }: { screen: HistoricalScreen }) {
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

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Signals reconstructed" value={String(screen.selected)} />
        <StatTile label="Moved as expected (24h)" value={String(screen.moved_expected_24h)} />
        <StatTile label="Moved against (24h)" value={String(screen.moved_against_24h)} />
        <StatTile label="Not evaluable (24h)" value={String(screen.pending_24h)} />
      </div>
      <p className="-mt-4 text-[13px] text-arepo-muted">
        Considered {screen.universe_considered} outcomes; {screen.eligible} had enough history
        and a strong enough signal to rank. A move in the signalled direction is not a claim of
        profitability.
      </p>

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
                {screen.entries.map((e) => (
                  <HistoricalRow key={`${e.market_id}-${e.token_id}`} entry={e} />
                ))}
              </tbody>
            </table>
          </div>
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
  const verdict =
    entry.direction_correct_24h === true
      ? { tone: "good" as const, label: "As expected" }
      : entry.direction_correct_24h === false
        ? { tone: "bad" as const, label: "Against" }
        : { tone: "pending" as const, label: "Not evaluable" };
  return (
    <tr>
      <td className="px-4 py-2.5">
        <Link
          href={`/markets/${encodeURIComponent(entry.market_id)}`}
          className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
        >
          {entry.market_question}
        </Link>
        <div className="text-[12px] text-arepo-muted">{entry.outcome_name}</div>
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
