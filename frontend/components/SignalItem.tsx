"use client";

import { useState } from "react";
import type { Signal } from "@/lib/types";
import { formatDateTime, formatPercent, titleCase } from "@/lib/format";
import { StrengthMeter } from "./StrengthMeter";
import { DataQualityBadge } from "./DataQualityBadge";

export function SignalItem({ signal }: { signal: Signal }) {
  const [open, setOpen] = useState(false);
  const panelId = `signal-${signal.token_id}-${signal.kind}-${signal.computed_at}`.replace(/[^a-zA-Z0-9-]/g, "");

  return (
    <div className="panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-sm">{titleCase(signal.kind)}</span>
            <DataQualityBadge quality={signal.data_quality} />
            {signal.window && (
              <span className="text-xs text-muted-fg font-mono">window {signal.window}</span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-fg">{signal.detected}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StrengthMeter strength={signal.strength} direction={signal.direction} />
          <span className="text-xs text-muted-fg font-mono">
            confidence {formatPercent(signal.confidence, 0)}
          </span>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="focus-ring mt-3 rounded-instrument text-xs font-medium text-astro-brass hover:underline"
      >
        {open ? "Hide details" : "Why this fired"}
      </button>

      {open && (
        <div id={panelId} className="mt-3 space-y-3 border-t border-astro-light-border dark:border-astro-border pt-3 text-sm">
          <div>
            <div className="text-xs font-medium text-muted-fg uppercase tracking-wide">Method</div>
            <p className="mt-0.5">{signal.method}</p>
          </div>
          <div>
            <div className="text-xs font-medium text-muted-fg uppercase tracking-wide">Why it matters</div>
            <p className="mt-0.5">{signal.why_it_matters}</p>
          </div>
          <div>
            <div className="text-xs font-medium text-muted-fg uppercase tracking-wide">Limitations</div>
            <p className="mt-0.5">{signal.limitations}</p>
          </div>
          {signal.components.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-fg uppercase tracking-wide mb-1">Components</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono font-tabular">
                  <thead>
                    <tr className="text-left text-muted-fg">
                      <th className="pr-3 py-1 font-normal">Name</th>
                      <th className="pr-3 py-1 font-normal">Raw</th>
                      <th className="pr-3 py-1 font-normal">Normalized</th>
                      <th className="pr-3 py-1 font-normal">Weight</th>
                      <th className="py-1 font-normal font-sans">Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signal.components.map((c, i) => (
                      <tr key={`${c.name}-${i}`} className="border-t border-astro-light-border dark:border-astro-border">
                        <td className="pr-3 py-1.5 whitespace-nowrap">{c.name}</td>
                        <td className="pr-3 py-1.5">{c.raw_value ?? "—"}</td>
                        <td className="pr-3 py-1.5">{c.normalized_value ?? "—"}</td>
                        <td className="pr-3 py-1.5">{c.weight ?? "—"}</td>
                        <td className="py-1.5 font-sans text-muted-fg">{c.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <p className="text-xs text-muted-fg">Computed {formatDateTime(signal.computed_at)}</p>
        </div>
      )}
    </div>
  );
}
