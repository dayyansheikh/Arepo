"use client";

import { useState } from "react";
import Link from "next/link";
import type { Signal } from "@/lib/types";
import { directionalVerdict } from "@/lib/directional";
import { formatDateTime, formatNumber, formatPercent } from "@/lib/format";
import {
  formatLookback,
  componentUnavailableReason,
  friendlyComponentName,
  friendlySignalTitle,
  replaceComponentNames,
  technicalSignalTerm,
} from "@/lib/signal-labels";
import { StrengthMeter } from "./StrengthMeter";
import { DataQualityBadge } from "./DataQualityBadge";
import { MetricHelp } from "./MetricHelp";
import { Disclose } from "./ui";

/** Whether a signal qualifies for a directional model view (spec §13), with the reason. */
function DirectionalBadge({ signal }: { signal: Signal }) {
  const v = directionalVerdict(signal);
  return (
    <p
      className={`mt-2 inline-flex flex-wrap items-center gap-1.5 rounded-md px-2 py-1 text-[12px] ${
        v.qualifies
          ? "bg-arepo-accentTint text-arepo-accentActive"
          : "bg-arepo-surface2 text-arepo-muted"
      }`}
    >
      <span aria-hidden="true">{v.qualifies ? "✓" : "○"}</span>
      <span className="font-medium">
        {v.qualifies
          ? "Qualifies for a directional model view"
          : "Observational only, not a directional view"}
      </span>
      <span>({v.reason})</span>
    </p>
  );
}

/**
 * A single explainable signal. Plain-English meaning first (what fired), then a
 * "Why this fired" expander with method, why it may matter, limitations and the
 * component breakdown, plus a link to the methodology. Confidence sits beside
 * strength so the two are never confused.
 */
