"use client";

import type { Contrast, FeatureWeight, MlBlock } from "@/lib/lab/types";
import { seriesColors, theme } from "@/lib/theme";
import { Card, Pill, Quiet } from "./primitives";
import type { Tone } from "@/lib/lab/model";

const STATUS: Record<string, { label: string; tone: Tone }> = {
  running: { label: "Training", tone: "accent" },
  done: { label: "Fitted", tone: "pos" },
  waiting: { label: "Waiting for data", tone: "neutral" },
  parked: { label: "Parked", tone: "muted" },
};

/**
 * Families take the site's chart colours in fixed first-seen order (extras fold into grey), but
 * only when a family holds several bars; with one bar per family the label already names it and
 * a single neutral colour is calmer.
 */
function familyColours(weights: FeatureWeight[]): Map<string, string> | null {
  const counts = new Map<string, number>();
  for (const w of weights) counts.set(w.family || "other", (counts.get(w.family || "other") ?? 0) + 1);
  if (!Array.from(counts.values()).some((c) => c > 1)) return null;
  const map = new Map<string, string>();
  for (const fam of counts.keys()) {
    map.set(fam, map.size < seriesColors.length ? seriesColors[map.size] : theme.muted);
  }
  return map;
}

const AXIS_LABEL = "Drop-one log-loss change (nats)";

