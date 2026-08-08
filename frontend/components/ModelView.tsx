"use client";

import type { Signal } from "@/lib/types";
import { formatPercent } from "@/lib/format";
import { directionalVerdict, directionLabel, DIRECTION_TONE_CLASS, strengthWord } from "@/lib/directional";

// The directional gate lives in lib/directional.ts so Market Detail (here) and Signal Lab use the
// exact same rule (spec §4, §13), mirroring the backend hypothesis + price-family logic.

function strongest(signals: Signal[]): Signal | null {
  if (signals.length === 0) return null;
  return [...signals].sort((a, b) => b.strength - a.strength)[0];
}

function hypothesis(sig: Signal): { directional: boolean; text: string } {
  const directional = directionalVerdict(sig).qualifies;
  if (!directional) {
    return {
      directional: false,
      text: "Arepo does not currently have enough independent evidence to favour a direction in this market.",
    };
  }
  const name = sig.outcome_name ?? "this";
  const pressure = sig.direction === "up" ? "upward" : "downward";
  return {
    directional: true,
    text: `Arepo currently sees ${strengthWord(sig.strength)} evidence of ${pressure} repricing pressure on the ${name} outcome.`,
  };
}

/**
 * The "Current model view" lead for a market (spec §6): it states the cautious statistical
 * hypothesis first, then the directional view, signal strength and confidence, a concise reason
 * and the key risks, before the detailed per-signal breakdown below. When several outcomes have
 * related signals (Yes/No of a binary market), only the strongest is led with, and a note
 * explains that the complementary outcome mirrors it rather than being separate evidence.
 */
export function ModelView({ signals }: { signals: Signal[] }) {
  const lead = strongest(signals);
  if (!lead) {
    return (
      <div className="rounded-card border border-arepo-border bg-arepo-surface p-5">
        <p className="text-[14px] text-arepo-ink2">
          Arepo does not currently have enough independent evidence to favour a direction in this
          market.
        </p>
      </div>
    );
  }
  const h = hypothesis(lead);
  const others = signals.filter((s) => s.token_id !== lead.token_id);

  return (
    <div className="rounded-card border border-arepo-border bg-arepo-surface p-5">
      <p className="text-[15px] font-medium leading-relaxed text-arepo-ink">{h.text}</p>

      {h.directional && (
        <div className="mt-3 flex flex-wrap gap-2 text-[12px]">
          <Stat label="Direction">
            {(() => {
              const d = directionLabel(lead.direction, lead.outcome_name);
              return (
                <span className={DIRECTION_TONE_CLASS[d.tone]}>
                  {d.glyph} {d.text}
                </span>
              );
            })()}
          </Stat>
          <Stat label="Signal strength">{formatPercent(lead.strength, 0)}</Stat>
          <Stat label="Confidence (data quality)">{formatPercent(lead.confidence, 0)}</Stat>
        </div>
      )}

      {lead.why_it_matters && (
        <p className="mt-3 text-[13px] leading-relaxed text-arepo-muted">
          <span className="font-medium text-arepo-ink2">Why: </span>
          {lead.why_it_matters}
        </p>
      )}
      {lead.limitations && (
        <p className="mt-2 text-[13px] leading-relaxed text-arepo-muted">
          <span className="font-medium text-arepo-ink2">Risks: </span>
          {lead.limitations}
        </p>
      )}

      {others.length > 0 && (
        <p className="mt-3 text-[12px] text-arepo-muted">
          The other outcome moves as the mathematical mirror of this one, so it is not separate
          evidence. See the full per-signal breakdown below.
        </p>
      )}

      <p className="mt-3 border-t border-arepo-border pt-3 text-[12px] text-arepo-muted">
        This is a statistical research hypothesis, not financial advice. Check the evidence,
        market rules and risks yourself before making any decision.
      </p>
    </div>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-arepo-surface2 px-2 py-1">
      <span className="uppercase tracking-wide text-arepo-muted">{label}</span>
      <span className="font-tabular font-semibold text-arepo-ink">{children}</span>
    </span>
  );
}
