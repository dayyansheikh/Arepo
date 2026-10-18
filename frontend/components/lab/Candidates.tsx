"use client";

import {
  countdownLabel,
  daysUntil,
  hasFailed,
  hideEffect,
  rankCandidates,
  shortDate,
  STAGE_META,
  stageIndex,
  stageTrail,
  timeProgress,
  verdictMeta,
  type TrailMark,
} from "@/lib/lab/model";
import { STAGES, type Experiment, type LiveTest } from "@/lib/lab/types";
import { fmtCount, Pill, ProgressBar, Quiet } from "./primitives";

const MARK_CLASS: Record<TrailMark, string> = {
  pass: "bg-arepo-accent/45",
  pending: "bg-arepo-accent",
  fail: "bg-arepo-warn",
  none: "bg-arepo-surface2",
};

/**
 * Seven small segments, one per stage: passed (soft red), current/pending (red), failed (amber),
 * not reached (empty). Drawn from the experiment's own stage_results when present.
 */
export function StageTrack({ exp, compact = false }: { exp: Experiment; compact?: boolean }) {
  const trail = stageTrail(exp);
  const idx = stageIndex(exp.stage);
  const failedAt = trail.find((t) => t.mark === "fail");
  const label = idx >= 0 ? STAGE_META[STAGES[idx]].label : "Unknown stage";
  return (
    <div>
      <div
        className={`flex ${compact ? "gap-[3px]" : "gap-1"}`}
        role="img"
        aria-label={`Stage ${idx + 1} of ${STAGES.length}: ${label}${failedAt ? `, failed at ${STAGE_META[failedAt.stage].label}` : ""}`}
      >
        {trail.map((t) => (
          <span key={t.stage} className={`${compact ? "h-1.5 w-2.5" : "h-1.5 flex-1"} rounded-full ${MARK_CLASS[t.mark]}`} />
        ))}
      </div>
      {!compact ? (
        <p className="mt-1.5 text-[12px] text-arepo-muted">
          Stage {idx + 1} of {STAGES.length} · <span className="text-arepo-ink2">{label}</span>
          {failedAt ? <span className="text-arepo-warnText"> · failed at {STAGE_META[failedAt.stage].label.toLowerCase()}</span> : null}
        </p>
      ) : null}
    </div>
  );
}

const TRAIL_GLYPH: Record<TrailMark, { glyph: string; cls: string; word: string }> = {
  pass: { glyph: "✓", cls: "border-arepo-pos/40 bg-arepo-pos/10 text-arepo-pos", word: "passed" },
  fail: { glyph: "✕", cls: "border-arepo-warn/50 bg-arepo-warn/15 text-arepo-warnText", word: "failed" },
  pending: { glyph: "•", cls: "border-arepo-accentBorder bg-arepo-accentTint text-arepo-accentActive", word: "in progress" },
  none: { glyph: "", cls: "border-arepo-border bg-arepo-surface text-arepo-muted", word: "not reached" },
};

