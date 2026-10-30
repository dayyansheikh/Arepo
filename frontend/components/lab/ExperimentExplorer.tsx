"use client";

import { useMemo, useState } from "react";
import {
  EMPTY_FILTER,
  facetCounts,
  filterExperiments,
  hideEffect,
  NO_VERDICT,
  sortExperiments,
  STAGE_META,
  verdictKey,
  verdictMeta,
  type ExperimentFilter,
} from "@/lib/lab/model";
import { STAGES, type Experiment, type Stage } from "@/lib/lab/types";
import { StageTrack, StageTrail } from "./Candidates";
import { Pill, Quiet } from "./primitives";

const PAGE = 10;
const VERDICT_ORDER = ["replicated", "advanced", "failed_costs", "not_detected", "not_testable", "pending", NO_VERDICT];

function Chip({
  active,
  onClick,
  children,
  count,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`focus-ring inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-[12.5px] font-medium transition-colors ${
        active
          ? "border-arepo-ink bg-arepo-ink text-white"
          : "border-arepo-border bg-arepo-surface text-arepo-ink2 hover:border-arepo-borderStrong hover:bg-arepo-surface2"
      }`}
    >
      {children}
      {typeof count === "number" ? (
        <span className={`font-tabular text-[11px] ${active ? "text-white/70" : "text-arepo-muted"}`}>{count}</span>
      ) : null}
    </button>
  );
}

function toggle(list: string[], v: string): string[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function ChipRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4" role="group" aria-label={label}>
      <span className="w-16 flex-none pt-1.5 text-[11.5px] font-semibold uppercase tracking-wider text-arepo-muted">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}

