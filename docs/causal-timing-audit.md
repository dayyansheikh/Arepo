# Causal-timing audit: cutoff_at vs frozen_at

## The reproduced issue

Local `research_cohorts` showed cohorts frozen long after their labelled boundary, e.g. a weekly
cohort with `cutoff_at` 2026-08-03 00:00 but `frozen_at` 2026-08-06 00:57 (nearly 3 days late). The
forward collector computed horizon due times from `cutoff_at` (the snapped cadence LABEL), so a late
freeze's outcomes were measured from a boundary at which no prediction was actually made. A weekly
cohort frozen on Thursday could be presented as if Arepo predicted on Monday using Monday
information. That is a causal‑integrity defect.

## Audit result — every use of cutoff_at / frozen_at

| Area | Before | After |
| --- | --- | --- |
| Cohort creation | keyed by (cadence, cutoff_at) | unchanged; `cutoff_at` is now the SCHEDULED bucket label, exposed as `scheduled_for` |
| Causal origin | implicit (cutoff_at) | explicit `evaluation_origin_at` = `frozen_at`, stored per cohort |
| Frozen entry prices | captured at screen time (= now at freeze ≈ frozen_at) | unchanged; documented as at/≤ frozen_at |
| Forward due times | **`cutoff_at` + horizon (bug)** | **`evaluation_origin_at` (frozen_at) + horizon** |
| Causal guard | rejected horizons predating freeze | obsolete/removed: horizons now always start at frozen_at |
| Time-to-close | `expected_close - now` (now = freeze moment) | unchanged; explicitly from frozen_at |
| Resolution eval | per market_id, timing-independent | unchanged |
| Replay (research) | showed cut-off | shows ACTUAL frozen time + "scheduled for X, frozen at Y", lateness |
| Research status | oldest/newest by cutoff | by causal origin (frozen); adds scheduled/actual/lateness + late counts |
| Baselines / ablation | operate on obs | unchanged (obs are now correctly timed) |
| Walk-forward | live partition | unchanged; dedup/order use causal origin |
| Execution | entry vs forward midpoints | unchanged (obs correctly timed) |
| API schemas | cutoff_at | + scheduled_for, frozen_at, evaluation_origin_at, lateness, late/excessively-late |
| Frontend copy | "cut-off" | actual freeze time prominent + lateness/late badges |
| Legacy weekly pipeline | already used `due_horizons(frozen_at)` | unchanged (was already correct) |

## Required architecture (implemented)

- `evaluation_origin_at` == `frozen_at`; `lateness_seconds` = frozen_at − cutoff_at; `late`
  (> 15 min) and `excessively_late` (> 6 h) flags.
- Every forward horizon, entry timestamp and time-to-close is measured from `frozen_at`.
- No observation before `frozen_at` is ever used as a forward outcome (horizons start at frozen_at).
- `cutoff_at` remains only as the cadence bucket label (exposed as `scheduled_for`).
- A late cohort is labelled "Scheduled for X, actually frozen at Y" in Replay.
- Missed cohorts are NOT backfilled with current data under the missed boundary: the freeze uses
  current data timestamped at frozen_at, and the outcome window runs from frozen_at.

## Lateness policy

- Small delays recorded (`lateness_seconds`); `late` above 15 min.
- `excessively_late` above 6 h: still causally valid (origin = frozen_at) but **excluded from
  comparable performance** so a stale/backfilled run cannot be shown as a genuine scheduled
  prediction. Research status reports the late and excessively-late (excluded) counts.
- In production the freeze crons fire ~5 min after each boundary, so real cohorts are not late.

## Local cohort audit + cleanup

The five existing local cohorts were dry-run test artifacts (arbitrary freeze times, 0 evaluable
outcomes, `evaluation_origin_at` NULL). They were timing-invalid and removed after a timestamped
backup (`astrolabe.db.backup-<ts>`), leaving a clean slate. Exact commands are in the final report.

## Tests (all passing)

`tests/unit/test_research_timing.py` + `test_research_pipeline.py::test_horizons_run_from_frozen_at_not_cutoff`:
horizons run from frozen_at; a Thursday freeze creates only Thursday+ outcomes (never Tue/Wed); a
missed weekly is not presented as a Monday prediction (origin = frozen_at, excessively-late
excluded); moderately-late cohorts stay valid and in-sample; early observations are rejected; and the
status reports scheduled vs actual freeze time and lateness.