function signed(v: number): string {
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(4)}`;
}

/** Diverging bars around zero, one row per feature/family, with its own scale per group. */
function WeightBars({
  rows,
  colours,
  dashed = false,
}: {
  rows: FeatureWeight[];
  colours: Map<string, string> | null;
  dashed?: boolean;
}) {
  const maxPos = Math.max(0, ...rows.map((r) => r.weight));
  const maxNeg = Math.max(0, ...rows.map((r) => -r.weight));
  const span = maxPos + maxNeg || 1;
  const zero = (maxNeg / span) * 100;
  return (
    <div>
      <ul className="space-y-2.5" aria-hidden="true">
        {rows.map((r, i) => {
          const colour = colours?.get(r.family || "other") ?? theme.series2;
          const w = (Math.abs(r.weight) / span) * 100;
          const left = r.weight >= 0 ? zero : zero - w;
          return (
            <li
              key={`${r.feature}-${i}`}
              className="group grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 sm:grid-cols-[11rem_1fr_4.5rem]"
              title={`${r.feature}${r.family ? ` · ${r.family.replace(/_/g, " ")}` : ""} · ${signed(r.weight)} nats`}
            >
              <span className="min-w-0 truncate text-[13px] text-arepo-ink2">{r.feature}</span>
              <span className="relative order-3 col-span-2 h-3 rounded-[4px] bg-arepo-surface2 sm:order-none sm:col-span-1">
                {maxNeg > 0 ? (
                  <span className="absolute inset-y-[-3px] w-px bg-arepo-borderStrong" style={{ left: `${zero}%` }} />
                ) : null}
                <span
                  className="lab-grow absolute inset-y-0 block rounded-[4px] transition-opacity group-hover:opacity-80"
                  style={{
                    left: `${left}%`,
                    width: `${w}%`,
                    background: dashed ? "transparent" : colour,
                    border: dashed ? `1.5px dashed ${theme.series2}` : undefined,
                    transformOrigin: r.weight >= 0 ? "left center" : "right center",
                    animationDelay: `${i * 60}ms`,
                  }}
                />
              </span>
              <span className="font-tabular text-right text-[12.5px] text-arepo-muted">{signed(r.weight)}</span>
            </li>
          );
        })}
      </ul>
      <div className="mt-2 hidden grid-cols-[11rem_1fr_4.5rem] gap-x-3 sm:grid" aria-hidden="true">
        <span />
        <span className="relative h-4 text-[11px] text-arepo-muted">
          {maxNeg > 0 ? (
            <span className="absolute -translate-x-1/2" style={{ left: `${zero}%` }}>
              0
            </span>
          ) : (
            <span className="absolute left-0">0</span>
          )}
        </span>
        <span />
      </div>
    </div>
  );
}

function FeatureWeights({ weights, note }: { weights: FeatureWeight[]; note?: string }) {
  const valid = weights.filter((w) => w && Number.isFinite(w.weight));
  if (!valid.length) return <Quiet>No feature weights yet.</Quiet>;
  const byWeight = (a: FeatureWeight, b: FeatureWeight) => b.weight - a.weight;
  const main = valid.filter((w) => w.comparable !== false).sort(byWeight);
  const other = valid.filter((w) => w.comparable === false).sort(byWeight);
  const colours = familyColours(main);
  return (
    <figure className="m-0">
      <figcaption className="sr-only">
        {AXIS_LABEL}, largest first: {main.map((r) => `${r.feature} ${signed(r.weight)}`).join(", ")}
        {other.length ? `. From a different run, not comparable: ${other.map((r) => `${r.feature} ${signed(r.weight)}`).join(", ")}` : ""}.
      </figcaption>
      {main.length ? <WeightBars rows={main} colours={colours} /> : null}
      <p className="mt-1 text-[11.5px] font-medium text-arepo-muted sm:pl-[11.75rem]">{AXIS_LABEL}</p>
      {colours ? (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
          {Array.from(colours).map(([fam, c]) => (
            <span key={fam} className="inline-flex items-center gap-1.5 text-[12px] text-arepo-ink2">
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
              {fam.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      ) : null}
      {other.length ? (
        <div className="mt-5 border-t border-dashed border-arepo-border pt-4">
          <p className="mb-3 text-[12px] font-semibold text-arepo-ink2">
            Different run, not comparable <span className="font-normal text-arepo-muted">(own scale)</span>
          </p>
          <WeightBars rows={other} colours={null} dashed />
        </div>
      ) : null}
      {note ? <p className="mt-4 text-[12px] leading-relaxed text-arepo-muted">{note}</p> : null}
    </figure>
  );
}

function fmt(v: number): string {
  const a = Math.abs(v);
  return a !== 0 && a < 0.1 ? v.toFixed(4) : v.toFixed(2);
}

function ContrastChart({ contrasts }: { contrasts: Contrast[] }) {
  const rows = contrasts.filter((c) => Number.isFinite(c.value));
  if (!rows.length) return <Quiet>No contrasts yet.</Quiet>;
  const vals = rows.flatMap((c) => [c.value, c.lo ?? c.value, c.hi ?? c.value, 0]);
  let lo = Math.min(...vals);
  let hi = Math.max(...vals);
  const pad = (hi - lo || 1) * 0.12;
  lo -= pad;
  hi += pad;
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const unit = rows[0].unit ?? "";
  return (
    <figure className="m-0">
      <figcaption className="sr-only">
        Contrasts with intervals:{" "}
        {rows
          .map((c) => `${c.label}: ${fmt(c.value)} ${c.unit ?? ""} (${c.lo != null ? fmt(c.lo) : "?"} to ${c.hi != null ? fmt(c.hi) : "?"})${c.replicated ? ", replicated" : ""}`)
          .join("; ")}
        .
      </figcaption>
      <ul className="space-y-4" aria-hidden="true">
        {rows.map((c) => (
          <li key={c.label} className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[14rem_1fr_9.5rem] sm:items-center">
            <span className="text-[13px] text-arepo-ink2">
              {c.label}
              {c.replicated ? <span className="ml-1.5 text-[11px] font-semibold text-arepo-pos">replicated</span> : null}
            </span>
            <span className="relative block h-6" title={`${fmt(c.value)} ${c.unit ?? ""}`}>
              <span className="absolute inset-x-0 top-1/2 h-px bg-arepo-border" />
              <span
                className="absolute top-0 h-full border-l border-dashed border-arepo-borderStrong"
                style={{ left: `${x(0)}%` }}
              />
              {c.lo != null && c.hi != null ? (
                <span
                  className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
                  style={{
                    left: `${x(c.lo)}%`,
                    width: `${x(c.hi) - x(c.lo)}%`,
                    background: c.replicated ? theme.accent : theme.series2,
                    opacity: 0.45,
                  }}
                />
              ) : null}
              <span
                className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2"
                style={{
                  left: `${x(c.value)}%`,
                  background: c.replicated ? theme.accent : theme.surface,
                  borderColor: c.replicated ? theme.surface : theme.series2,
                  boxShadow: c.replicated ? `0 0 0 1px ${theme.accent}` : undefined,
                }}
              />
            </span>
            <span className="font-tabular text-[12px] text-arepo-muted sm:text-right">
              <span className="font-semibold text-arepo-ink">{fmt(c.value)}</span>{" "}
              [{c.lo != null ? fmt(c.lo) : "?"}, {c.hi != null ? fmt(c.hi) : "?"}]
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-2 hidden grid-cols-[14rem_1fr_9.5rem] gap-x-4 sm:grid" aria-hidden="true">
        <span />
        <span className="relative h-4 text-[11px] text-arepo-muted">
          <span className="absolute -translate-x-1/2" style={{ left: `${x(0)}%` }}>
            0
          </span>
          <span className="absolute left-0">{fmt(lo)}</span>
          <span className="absolute right-0">{fmt(hi)}</span>
        </span>
        <span className="text-right text-[11px] text-arepo-muted">{unit}</span>
      </div>
      <p className="mt-3 text-[12px] leading-relaxed text-arepo-muted">
        Dot: estimate{unit ? ` (${unit})` : ""}; bar: interval; dashed line: no difference. Filled red dots held up
        on unseen data.
      </p>
    </figure>
  );
}

export function MachineLearning({ ml }: { ml: MlBlock | undefined }) {
  if (!ml) return <Quiet>The latest snapshot has no machine-learning block.</Quiet>;
  const status = STATUS[ml.status ?? ""] ?? { label: ml.status ?? "Unknown", tone: "neutral" as Tone };
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
      <Card className="lg:col-span-2">
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={status.tone}>
            {ml.status === "running" ? (
              <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
            ) : null}
            {status.label}
          </Pill>
        </div>
        {ml.status_note ? <p className="mt-2 text-[13.5px] leading-relaxed text-arepo-ink2">{ml.status_note}</p> : null}
        <h3 className="mt-5 text-[13px] font-semibold uppercase tracking-wider text-arepo-muted">What it has learnt</h3>
        {ml.learned?.length ? (
          <ol className="mt-3 space-y-3">
            {ml.learned.map((s, i) => (
              <li key={i} className="flex gap-3 text-[14px] leading-relaxed text-arepo-ink">
                <span className="font-display mt-px flex h-5 w-5 flex-none items-center justify-center rounded-full bg-arepo-accentTint text-[11px] font-semibold text-arepo-accentActive">
                  {i + 1}
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-2 text-[13.5px] text-arepo-muted">Nothing summarised yet.</p>
        )}
      </Card>
      <Card className="lg:col-span-3">
        <h3 className="text-[15px] font-semibold text-arepo-ink">What the model leans on</h3>
        <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">
          Change in log-loss when each family is dropped from the model.
        </p>
        <FeatureWeights weights={ml.feature_weights ?? []} note={ml.feature_weights_note} />
      </Card>
      <Card className="lg:col-span-5">
        <h3 className="text-[15px] font-semibold text-arepo-ink">Where the model differs</h3>
        <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">
          Measured differences between situations, with intervals.
        </p>
        <ContrastChart contrasts={ml.contrasts ?? []} />
      </Card>
    </div>
  );
}
