"use client";

import { useId } from "react";
import { hasFailed, type PipelineStage } from "@/lib/lab/model";
import type { Experiment } from "@/lib/lab/types";
import { Dot, fmtCount } from "./primitives";

// The track warms from a neutral stone to the Arepo red tint towards the confirmed stage. It has a
// constant thickness on purpose: stage counts are not a strict funnel (they need not shrink), so
// the diagram must not imply one.
const FROM = [0xe9, 0xe5, 0xdf];
const TO = [0xf7, 0xd2, 0xd2];
function stageColor(i: number, n: number): string {
  const t = n > 1 ? i / (n - 1) : 0;
  const c = FROM.map((a, k) => Math.round(a + (TO[k] - a) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

function horizontalPath(a: number, b: number): string {
  const t0 = 50 - a / 2;
  const t1 = 50 - b / 2;
  const b0 = 50 + a / 2;
  const b1 = 50 + b / 2;
  return `M0,${t0} C50,${t0} 50,${t1} 100,${t1} L100,${b1} C50,${b1} 50,${b0} 0,${b0} Z`;
}

function verticalPath(a: number, b: number): string {
  const l0 = 50 - a / 2;
  const l1 = 50 - b / 2;
  const r0 = 50 + a / 2;
  const r1 = 50 + b / 2;
  return `M${l0},0 C${l0},50 ${l1},50 ${l1},100 L${r1},100 C${r1},50 ${r0},50 ${r0},0 Z`;
}

function Segment({
  orientation,
  from,
  to,
  colorA,
  colorB,
  gid,
}: {
  orientation: "h" | "v";
  from: number;
  to: number;
  colorA: string;
  colorB: string;
  gid: string;
}) {
  const h = orientation === "h";
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="pointer-events-none absolute overflow-visible"
      style={
        h
          ? { left: "50%", top: 0, width: "100%", height: "100%" }
          : { left: 0, top: 22, width: "100%", height: "100%" }
      }
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2={h ? "1" : "0"} y2={h ? "0" : "1"}>
          <stop offset="0%" stopColor={colorA} />
          <stop offset="100%" stopColor={colorB} />
        </linearGradient>
      </defs>
      <path d={h ? horizontalPath(from, to) : verticalPath(from, to)} fill={`url(#${gid})`} />
      {/* A slow dotted current along the centre line: the pipeline is live. */}
      <line
        x1={h ? 0 : 50}
        y1={h ? 50 : 0}
        x2={h ? 100 : 50}
        y2={h ? 50 : 100}
        stroke="#ffffff"
        strokeOpacity={0.9}
        strokeWidth={1.5}
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
        className="lab-flow"
      />
    </svg>
  );
}

/** A small chevron between two stages: the gate an idea must pass to move on. */
function Gate({ orientation }: { orientation: "h" | "v" }) {
  const h = orientation === "h";
  return (
    <span
      aria-hidden="true"
      className="pointer-events-none absolute z-[5] flex h-5 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-arepo-surface text-arepo-muted shadow-arepo-sm ring-1 ring-arepo-border"
      style={h ? { left: "100%", top: "50%" } : { left: "50%", top: "calc(50% + 22px)" }}
    >
      <svg viewBox="0 0 10 10" className={`h-2.5 w-2.5 ${h ? "" : "rotate-90"}`}>
        <path d="M3.5 2l3 3-3 3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

function CandidateChip({ exp }: { exp: Experiment }) {
  const failed = hasFailed(exp);
  const live = exp.stage === "live_test" && !failed;
  return (
    <a
      href={`#cand-${encodeURIComponent(exp.id)}`}
      className={`focus-ring group flex items-start gap-1.5 rounded-lg border px-2 py-1 text-left text-[12.5px] leading-snug transition-colors ${
        failed
          ? "border-dashed border-arepo-borderStrong bg-arepo-surface2 text-arepo-muted"
          : "border-arepo-border bg-arepo-surface text-arepo-ink shadow-arepo-sm hover:border-arepo-accentBorder"
      }`}
      title={`${exp.title ?? exp.id}${failed ? ": failed this gate" : ""}`}
    >
      <span className="mt-[5px] flex-none">
        {failed ? (
          <svg aria-hidden="true" viewBox="0 0 8 8" className="h-2 w-2 text-arepo-warn">
            <path d="M1 1l6 6M7 1L1 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        ) : (
          <Dot tone="accent" pulse={live} />
        )}
      </span>
      <span className="min-w-0">
        <span className={`font-medium ${failed ? "line-through decoration-arepo-borderStrong" : ""}`}>{exp.title ?? exp.id}</span>
        {failed ? <span className="block text-[11px] text-arepo-warnText">failed here</span> : null}
        {live ? <span className="block text-[11px] text-arepo-muted">collecting</span> : null}
      </span>
    </a>
  );
}

function Node({ stage, last, size }: { stage: PipelineStage; last: boolean; size: number }) {
  const hasCands = stage.candidates.some((c) => !hasFailed(c));
  return (
    <div
      className={`relative z-10 flex items-center justify-center rounded-full bg-arepo-surface shadow-arepo-sm ${
        last
          ? "border-[1.5px] border-dashed border-arepo-accent/60"
          : hasCands
            ? "border-[1.5px] border-arepo-accent/70"
            : "border border-arepo-borderStrong"
      }`}
      style={{ width: size, height: size }}
    >
      <span
        className={`font-display font-tabular font-semibold leading-none ${
          last ? "text-arepo-accentActive" : "text-arepo-ink"
        }`}
        style={{ fontSize: size > 50 ? 19 : 16 }}
      >
        {fmtCount(stage.count)}
      </span>
    </div>
  );
}

/**
 * Hero diagram: the seven gates an idea must pass to become a confirmed edge. Counts sit in the
 * nodes on a constant-width track (not a narrowing funnel: counts need not be monotone); leading
 * candidates are drawn as markers in the stage they have reached, failed ones muted and crossed. Distance to an edge is the stage reached,
 * never a probability. Horizontal from md up, vertical on phones.
 */
export function EdgePipeline({ stages }: { stages: PipelineStage[] }) {
  const uid = useId().replace(/[:]/g, "");
  const n = stages.length;
  const HW = 30; // track thickness, % of rail height
  const VW = 40; // track thickness, % of rail width
  const summary = stages
    .map((s) => `${s.label}: ${fmtCount(s.count)}${s.unit ? ` ${s.unit}` : ""}${s.candidates.length ? ` (candidates: ${s.candidates.map((c) => c.title ?? c.id).join(", ")})` : ""}`)
    .join("; ");

  return (
    <figure className="m-0">
      <figcaption className="sr-only">Edge pipeline. {summary}.</figcaption>

      {/* Desktop / tablet: left to right. */}
      <ol aria-label="Edge pipeline stages" className="hidden grid-cols-7 md:grid">
        {stages.map((s, i) => (
          <li key={s.stage} className="flex min-w-0 flex-col items-center">
            <div className="relative flex h-24 w-full items-center justify-center">
              {i < n - 1 ? (
                <Segment
                  orientation="h"
                  from={HW}
                  to={HW}
                  colorA={stageColor(i, n)}
                  colorB={stageColor(i + 1, n)}
                  gid={`${uid}-h${i}`}
                />
              ) : null}
              {i < n - 1 ? <Gate orientation="h" /> : null}
              <Node stage={s} last={i === n - 1} size={58} />
            </div>
            <div className="mt-3 px-1.5 text-center">
              <p className="text-[13.5px] font-semibold text-arepo-ink">{s.label}</p>
              {s.unit ? <p className="text-[11px] text-arepo-muted">{s.unit}</p> : null}
              <p className="mx-auto mt-0.5 hidden max-w-[150px] text-[12px] leading-snug text-arepo-muted lg:block">
                {s.help}
              </p>
            </div>
            {s.candidates.length ? (
              <ul className="mt-3 flex w-full max-w-[160px] flex-col gap-1.5 px-1.5" aria-label={`Candidates at ${s.label}`}>
                {s.candidates.map((c) => (
                  <li key={c.id}>
                    <CandidateChip exp={c} />
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ol>

      {/* Phone: top to bottom. */}
      <ol aria-label="Edge pipeline stages" className="md:hidden">
        {stages.map((s, i) => (
          <li key={s.stage} className="relative flex gap-4">
            <div className="relative w-14 flex-none self-stretch">
              {i < n - 1 ? (
                <Segment
                  orientation="v"
                  from={VW}
                  to={VW}
                  colorA={stageColor(i, n)}
                  colorB={stageColor(i + 1, n)}
                  gid={`${uid}-v${i}`}
                />
              ) : null}
              {i < n - 1 ? <Gate orientation="v" /> : null}
              <div className="flex justify-center">
                <Node stage={s} last={i === n - 1} size={44} />
              </div>
            </div>
            <div className="min-w-0 flex-1 pb-6 pt-1">
              <p className="text-[14.5px] font-semibold text-arepo-ink">
                {s.label}
                {s.unit ? <span className="ml-1.5 text-[11.5px] font-normal text-arepo-muted">{fmtCount(s.count)} {s.unit}</span> : null}
              </p>
              <p className="text-[12.5px] leading-snug text-arepo-muted">{s.help}</p>
              {s.candidates.length ? (
                <ul className="mt-2 flex flex-wrap gap-1.5" aria-label={`Candidates at ${s.label}`}>
                  {s.candidates.map((c) => (
                    <li key={c.id}>
                      <CandidateChip exp={c} />
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </figure>
  );
}
