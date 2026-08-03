"use client";

import { useState } from "react";
import Link from "next/link";
import type { Signal } from "@/lib/types";
import { formatDateTime, formatNumber, formatPercent, titleCase } from "@/lib/format";
import { StrengthMeter } from "./StrengthMeter";
import { DataQualityBadge } from "./DataQualityBadge";
import { MetricHelp } from "./MetricHelp";

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
            <span className="text-sm font-semibold text-arepo-ink">{titleCase(signal.kind)}</span>
            <DataQualityBadge quality={signal.data_quality} />
            {signal.window && (
              <span className="text-xs text-arepo-muted">window {signal.window}</span>
            )}
          </div>
          <p className="mt-1.5 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            {signal.detected}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StrengthMeter strength={signal.strength} direction={signal.direction} className="min-w-36" />
          <span className="flex items-center gap-1 text-xs text-arepo-muted">
            <MetricHelp metric="confidence" showTerm={false} />
            confidence {formatPercent(signal.confidence, 0)}
          </span>
        </div>
      </div>

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
          <Field label="Limitations">{signal.limitations}</Field>

          {signal.components.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-arepo-muted">
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
                    {signal.components.map((c, i) => (
                      <tr key={`${c.name}-${i}`} className="border-t border-arepo-border">
                        <td className="whitespace-nowrap py-1.5 pr-3 text-arepo-ink">{c.name}</td>
                        <td className="py-1.5 pr-3">{formatNumber(c.raw_value, 3)}</td>
                        <td className="py-1.5 pr-3">{formatNumber(c.normalized_value, 3)}</td>
                        <td className="py-1.5 pr-3">{formatNumber(c.weight, 2)}</td>
                        <td className="py-1.5 text-arepo-muted">{c.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-arepo-muted">{label}</div>
      <p className="mt-0.5 max-w-reading leading-relaxed text-arepo-ink2">{children}</p>
    </div>
  );
}
