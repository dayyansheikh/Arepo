# Edge-research infrastructure baseline

Recorded at the start of the edge-research infrastructure pass, on branch
`arepo-edge-research-infrastructure` (safety tag `arepo-before-edge-research-infrastructure`),
before any schema or model change. Sourced from the running code, the live `astrolabe.db`, the
crons in `render.yaml`, and the read-only edge-research audit.

Gates at baseline: **backend 320 tests pass, ruff clean; frontend tsc/lint clean, 21 vitest.**

| Dimension | Baseline state | Evidence |
| --- | --- | --- |
| Real prospective cohort count | **0** | `weekly_cohorts` has 1 row, `provenance_class='synthetic'` |
| Reconstructed cohort count | **0** (computed live, never stored) | `historical.py` recomputes each request |
| Synthetic cohort count | 1 (`2026-W28`, frozen) | live DB |
| Cohort cadence | **Weekly only** | `WeeklyCohortRow` keyed by `iso_year/iso_week`; `render.yaml` `cohort-freeze` = `59 23 * * 0` |
| Frozen fields | model version, direction, strength, confidence(data-quality), components, entry/bid/ask/spread/depth; **no Research Priority, no universe** | `models.py SignalSnapshotRow/CohortEntryRow`; `research_priority` only in `historical.py` |
| Shadow coverage | **Top-10 only** (`COHORT_TARGET_SIZE=10`) | `engine.py`; not every directional signal |
| Outcome horizons | 1h, 24h, 7d, final | `constants.FORWARD_HORIZONS={1h,24h,7d}` + `MarketResolutionRow`; **no 6h** |
| Baseline coverage | no-change, momentum, price-only, current-implied, always-up/down (6) | `replay_stats.compare_baselines`; **no order-book-only, no trade-flow-only, no full-without-momentum** |
| Execution-cost assumptions | spread-crossing (`fill = entry + spread*SPREAD_CROSS_FRACTION`) + fee | `portfolio.fill_price`; **depth stored but unused; no slippage** |
| Ablation availability | **None** | no `ablation` code anywhere |
| Walk-forward availability | **None** | no partition/holdout code anywhere |
| Calibration availability | **None** (deliberately N/A) | `replay_stats.py` documents Brier/log-loss N/A |
| Collector status | microstructure snapshots running (~1169 rows); cohort-rank hourly (provisional), freeze weekly | `render.yaml` crons; live DB |
| Backend tests | 320 | `pytest -q` |
| Frontend tests | 21 vitest | `vitest run` |

## What this pass must build (from the audit backlog)

Multi-cadence immutable cohorts (6h/daily/weekly) freezing **every directional signal + the full
screened universe** with roles and all fields incl Research Priority; outcomes at 1h/6h/24h/7d/final
with rich forward fields; a depth-aware executable-cost model (midpoint vs executable); the full
prospective baseline set (incl order-book-only, trade-flow-only, full-without-momentum); a
deterministic feature-ablation framework; walk-forward partitions; a calibration guard; an extended
research-status API + Replay surface; tests for all of it; a production-equivalent dry run; and a
deployment handoff. Frameworks must be real and tested but may report "awaiting real data" until
prospective cohorts accumulate. No threshold/sample/cut-off/eligibility change to flatter results.
