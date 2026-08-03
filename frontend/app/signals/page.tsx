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
import { MetricHelp } from "@/components/MetricHelp";
import { SectionLabel, Disclose, Badge, PageHeader } from "@/components/ui";

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
        <PageHeader
          title="Signal Lab"
          lead={
            <>
              Every market currently showing unusual activity, ranked by strength, with the
              reasoning behind each one.
            </>
          }
        />
        <DisclaimerBanner />
      </div>

      <div className="panel space-y-5 p-6">
        <div>
          <h2 className="text-base font-bold text-arepo-ink">What does &ldquo;Unusual market activity&rdquo; mean?</h2>
          <p className="mt-1.5 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            A signal fires when a market&apos;s recent price, spread, volume and order-book
            behaviour look statistically unusual compared with its own history, not compared with
            any other market. That can mean an unusual price move, a sudden pickup in trading
            activity, a lopsided order book, a widening spread, or a shift in the depth available
            near the price, alone or in combination.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-arepo-ink">Which factors contributed, and why the score rises</h3>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            Each card lists the factors behind it in plain English, for example &ldquo;unusual price
            move&rdquo; or &ldquo;order-book imbalance&rdquo;. The more of these that line up at
            once, the higher the score: a market with an unusual price move, a widening spread and
            a lopsided order book together will score higher than one showing just an unusual
            price move on its own.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-arepo-ink">What a score such as 93 means</h3>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            Strength runs from 0 to 100. A score of 93 means this market&apos;s recent behaviour
            is close to the most unusual the method can register, not that something specific is
            about to happen and not a probability of anything. Treat a high score as a strong
            prompt to read the detail, not as a verdict.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-arepo-ink">Strength is not confidence</h3>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            <MetricHelp metric="signal-strength" /> measures how unusual the behaviour looks.{" "}
            <MetricHelp metric="confidence" /> measures how much to trust that reading, based on
            how much clean history, spread and depth went into it. A high-strength signal built on
            thin data can carry low confidence, which is why the two sit side by side on every
            card rather than being blended into one number.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-arepo-ink">Not proof of insider information</h3>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            A high score is a screening heuristic: a prompt to look more closely, not evidence that
            anyone traded on non-public information. Ordinary news, thin liquidity or a single
            large but perfectly legitimate order can all produce the same reading.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-arepo-ink">Data coverage and lookback</h3>
          <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-ink2">
            <MetricHelp metric="data-coverage" /> describes how much clean history and order-book
            depth a reading is based on. Limited or poor coverage means the numbers should be read
            as more approximate. <MetricHelp metric="lookback" /> is the recent window of
            observations, or span of time, the calculation looks back over: a longer lookback
            smooths out short-lived blips, while a shorter one reacts faster but is noisier.
          </p>
        </div>

        <Disclose summary="Show technical detail">
          <p className="max-w-reading text-sm leading-relaxed text-arepo-muted">
            The technical name for this reading is <strong>Composite anomaly score</strong>. It is
            a weighted mean of normalised components, each capped before weighting. The full
            derivation, including weights and caps, lives on the{" "}
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