/** Expanded-row trail: each stage with a tick, cross, dot or nothing, plus the stage name. */
export function StageTrail({ exp }: { exp: Experiment }) {
  const trail = stageTrail(exp);
  return (
    <ol className="flex flex-wrap items-center gap-x-1 gap-y-2" aria-label="Stage results">
      {trail.map((t, i) => {
        const g = TRAIL_GLYPH[t.mark];
        return (
          <li key={t.stage} className="flex items-center gap-1">
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11.5px] ${g.cls} ${t.mark === "none" ? "opacity-70" : ""}`}
              aria-label={`${STAGE_META[t.stage].label}: ${g.word}`}
            >
              {g.glyph ? <span aria-hidden="true" className="font-semibold">{g.glyph}</span> : null}
              <span aria-hidden="true">{STAGE_META[t.stage].label}</span>
            </span>
            {i < trail.length - 1 ? <span aria-hidden="true" className="h-px w-2 bg-arepo-border" /> : null}
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Collection progress for a live test, counts and dates only. With a count target: a count bar.
 * Without one: time elapsed towards the registered analysis date (when the start is known), or
 * a plain countdown.
 */
export function LiveProgress({ live, nowMs }: { live: LiveTest; nowMs: number }) {
  const days = daysUntil(live.analysis_after, nowMs);
  const countdown = countdownLabel(days);
  const frac = live.target ? null : timeProgress(live.started_at, live.analysis_after, nowMs);
  return (
    <div>
      <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-2 text-[12px]">
        <span className="text-arepo-muted">
          {typeof live.collected === "number" ? (
            <>
              <span className="font-tabular text-arepo-ink2">{fmtCount(live.collected)}</span>
              {live.target ? ` / ${fmtCount(live.target)}` : ""} {live.unit ?? "collected"}
            </>
          ) : (
            "Collecting"
          )}
        </span>
        {live.analysis_after ? (
          <span className="text-arepo-muted">
            Analysis {shortDate(live.analysis_after)}
            {countdown ? <span className="text-arepo-ink2"> · {countdown}</span> : null}
          </span>
        ) : null}
      </div>
      {live.target && typeof live.collected === "number" ? (
        <ProgressBar value={live.collected} max={live.target} tone="neutral" label={`${live.title ?? live.id}: ${live.collected} of ${live.target} collected`} />
      ) : frac != null ? (
        <ProgressBar
          value={Math.round(frac * 100)}
          max={100}
          tone="neutral"
          label={`${live.title ?? live.id}: ${Math.round(frac * 100)}% of the time to the analysis date has passed`}
        />
      ) : null}
    </div>
  );
}

function CandidateCard({ exp, live, nowMs }: { exp: Experiment; live?: LiveTest; nowMs: number }) {
  const v = verdictMeta(exp.verdict);
  const days = daysUntil(exp.next_date, nowMs);
  const countdown = countdownLabel(days);
  const showEffect = !hideEffect(exp) && exp.effect?.label;
  const failed = hasFailed(exp);
  return (
    <article
      id={`cand-${encodeURIComponent(exp.id)}`}
      className={`flex scroll-mt-28 flex-col rounded-card border p-5 transition-shadow target:ring-2 target:ring-arepo-accentBorder ${
        failed
          ? "border-dashed border-arepo-borderStrong bg-arepo-surface2/60"
          : "border-arepo-border bg-arepo-surface hover:shadow-arepo-hover"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-[11.5px] text-arepo-muted">{exp.id}</span>
        <Pill tone={v.tone} title={v.help}>
          {v.label}
        </Pill>
      </div>
      <h3 className={`mt-2 text-[17px] font-semibold leading-snug ${failed ? "text-arepo-ink2" : "text-arepo-ink"}`}>
        {exp.title ?? exp.id}
      </h3>
      {exp.plain ? <p className="mt-1.5 text-[13.5px] leading-relaxed text-arepo-ink2">{exp.plain}</p> : null}

      <div className="mt-4">
        <StageTrack exp={exp} />
      </div>

      {hideEffect(exp) ? (
        <div className="mt-4 rounded-control bg-arepo-surface2 px-3 py-2.5">
          {live ? <LiveProgress live={live} nowMs={nowMs} /> : null}
          <p className="mt-1.5 text-[11.5px] leading-snug text-arepo-muted">
            Live test: counts only. Nobody looks at results before the registered analysis.
          </p>
        </div>
      ) : showEffect ? (
        <p className="mt-4 text-[13px] text-arepo-ink2">
          <span className="font-tabular font-semibold text-arepo-ink">{exp.effect?.label}</span>
          {exp.effect?.note ? <span className="text-arepo-muted"> {exp.effect.note}</span> : null}
        </p>
      ) : null}

      <div className="mt-auto pt-4">
        {exp.next ? (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-arepo-border pt-3 text-[12.5px]">
            <span className="text-arepo-ink2">
              <span className="text-arepo-muted">Next · </span>
              {exp.next}
            </span>
            {countdown ? (
              <span
                className="font-tabular rounded-full bg-arepo-surface2 px-2 py-0.5 text-[11.5px] font-semibold text-arepo-ink2"
                title={shortDate(exp.next_date)}
              >
                {countdown}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function Candidates({
  experiments,
  liveTests,
  nowMs,
}: {
  experiments: Experiment[];
  liveTests: LiveTest[];
  nowMs: number;
}) {
  const cands = rankCandidates(experiments).slice(0, 5);
  if (!cands.length) return <Quiet>No leading candidates in the latest snapshot.</Quiet>;
  const liveById = new Map(liveTests.map((l) => [l.id, l]));
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {cands.map((e) => (
        <CandidateCard key={e.id} exp={e} live={liveById.get(e.id)} nowMs={nowMs} />
      ))}
    </div>
  );
}