export function SignalItem({ signal }: { signal: Signal }) {
  const [open, setOpen] = useState(false);
  const panelId = `signal-${signal.token_id}-${signal.kind}-${signal.computed_at}`.replace(
    /[^a-zA-Z0-9-]/g,
    ""
  );

  return (
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-5 shadow-arepo-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-sm font-semibold text-arepo-ink">
              {friendlySignalTitle(signal.kind)}
              {signal.kind === "composite_anomaly" && (
                <MetricHelp metric="composite-anomaly" showTerm={false} />
              )}
            </span>
            <DataQualityBadge quality={signal.data_quality} />
            {signal.window && (
              <span className="flex items-center gap-1 text-xs text-arepo-muted">
                {formatLookback(signal.window)}
                <MetricHelp metric="lookback" showTerm={false} />
              </span>
            )}
          </div>
          <p className="mt-1.5 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            {replaceComponentNames(signal.detected)}
          </p>
          <Link
            href={`/markets/${encodeURIComponent(signal.market_id)}`}
            className="focus-ring mt-2 inline-flex max-w-reading items-center gap-1 text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover"
          >
            <span className="truncate">
              {signal.market_question
                ? `Market: ${signal.market_question}${
                    signal.outcome_name ? ` (${signal.outcome_name})` : ""
                  }`
                : "Inspect this market"}
            </span>
            <span aria-hidden="true">&rarr;</span>
          </Link>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          {/* Direction in WORDS first (spec §7): never a bare "28 Up" that reads like a
              probability; up/down is not framed as good/bad. Colour + glyph are secondary cues. */}
          <span
            className="flex items-center gap-1 text-[13px] font-medium"
            title="The direction the outcome has been repricing. Not a probability and not good or bad."
          >
            {signal.direction === "up" && (
              <span className="text-arepo-pos">
                <span aria-hidden="true">&#9650;</span> Upward
              </span>
            )}
            {signal.direction === "down" && (
              <span className="text-arepo-warnText">
                <span aria-hidden="true">&#9660;</span> Downward
              </span>
            )}
            {signal.direction !== "up" && signal.direction !== "down" && (
              <span className="text-arepo-muted">No clear direction</span>
            )}
          </span>
          {/* Strength, labelled and out of 100 so it cannot be read as a probability. */}
          <span className="flex items-center gap-1.5 text-xs text-arepo-muted">
            <span>Strength</span>
            <StrengthMeter strength={signal.strength} className="min-w-24" />
            <span>/100</span>
            <MetricHelp metric="signal-strength" showTerm={false} />
          </span>
          <span className="flex items-center gap-1 text-xs text-arepo-muted">
            {/* Reliability confidence (data quality x corroboration x completeness), the SAME number
                the Opportunity Board and Market Detail show for this signal, never the raw 100%
                data-quality term (spec §6, §17). */}
            Confidence {formatPercent(signal.reliability_confidence ?? signal.confidence, 0)}
            <MetricHelp metric="confidence" showTerm={false} />
          </span>
        </div>
      </div>

      {/* Whether this signal qualifies for a directional model view, using the SAME gate as
          Market Detail (spec §4, §13), so Signal Lab never implies every anomaly is a
          directional opportunity. */}
      <DirectionalBadge signal={signal} />

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="focus-ring mt-3 rounded-md text-[13px] font-semibold text-arepo-accentActive hover:text-arepo-accentHover"
      >
        {open ? "Hide detail" : "Why this fired"}
      </button>

      {open && (
        <div
          id={panelId}
          className="mt-3 space-y-3 border-t border-arepo-border pt-3 text-sm"
        >
          <Field label="How it is measured">{signal.method}</Field>
          <Field label="Why it may matter">{signal.why_it_matters}</Field>
          <Field label="Data quality">
            Data coverage for this reading is {(DATA_QUALITY_WORDS[signal.data_quality] ?? signal.data_quality)}.
            Confidence ({formatPercent(signal.confidence, 0)}) reflects how much clean history, spread and
            order-book depth went into it. Lower confidence on thin data means the numbers are more
            likely to be noisy, not that the market itself is untrustworthy.
          </Field>
          <Field label="Limitations">{signal.limitations}</Field>
          <Field label="How this may be used">
            This is a prompt for research, not trading advice, and never a guarantee of
            profit. A researcher might use it to monitor the market for repricing, compare
            it with related or similar markets, watch whether the order-book imbalance
            persists rather than fading, look for confirmation from price movement or
            liquidity changes, and consider whether the market may simply be slow to
            reflect new information. Treat it as a starting point for further reading,
            not an instruction to trade.
          </Field>

          {signal.components.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-bold uppercase tracking-wide text-arepo-ink">
                Components
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-tabular">
                  <thead>
                    <tr className="text-left text-arepo-muted">
                      <th className="py-1 pr-3 font-medium">Name</th>
                      <th className="py-1 pr-3 font-medium">Raw</th>
                      <th className="py-1 pr-3 font-medium">Normalised</th>
                      <th className="py-1 pr-3 font-medium">Weight</th>
                      <th className="py-1 font-medium">Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signal.components.map((c, i) => {
                      const missing = c.raw_value === null;
                      return (
                        <tr key={`${c.name}-${i}`} className="border-t border-arepo-border">
                          <td className="whitespace-nowrap py-1.5 pr-3 text-arepo-ink">
                            {friendlyComponentName(c.name)}
                          </td>
                          {missing ? (
                            <td colSpan={3} className="py-1.5 pr-3 italic text-arepo-muted">
                              {componentUnavailableReason(c.name)}
                            </td>
                          ) : (
                            <>
                              <td className="py-1.5 pr-3">{formatNumber(c.raw_value, 3)}</td>
                              <td className="py-1.5 pr-3">
                                {formatNumber(c.normalized_value, 3)}
                              </td>
                              <td className="py-1.5 pr-3">{formatNumber(c.weight, 2)}</td>
                            </>
                          )}
                          <td className="py-1.5 text-arepo-muted">{c.explanation}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <Disclose summary="Show technical detail" className="mt-2">
                <div className="space-y-1.5 text-xs text-arepo-muted">
                  {technicalSignalTerm(signal.kind) && (
                    <p className="flex flex-wrap items-center gap-1">
                      Technical term:{" "}
                      <span className="font-semibold text-arepo-ink2">
                        {technicalSignalTerm(signal.kind)}
                      </span>
                      {signal.kind === "composite_anomaly" && (
                        <MetricHelp metric="composite-anomaly" showTerm={false} />
                      )}
                    </p>
                  )}
                  <p>Raw component identifiers, as used internally and in the Methodology formulas:</p>
                  <ul className="space-y-0.5 font-mono">
                    {signal.components.map((c, i) => (
                      <li key={`${c.name}-raw-${i}`}>
                        {friendlyComponentName(c.name)} = <code>{c.name}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              </Disclose>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <p className="text-xs text-arepo-muted">Computed {formatDateTime(signal.computed_at)}</p>
            <Link
              href="/methodology#signal-strength"
              className="focus-ring text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover"
            >
              Learn more &rarr;
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

const DATA_QUALITY_WORDS: Record<string, string> = {
  good: "good",
  limited: "limited",
  poor: "poor",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wide text-arepo-ink">{label}</div>
      <p className="mt-0.5 max-w-reading leading-relaxed text-arepo-ink2">{children}</p>
    </div>
  );
}
