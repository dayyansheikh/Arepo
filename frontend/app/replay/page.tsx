"use client";

import { useEffect, useState } from "react";
import { useAsync } from "@/lib/use-async";
import { getBacktest } from "@/lib/api";
import type { BacktestEvent } from "@/lib/types";
import { formatPercent, formatSignedPercent, formatZScore, formatPrice } from "@/lib/format";
import { ErrorState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { SectionLabel, Disclose, StatTile, Badge } from "@/components/ui";
import { MetricHelp } from "@/components/MetricHelp";

// Horizon is measured in dataset frames (each frame is one step of the deterministic
// replay dataset).
const HORIZON_OPTIONS = [5, 10, 20];

// How long to wait after the user stops dragging a slider before refetching.
const DEBOUNCE_MS = 300;

export default function ReplayPage() {
  // Immediate slider values, so the on-screen readout tracks the thumb exactly.
  const [strengthInput, setStrengthInput] = useState(0.6);
  const [moveInput, setMoveInput] = useState(0.03);
  const [horizon, setHorizon] = useState(5);

  // Debounced copies: these are what actually drive the refetch, so dragging a
  // slider doesn't fire a request on every pixel of movement.
  const [strengthThreshold, setStrengthThreshold] = useState(strengthInput);
  const [moveThreshold, setMoveThreshold] = useState(moveInput);

  useEffect(() => {
    const t = setTimeout(() => setStrengthThreshold(strengthInput), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [strengthInput]);

  useEffect(() => {
    const t = setTimeout(() => setMoveThreshold(moveInput), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [moveInput]);

  const { data, loading, error } = useAsync(
    () =>
      getBacktest({
        strength_threshold: strengthThreshold,
        move_threshold: moveThreshold,
        horizon,
      }),
    [strengthThreshold, moveThreshold, horizon]
  );

  const hits = data
    ? data.hit_rate !== null
      ? Math.round(data.hit_rate * data.evaluated)
      : data.events.filter((e) => e.followed_through === true).length
    : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[30px] font-semibold tracking-[-0.01em] text-arepo-ink">
          Replay &amp; backtest
        </h1>
        <p className="mt-1 max-w-reading text-sm leading-relaxed text-arepo-muted">
          See how often a signal was followed by a real price move, on a fixed demonstration
          dataset with a look-ahead-safe evaluation window.
        </p>
      </div>

      <div className="panel space-y-2 p-6">
        <h2 className="text-base font-semibold text-arepo-ink">What this page shows</h2>
        <ul className="max-w-reading list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-arepo-ink2">
          <li>Replay runs against a fixed sample dataset, not live markets.</li>
          <li>A signal is generated at one point in time, using only data available up to that moment.</li>
          <li>The system then checks what happened afterwards, over a set number of frames.</li>
          <li>The controls below change how selective the signal is: stricter settings mean fewer signals.</li>
          <li>A hit means the price moved as expected afterwards. It does not mean a trade based on it would have been profitable.</li>
          <li>This page demonstrates how to evaluate a signal. It is not evidence of predictive advantage.</li>
        </ul>
      </div>

      <form
        className="panel grid grid-cols-1 gap-6 p-6 sm:grid-cols-3 sm:items-start"
        onSubmit={(e) => e.preventDefault()}
      >
        <div className="space-y-3">
          <label htmlFor="strength" className="flex items-center justify-between gap-2 text-[13px] font-medium text-arepo-ink">
            <span className="flex items-center gap-1">
              Minimum signal strength
              <MetricHelp metric="threshold" showTerm={false} />
            </span>
            <span className="font-tabular text-arepo-accentActive">
              {formatPercent(strengthInput, 0)}
            </span>
          </label>
          <input
            id="strength"
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={strengthInput}
            onChange={(e) => setStrengthInput(Number(e.target.value))}
            className="slider-arepo"
          />
        </div>

        <div className="space-y-3">
          <label htmlFor="move" className="flex items-center justify-between gap-2 text-[13px] font-medium text-arepo-ink">
            <span className="flex items-center gap-1">
              Required later movement
              <MetricHelp metric="movement" showTerm={false} />
            </span>
            <span className="font-tabular text-arepo-accentActive">
              {formatPercent(moveInput, 1)}
            </span>
          </label>
          <input
            id="move"
            type="range"
            min={0}
            max={0.1}
            step={0.005}
            value={moveInput}
            onChange={(e) => setMoveInput(Number(e.target.value))}
            className="slider-arepo"
          />
        </div>

        <div className="space-y-3">
          <label htmlFor="horizon" className="flex items-center gap-1 text-[13px] font-medium text-arepo-ink">
            How far ahead to check
            <MetricHelp metric="evaluation-horizon" showTerm={false} />
          </label>
          <select
            id="horizon"
            className="select-arepo"
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          >
            {HORIZON_OPTIONS.map((h) => (
              <option key={h} value={h}>
                {h} frames
              </option>
            ))}
          </select>
        </div>
      </form>

      {loading && <ListSkeleton rows={6} />}
      {!loading && error && <ErrorState message={error} />}

      {!loading && data && (
        <>
          <div className="space-y-1">
            <p className="max-w-reading text-sm leading-relaxed text-arepo-ink">
              With these settings, <span className="font-semibold">{data.sample_size}</span>{" "}
              signals were tested. <span className="font-semibold">{hits}</span> were followed
              by a move in the expected direction.
            </p>
            <p className="max-w-reading text-[13px] leading-relaxed text-arepo-muted">
              A hit means the price followed through in the signalled direction within the
              horizon. It is not a claim that a trade based on it would have been profitable.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <StatTile
              label="Sample size"
              help={<MetricHelp metric="sample-size" showTerm={false} />}
              value={String(data.sample_size)}
            />
            <StatTile label="Evaluated" value={String(data.evaluated)} />
            <StatTile
              label="Hit rate"
              help={<MetricHelp metric="hit-rate" showTerm={false} />}
              value={formatPercent(data.hit_rate)}
              emphasis
            />
            <StatTile
              label="False positive rate"
              help={<MetricHelp metric="false-positive-rate" showTerm={false} />}
              value={formatPercent(data.false_positive_rate)}
            />
            <StatTile
              label="Average forward move"
              help={<MetricHelp metric="average-forward-move" showTerm={false} />}
              value={formatSignedPercent(data.avg_forward_move_directional)}
            />
            <StatTile label="Missing observations" value={String(data.missing_observations)} />
          </div>

          <Disclose summary="Show the tested signals">
            <EventsTable events={data.events} />
            <p className="mt-3 text-[13px] text-arepo-muted">
              Horizon {data.horizon} frames &middot; z-score window {data.zscore_window} frames
              &middot; minimum history {data.min_history} frames.
            </p>
          </Disclose>

          <Disclose summary="Assumptions and limitations">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <SectionLabel>Assumptions</SectionLabel>
                <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-arepo-muted">
                  {data.assumptions.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
              <div>
                <SectionLabel>Limitations</SectionLabel>
                <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-arepo-muted">
                  {data.limitations.map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Disclose>
        </>
      )}

      <DisclaimerBanner />
    </div>
  );
}

/** The full per-signal outcome table behind "Show the tested signals". */
function EventsTable({ events }: { events: BacktestEvent[] }) {
  return (
    <div className="overflow-hidden rounded-card border border-arepo-border bg-arepo-surface">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="bg-arepo-surface2 text-left text-[11px] uppercase tracking-wide text-arepo-muted">
              <th className="px-4 py-3 font-semibold">Market</th>
              <th className="px-4 py-3 font-semibold">Frame</th>
              <th className="px-4 py-3 font-semibold">Strength</th>
              <th className="px-4 py-3 font-semibold">Z-score</th>
              <th className="px-4 py-3 font-semibold">Direction</th>
              <th className="px-4 py-3 font-semibold">Entry</th>
              <th className="px-4 py-3 font-semibold">Forward</th>
              <th className="px-4 py-3 font-semibold">Followed through</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-arepo-border font-tabular">
            {events.map((ev, i) => (
              <tr key={`${ev.market_id}-${ev.token_id}-${i}`}>
                <td className="px-4 py-2.5 font-sans text-arepo-ink">{ev.market_id}</td>
                <td className="px-4 py-2.5">{ev.frame}</td>
                <td className="px-4 py-2.5">{formatPercent(ev.strength, 0)}</td>
                <td className="px-4 py-2.5">{formatZScore(ev.zscore)}</td>
                <td className="px-4 py-2.5">
                  {ev.direction === "up" && <span className="font-medium text-arepo-pos">Up</span>}
                  {ev.direction === "down" && <span className="font-medium text-arepo-neg">Down</span>}
                  {!ev.direction && <span className="text-arepo-muted">&mdash;</span>}
                </td>
                <td className="px-4 py-2.5">{formatPrice(ev.entry_price)}</td>
                <td className="px-4 py-2.5">{formatPrice(ev.forward_price)}</td>
                <td className="px-4 py-2.5 font-sans">
                  {ev.followed_through === null ? (
                    <span className="text-arepo-muted">&mdash;</span>
                  ) : (
                    <Badge tone={ev.followed_through ? "good" : "neutral"}>
                      {ev.followed_through ? "Yes" : "No"}
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center font-sans text-arepo-muted">
                  No events matched these thresholds.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
