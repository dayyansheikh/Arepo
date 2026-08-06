# Prospective Replay refinement (branch `arepo-prospective-replay-refinement`)

_This pass makes the public Replay product prospective-only and rebuilds it around choosing a real
frozen cohort, an evaluation horizon and a frozen closing window, then answering plainly: did the
market move as expected? It is a product, evaluation-display and Replay refinement pass, not model
tuning. No directional logic, threshold, confidence, Research Priority, eligibility,
evidence-family, baseline, ablation, walk-forward, edge criterion or frozen value was changed._

## What prospective Replay now means

Replay means **real predictions genuinely frozen before later prices became known**. The public page
shows only real prospective cohorts recorded by the scheduled freeze jobs and tracked forward from
their actual freeze time. The former reconstructed-analysis and synthetic-demonstration tabs were
removed from the public interface. The reconstructed screen (`/api/historical/screen`), the
synthetic weekly-cohort seed and the deterministic backtest remain in the codebase for internal use
and automated tests; they simply no longer appear as public Replay modes. Any legacy `?replay=`
value (reconstructed, synthetic, demo, historical, prospective) normalises safely to the single
prospective page and the stale parameter is stripped from the URL.

## Cohort cadence vs evaluation horizon

These are two independent axes and the product keeps them distinct:

- **Cohort cadence** is how often a cohort is frozen: six-hourly, daily or weekly. Only cadences for
  which a real cohort exists are offered. A cohort's cadence is read from the stored `cadence`
  string, so a manually created six-hour cohort is described as six-hourly and never as weekly. A
  weekly cohort is described as a cohort frozen by the weekly scheduled job.
- **Evaluation horizon** is how long after the freeze the outcome is measured: 1 hour, 6 hours, 24
  hours, 7 days, or final resolution. A horizon is only marked evaluable when the stored forward
  observation exists; otherwise it is shown as pending (not yet due, or not yet collected). Outcomes
  are always measured from `evaluation_origin_at`, which equals the actual freeze time, never the
  scheduled cut-off.

## How time-to-close filtering works

The closing-window filter uses the **frozen** time-to-close: `research_entries.time_remaining_hours`,
the value recorded at the moment the cohort was frozen. It is never recomputed from a market's
current time-to-close, so the filter stays a genuine point-in-time property of the prediction. The
options are "closing within 6 hours / 24 hours / 7 days / 30 days at the time of the freeze" and
"all closing times". Closing sooner is not implied to be a stronger signal; it is only a lens on
shorter-dated markets.

## What "moved as expected" means

For 1h/6h/24h/7d the question is: did the selected outcome's midpoint move in Arepo's stored
direction over the horizon, measured from the actual freeze time? Result labels are: moved as
expected, moved against the call, no price change, pending, unavailable, invalid. "No price change"
means the stored midpoint did not move at all (a tiny float-comparison guard, `REPLAY_MOVE_EPS`),
which is a plainer, stricter question than the 0.01 materiality floor used for the edge hit-rate
math. A favourable short-term move is never treated as a correct final-outcome forecast, and never
as proof of profit or edge.

## Why flat markets remain in the denominator

The headline sentence leads with the full count, for example: "Of 19 directional calls, 4 moved as
expected, 4 moved against the call and 11 did not change." Markets that did not move stay in the
denominator so the honest coverage of the calls is visible. Leading with a hit rate that silently
excluded flats would flatter the sample.

## Why a high hit rate among only moving markets can be misleading

Where a hit rate is shown it is explicitly labelled "Hit rate among markets that moved", for example
"50% (4 of 8)". Restricted to the eight markets that moved, four in each direction give 50%. That
number ignores the eleven flat markets and a handful of moves can swing it wildly, so it is never
presented as the headline and never as evidence of skill.

## Why one cohort cannot demonstrate edge

A single six-hour cohort of 19 directional calls is far below the predeclared minimum sample for any
edge claim, spans one short window and one model version, and cannot separate skill from noise. The
edge verdict on the research-status surface stays not-supported. The Replay product deliberately
answers only the plain descriptive question ("did these markets move as expected?") and never claims
an edge from one cohort.

## How local and production collection differ

Replay grows only when scheduled backend jobs freeze cohorts and collect later prices. Leaving the
page open in a browser collects nothing. Locally the single real six-hour cohort was frozen once and
its 1h and 6h forward prices collected; 24h and 7d remain pending until those horizons are collected.
In production the Render cron jobs freeze the 6h, daily and weekly cohorts at their boundaries and a
forward-collection cron records due observations automatically, with no browser involved.

## Scheduler status (prompt section 12)

`render.yaml` already defines real research cron jobs for all three cadences plus forward collection,
and shared final-resolution collection:

- `arepo-research-freeze-6h` — `5 0,6,12,18 * * *`
- `arepo-research-freeze-daily` — `10 0 * * *`
- `arepo-research-freeze-weekly` — `15 0 * * 1`
- `arepo-research-forward` — `*/20 * * * *`
- final resolutions are populated by the shared `arepo-resolve` cron and read by the research layer.

This configuration is correct and was left unchanged. It is not deployed here. The local browser
does not perform any of these jobs.

## API

Two typed, read-only, deterministic endpoints back the product, computing the evaluation truth
server-side so the frontend never re-classifies a market:

- `GET /api/research/replay/cohorts` — available real prospective cohorts (cadence, label,
  description, scheduled cut-off, actual freeze, evaluation origin, lateness, role counts, universe
  size, available horizons, resolution availability) plus a per-cadence summary and the newest-cohort
  default. Excessively-late cohorts are excluded, matching the existing excessive-lateness rule.
- `GET /api/research/replay/cohort/{id}?horizon=&scope=&closing=` — per-cohort result set: the
  headline movement counts, the public/shadow/combined split, movement coverage, the labelled
  hit-rate-among-moved, the top-ten-by-frozen-rank market rows (frozen rank, market, outcome, role,
  direction, frozen midpoint, horizon midpoint, midpoint movement, executable result where depth is
  genuinely available, frozen time-to-close, result state, per-row final resolution) and the separate
  final-resolution summary. Non-directional observation and abstention rows never enter the table;
  their counts stay in the methodology summary.

## Local verification commands

```
# Backend (from backend/, venv active)
python -m pytest -q                 # 376 passed
ruff check astrolabe tests scripts  # All checks passed!

# Frontend (from frontend/)
npx tsc --noEmit                    # clean
npm run lint                        # clean
npx vitest run                      # 58 passed (18 new in lib/replay.test.ts)
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run build   # 15 routes

# Real-browser acceptance (backend on :8000, frontend on :3000, real preserved DB)
npx playwright test                 # 85 passed
```
