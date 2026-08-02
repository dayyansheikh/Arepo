"use client";

import { useState } from "react";
import { useAsync } from "@/lib/use-async";
import { getBacktest } from "@/lib/api";
import { formatPercent, formatSignedPercent, formatZScore, formatPrice, titleCase } from "@/lib/format";
import { ErrorState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";

const HORIZON_OPTIONS = ["15m", "1h", "4h", "24h"];

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-4">
      <div className="text-xs text-muted-fg">{label}</div>
      <div className="mt-1 text-xl font-mono font-tabular">{value}</div>
    </div>
  );
}

export default function ReplayPage() {
  const [strengthThreshold, setStrengthThreshold] = useState(0.6);
  const [moveThreshold, setMoveThreshold] = useState(0.03);
  const [horizon, setHorizon] = useState("1h");

  const { data, loading, error } = useAsync(
    () =>
      getBacktest({
        strength_threshold: strengthThreshold,
        move_threshold: moveThreshold,
        horizon,
      }),
    [strengthThreshold, moveThreshold, horizon]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Replay &amp; Backtest</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-fg">
          This backtest runs against a deterministic, synthetic replay dataset with a
          look-ahead-safe evaluation window. It measures how often a signal was followed by a
          price move of the chosen size — it is not a profitability claim and does not reflect
          any real trading strategy or execution costs.
        </p>
      </div>

      <form
        className="panel flex flex-wrap items-end gap-4 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <div className="flex flex-col gap-1">
          <label htmlFor="strength" className="text-xs font-medium text-muted-fg">
            Strength threshold ({strengthThreshold.toFixed(2)})
          </label>
          <input
            id="strength"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={strengthThreshold}
            onChange={(e) => setStrengthThreshold(Number(e.target.value))}
            className="w-48"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="move" className="text-xs font-medium text-muted-fg">
            Move threshold ({formatPercent(moveThreshold, 1)})
          </label>
          <input
            id="move"
            type="range"
            min={0.005}
            max={0.2}
            step={0.005}
            value={moveThreshold}
            onChange={(e) => setMoveThreshold(Number(e.target.value))}
            className="w-48"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="horizon" className="text-xs font-medium text-muted-fg">
            Horizon
          </label>
          <select
            id="horizon"
            value={horizon}
            onChange={(e) => setHorizon(e.target.value)}
            className="focus-ring rounded-instrument border border-astro-light-border dark:border-astro-border bg-transparent px-3 py-1.5 text-sm"
          >
            {HORIZON_OPTIONS.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>
      </form>

      {loading && <ListSkeleton rows={6} />}
      {!loading && error && <ErrorState message={error} />}

      {!loading && data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatTile label="Sample size" value={String(data.sample_size)} />
            <StatTile label="Evaluated" value={String(data.evaluated)} />
            <StatTile label="Missing obs." value={String(data.missing_observations)} />
            <StatTile label="Hit rate" value={formatPercent(data.hit_rate)} />
            <StatTile label="False positive rate" value={formatPercent(data.false_positive_rate)} />
            <StatTile
              label="Avg forward move"
              value={formatSignedPercent(data.avg_forward_move_directional)}
            />
          </div>

          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="border-b border-astro-light-border dark:border-astro-border text-left text-xs text-muted-fg">
                  <th className="px-3 py-2 font-normal">Market</th>
                  <th className="px-3 py-2 font-normal">Frame</th>
                  <th className="px-3 py-2 font-normal">Strength</th>
                  <th className="px-3 py-2 font-normal">Z-score</th>
                  <th className="px-3 py-2 font-normal">Direction</th>
                  <th className="px-3 py-2 font-normal">Entry</th>
                  <th className="px-3 py-2 font-normal">Forward</th>
                  <th className="px-3 py-2 font-normal">Followed through</th>
                </tr>
              </thead>
              <tbody className="font-mono font-tabular">
                {data.events.map((ev, i) => (
                  <tr key={`${ev.market_id}-${ev.token_id}-${i}`} className="border-b border-astro-light-border dark:border-astro-border last:border-0">
                    <td className="px-3 py-2 font-sans">{ev.market_id}</td>
                    <td className="px-3 py-2">{ev.frame}</td>
                    <td className="px-3 py-2">{formatPercent(ev.strength, 0)}</td>
                    <td className="px-3 py-2">{formatZScore(ev.zscore)}</td>
                    <td className="px-3 py-2">
                      {ev.direction === "up" && <span className="text-astro-positive">up</span>}
                      {ev.direction === "down" && <span className="text-astro-negative">down</span>}
                      {!ev.direction && "—"}
                    </td>
                    <td className="px-3 py-2">{formatPrice(ev.entry_price)}</td>
                    <td className="px-3 py-2">{formatPrice(ev.forward_price)}</td>
                    <td className="px-3 py-2">
                      {ev.followed_through === null
                        ? "—"
                        : ev.followed_through
                          ? "yes"
                          : "no"}
                    </td>
                  </tr>
                ))}
                {data.events.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-center text-muted-fg font-sans">
                      No events matched these thresholds.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="panel p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg mb-2">
                Assumptions
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-fg">
                {data.assumptions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
            <div className="panel p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg mb-2">
                Limitations
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-fg">
                {data.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          </div>

          <p className="text-xs text-muted-fg">
            Horizon {titleCase(data.horizon)} · z-score window {data.zscore_window} · minimum
            history {data.min_history}
          </p>
        </>
      )}
    </div>
  );
}