function Row({ exp, open, onToggle }: { exp: Experiment; open: boolean; onToggle: () => void }) {
  const v = verdictMeta(exp.verdict);
  const stageLabel = exp.stage && exp.stage in STAGE_META ? STAGE_META[exp.stage as Stage].label : exp.stage ?? "–";
  const panelId = `exp-${exp.id}-panel`;
  return (
    <li className="border-b border-arepo-border last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
        className="focus-ring grid w-full grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1 px-1 py-3 text-left transition-colors hover:bg-arepo-surface2/70 sm:grid-cols-[5.5rem_1fr_auto_8rem_auto] sm:px-3"
      >
        <span className="font-mono text-[11.5px] text-arepo-muted">{exp.id}</span>
        <span className="min-w-0 truncate text-[14px] font-medium text-arepo-ink">
          {exp.candidate ? (
            <span className="mr-1.5 inline-block h-1.5 w-1.5 -translate-y-0.5 rounded-full bg-arepo-accent" aria-label="Leading candidate" />
          ) : null}
          {exp.title ?? exp.id}
        </span>
        <span className="hidden sm:block" title={stageLabel}>
          <StageTrack exp={exp} compact />
        </span>
        <span className="hidden justify-self-start sm:block">
          <Pill tone={v.tone} title={v.help}>
            {v.label}
          </Pill>
        </span>
        <svg
          aria-hidden="true"
          viewBox="0 0 12 12"
          className={`h-3 w-3 text-arepo-muted transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
        <span className="col-span-3 flex flex-wrap items-center gap-2 sm:hidden">
          <span className="text-[12px] text-arepo-muted">{stageLabel}</span>
          <Pill tone={v.tone}>{v.label}</Pill>
        </span>
      </button>
      {open ? (
        <div id={panelId} className="lab-rise px-1 pb-4 sm:px-3 sm:pl-[6.25rem]">
          {exp.plain ? <p className="max-w-reading text-[14px] leading-relaxed text-arepo-ink2">{exp.plain}</p> : null}
          <div className="mt-3">
            <StageTrail exp={exp} />
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-[12.5px] sm:grid-cols-4">
            <Meta label="Stage" value={stageLabel} />
            <Meta label="Verdict" value={v.label} hint={v.help} />
            <Meta label="Batch" value={exp.batch} />
            <Meta label="Family" value={exp.family?.replace(/_/g, " ")} />
            <Meta label="Status" value={exp.status} />
            <Meta
              label="Effect"
              value={
                hideEffect(exp)
                  ? "Hidden until the registered analysis"
                  : exp.effect?.label
                    ? `${exp.effect.label}${exp.effect.note ? ` (${exp.effect.note})` : ""}`
                    : undefined
              }
            />
            <Meta label="Next" value={exp.next ?? undefined} />
          </dl>
        </div>
      ) : null}
    </li>
  );
}

function Meta({ label, value, hint }: { label: string; value?: string | null; hint?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-arepo-muted">{label}</dt>
      <dd className="text-arepo-ink" title={hint}>
        {value || "–"}
      </dd>
    </div>
  );
}

export function ExperimentExplorer({ experiments }: { experiments: Experiment[] }) {
  const [filter, setFilter] = useState<ExperimentFilter>(EMPTY_FILTER);
  const [openId, setOpenId] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const stageFacets = useMemo(() => facetCounts(experiments, (e) => e.stage, STAGES), [experiments]);
  const verdictFacets = useMemo(() => facetCounts(experiments, verdictKey, VERDICT_ORDER), [experiments]);
  const batchFacets = useMemo(
    () =>
      facetCounts(experiments, (e) => e.batch).sort((a, b) =>
        a.value.localeCompare(b.value, undefined, { numeric: true }),
      ),
    [experiments],
  );
  const results = useMemo(() => sortExperiments(filterExperiments(experiments, filter)), [experiments, filter]);
  const visible = showAll ? results : results.slice(0, PAGE);
  const filtered =
    filter.stages.length + filter.verdicts.length + filter.batches.length > 0 || filter.query.trim() !== "";

  if (!experiments.length) return <Quiet>No experiments in the latest snapshot.</Quiet>;

  return (
    <div className="panel p-4 sm:p-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="relative min-w-0 flex-1 basis-60">
            <span className="sr-only">Search experiments</span>
            <svg aria-hidden="true" viewBox="0 0 16 16" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-arepo-muted">
              <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              value={filter.query}
              onChange={(e) => setFilter((f) => ({ ...f, query: e.target.value }))}
              placeholder="Search by name, id, family…"
              className="w-full rounded-control border border-arepo-borderStrong bg-arepo-surface py-2 pl-9 pr-3 text-[14px] text-arepo-ink placeholder:text-arepo-muted"
            />
          </label>
          <p className="font-tabular text-[13px] text-arepo-muted" aria-live="polite">
            {results.length} of {experiments.length}
          </p>
          {filtered ? (
            <button type="button" className="btn btn-ghost !px-2 !py-1 text-[12.5px]" onClick={() => setFilter(EMPTY_FILTER)}>
              Clear filters
            </button>
          ) : null}
        </div>

        <ChipRow label="Stage">
          {stageFacets.map((f) => (
            <Chip
              key={f.value}
              count={f.count}
              active={filter.stages.includes(f.value)}
              onClick={() => setFilter((x) => ({ ...x, stages: toggle(x.stages, f.value) }))}
            >
              {f.value in STAGE_META ? STAGE_META[f.value as Stage].label : f.value}
            </Chip>
          ))}
        </ChipRow>
        <ChipRow label="Verdict">
          {verdictFacets.map((f) => (
            <Chip
              key={f.value}
              count={f.count}
              active={filter.verdicts.includes(f.value)}
              onClick={() => setFilter((x) => ({ ...x, verdicts: toggle(x.verdicts, f.value) }))}
            >
              {f.value === NO_VERDICT ? "No verdict yet" : verdictMeta(f.value).label}
            </Chip>
          ))}
        </ChipRow>
        {batchFacets.length > 1 ? (
          <ChipRow label="Batch">
            {batchFacets.map((f) => (
              <Chip
                key={f.value}
                count={f.count}
                active={filter.batches.includes(f.value)}
                onClick={() => setFilter((x) => ({ ...x, batches: toggle(x.batches, f.value) }))}
              >
                {f.value}
              </Chip>
            ))}
          </ChipRow>
        ) : null}
      </div>

      <ul className="mt-5 border-t border-arepo-border" aria-label="Experiments">
        {visible.map((e) => (
          <Row key={e.id} exp={e} open={openId === e.id} onToggle={() => setOpenId((id) => (id === e.id ? null : e.id))} />
        ))}
      </ul>
      {!results.length ? <p className="py-6 text-center text-[13.5px] text-arepo-muted">Nothing matches these filters.</p> : null}
      {results.length > PAGE ? (
        <div className="mt-3 text-center">
          <button type="button" className="btn btn-secondary text-[13px]" onClick={() => setShowAll((s) => !s)}>
            {showAll ? "Show fewer" : `Show all ${results.length}`}
          </button>
        </div>
      ) : null}
    </div>
  );
}
