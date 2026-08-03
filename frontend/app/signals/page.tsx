"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getSignals } from "@/lib/api";
import type { Signal } from "@/lib/types";
import { SignalItem } from "@/components/SignalItem";
import { ListSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { SectionLabel, Disclose, Badge } from "@/components/ui";

type MinStrength = "any" | "0.7" | "0.4";

const MIN_STRENGTH_OPTIONS: { value: MinStrength; label: string }[] = [
  { value: "any", label: "Any strength" },
  { value: "0.7", label: "70+ (strong)" },
  { value: "0.4", label: "40+ (moderate or above)" },
];

function strengthTier(strength: number): { label: string; tone: "strong" | "moderate" | "weak" } {
  if (strength >= 0.7) return { label: "Strong", tone: "strong" };
  if (strength >= 0.4) return { label: "Moderate", tone: "moderate" };
  return { label: "Weak", tone: "weak" };
}

export default function SignalLabPage() {
  const { mode } = useMode();
  const { data, loading, error } = useAsync(() => getSignals(mode, 50), [mode]);
  const [minStrength, setMinStrength] = useState<MinStrength>("any");

  const sorted = useMemo(() => {
    const signals = data ? [...data.signals] : [];
    signals.sort((a, b) => b.strength - a.strength);
    return signals;
  }, [data]);

  const filtered = useMemo(() => {
    if (minStrength === "any") return sorted;
    const threshold = Number(minStrength);
    return sorted.filter((s) => s.strength >= threshold);
  }, [sorted, minStrength]);

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div>
          <h1 className="text-[30px] font-semibold tracking-[-0.01em] text-arepo-ink">Signal Lab</h1>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-muted">
            Every market currently showing a composite anomaly signal, ranked by strength, with the
            reasoning behind each one.
          </p>
        </div>
        <DisclaimerBanner />
      </div>

      <div className="panel space-y-2 p-6">
        <h2 className="text-base font-semibold text-arepo-ink">What is the composite anomaly signal?</h2>
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-ink2">
          It blends three things that are each ordinary to watch in any market: how far the price has
          moved from its recent average, how wide the bid-ask spread has become, and how imbalanced the
          order book looks. When several of these line up at once, the composite score rises and a
          signal fires. A high score is not proof of informed or insider activity, it is a screening
          heuristic that flags where to look more closely.
        </p>
        <Disclose summary="Show the maths">
          <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
            The score is a weighted mean of normalised components, each capped before weighting. The
            full derivation, including weights and caps, lives on the{" "}
            <Link
              href="/methodology#signal-strength"
              className="focus-ring font-medium text-arepo-accentActive hover:text-arepo-accentHover"
            >
              Methodology
            </Link>{" "}
            page.
          </p>
        </Disclose>
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionLabel>Currently firing</SectionLabel>
          <label className="flex items-center gap-2 text-[13px] text-arepo-muted">
            <span className="sr-only">Filter by minimum strength</span>
            <select
              className="select-arepo w-48"
              value={minStrength}
              onChange={(e) => setMinStrength(e.target.value as MinStrength)}
              aria-label="Minimum signal strength"
            >
              {MIN_STRENGTH_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {loading && <ListSkeleton rows={8} />}
        {!loading && error && <ErrorState message={error} />}
        {!loading && !error && sorted.length === 0 && (
          <EmptyState message="No signals available in this mode right now." />
        )}
        {!loading && !error && sorted.length > 0 && filtered.length === 0 && (
          <EmptyState message="No signals meet this strength filter. Try lowering it." />
        )}
        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-3">
            {filtered.map((s, i) => (
              <SignalRow key={`${s.kind}-${s.token_id}-${i}`} signal={s} />
            ))}
          </div>
        )}
      </section>

      <Disclose summary="How thresholds affect selectivity">
        <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
          Raising the minimum strength gives fewer, higher-confidence signals. Lowering it surfaces
          more candidates with more false positives. Confidence and strength are not the same thing:
          confidence reflects the quality of the underlying data (history length, spread, depth), not
          how big the anomaly is. Test the effect of any threshold combination in{" "}
          <Link
            href="/replay"
            className="focus-ring font-medium text-arepo-accentActive hover:text-arepo-accentHover"
          >
            Replay
          </Link>
          .
        </p>
      </Disclose>
    </div>
  );
}

/** Wraps SignalItem with a subtle strength-tier badge above the card. */
function SignalRow({ signal }: { signal: Signal }) {
  const tier = strengthTier(signal.strength);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-end">
        <Badge tone={tier.tone}>{tier.label}</Badge>
      </div>
      <SignalItem signal={signal} />
    </div>
  );
}
