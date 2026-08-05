# Edge-research adversarial review

Independent adversarial pass over the edge-research engine (freeze -> forward collection ->
baselines/ablation -> edge verdict -> `/api/research/status` -> Replay UI). Each item below is an
attempted disproof of the system's honesty claims, with the outcome, severity, exact location and a
concrete scenario or reproduction. Findings that did NOT hold up are listed at the end so the record
is not one-sided.

## Confirmed findings

### 1. `beats_momentum` / `beats_price_only` are mathematically unsatisfiable — edge can never be "supported", not even with a perfect sample
**Severity: MAJOR** (fails safe today, but the docs mischaracterise the remaining work)

- `backend/astrolabe/analytics/anomaly.py:166-168` sets `direction` to the sign of the z-score.
- `backend/astrolabe/evaluation/research_engine.py:280` sets `momentum_direction = _sign(ta.zscore)`
  — the same z-score. So whenever a directional call exists, `entry.direction ==
  entry.momentum_direction` by construction (acknowledged in
  `research_predictors.py:6-8`: "momentum, price-only and Arepo share a direction by construction").
  `price_z_only` (`research_predictors.py:61-63`) uses the identical field.
- `research_analysis.py:156-160` requires `arepo["hit_rate"] > momentum["hit_rate"]` (strict `>`).
  Since the two predictors make an identical call on every observation, their hit rates are always
  equal, never strictly greater.
- Reproduced directly: fed `baseline_table`/`edge_verdict` a synthetic 150-observation sample where
  Arepo is correct 100% of the time (a "perfect" prospective run) and manually satisfied every other
  criterion. Result: `beats_momentum: False`, `beats_price_only: False`, `edge_supported: False`.
  No accumulation of real data can change this outcome under the current direction derivation.
- `docs/edge-research-requirement-traceability.md` row 14 says only "Awaiting data to ever flip to
  supported" — this implies the gap is sample size. It is not: two of the ten criteria are currently
  unwinnable by design, independent of sample size.
- **Fix**: either redefine `beats_momentum`/`beats_price_only` to compare against a genuinely
  independent baseline (e.g. Arepo's edge must come from the non-price families adding value, which
  `ablation_adds_value` already tests), or drop the redundant criteria and rely on
  `ablation_adds_value` for that claim, and correct the traceability doc to say so explicitly.

### 2. Three of ten edge criteria have no computation path in production at all
**Severity: MAJOR**

- `research_service.py:136-137` calls `edge_verdict(..., walk_forward_stable=None,
  ablation_beats_momentum=None, adversarial_passed=None)` — hardcoded, always.
- `research_analysis.py:170-173` turns these into `bool(None) == False`.
- `research_walk_forward.py`'s `walk_forward_windows`/`window_verdict`/`assert_no_leakage` are never
  imported or called anywhere outside their own module and unit tests (`grep` across
  `backend/astrolabe` confirms zero production callers).
- No "adversarial_passed" computation exists anywhere in the codebase; it is a free parameter with
  no source of truth.
- Combined with #1, **5 of the 10 AND-ed criteria are currently unsatisfiable**, 2 for mathematical
  reasons and 3 for missing glue code. `edge_supported` cannot become `True` today under any data
  volume without further engineering, not just data accumulation as the traceability doc implies.
- **Fix**: either wire `research_walk_forward` output and a real ablation/adversarial check into
  `research_service.status()`, or state plainly in the docs/UI that these criteria require
  additional unbuilt code, not just elapsed time.

### 3. Cross-cadence aggregation treats correlated observations of the same market as independent samples
**Severity: MAJOR**

- `research_service.py:60-65` (`_frozen_entries`) and `horizon_analysis`/`status`
  (`research_service.py:67-179`) pool entries from **every** frozen cohort across all three cadences
  (6h/daily/weekly) with no de-duplication by `market_id`.
- A market active for two weeks is frozen independently by ~4 weekly, ~14 daily and ~56 six-hourly
  runs (`screen_universe` re-screens the live active universe each run — the same persistent market
  is picked up every time). Each freeze produces a separate `ResearchEntryRow`, and each contributes
  its own "evaluable" 24h observation to `horizon_analysis`/`edge_verdict`.
- `MIN_PROSPECTIVE_SAMPLE = 100` (`research_constants.py:85`) and the Wilson interval
  (`replay_stats.wilson_interval`) both assume i.i.d. Bernoulli trials. Heavily overlapping
  cadence windows on the same underlying market are not independent — a handful of persistent
  markets could satisfy `meets_minimum_sample` and produce an artificially tight `ci95` while
  representing far fewer independently-informative signals than the count implies.
- **Fix**: de-duplicate by `market_id` (or explicitly weight/cluster by market) before computing
  `evaluable_sample`, the Wilson CI and the edge verdict; or restrict the primary edge test to one
  cadence (e.g. daily) and report the others as secondary.

### 4. `provenance_class` can be silently mutated on an already-frozen cohort
**Severity: MAJOR (latent — currently unreachable, but the guard is genuinely absent)**

- `research_engine.py:230-231`:
  ```python
  if cohort.provenance_class != provenance_class:
      cohort.provenance_class = provenance_class
  if cohort.frozen:
      return {...}
  ```
  The provenance mutation happens **before** the frozen check and has no `CohortFrozenError` guard,
  unlike `add_entry` (`research_repository.py:109-112`) which correctly raises on a frozen cohort.
- Today this is unreachable because `get_or_create_cohort` (`research_repository.py:87-104`)
  hardcodes `provenance_class="prospective"` on creation, ignoring any caller-supplied value, so no
  code path ever creates a non-"prospective" `ResearchCohortRow`. But the mutation branch itself is
  live code with no test coverage of the frozen case, and the module docstring's claim ("a frozen
  cohort can never gain, drop or alter an entry") does not cover this field.
- Concrete risk: any future caller of `freeze_from_inputs` with a non-default `provenance_class`
  argument against an existing frozen cohort would silently reclassify it — e.g. flipping a
  synthetic/backfilled cohort to `"prospective"` (the function's default parameter value) would
  contaminate every "real stored rows" claim in `research_service.status()`, with no revision
  logged.
- **Fix**: raise `CohortFrozenError` if `cohort.frozen and cohort.provenance_class !=
  provenance_class`, and/or have `get_or_create_cohort` honour the caller's `provenance_class` on
  creation (it currently silently ignores it, which is a second, related bug).

### 5. `positive_after_costs` is not sample-gated on the executable-cost denominator
**Severity: MAJOR**

- `edge_verdict` (`research_analysis.py:161-165`) checks `meets_minimum_sample` against
  `evaluable_sample` (a horizon's midpoint-only count) but bases `positive_after_costs` on
  `arepo["mean_executable_move"]`, which is computed only over `executable_evaluated` — the subset
  with usable `near_mid_depth` on both entry and exit (`research_analysis.py:38-44`,
  `execution.py:74-83`). There is no minimum-sample check on `executable_evaluated` anywhere
  (confirmed by grep: `MIN_PROSPECTIVE_SAMPLE` is referenced only once, against `evaluable_sample`).
- Reproduced directly: 100 synthetic observations (satisfies `meets_minimum_sample`), only 2 of them
  carry depth data. `full_arepo["evaluated"] == 100`, but `executable_evaluated == 2` and
  `mean_executable_move` (0.07, positive) is computed from just those 2 — enough to satisfy
  `positive_after_costs` while the "100-sample minimum" gate is checking an unrelated, much larger
  denominator.
- **Fix**: add an explicit minimum on `executable_evaluated` (not just `evaluable_sample`) before
  `positive_after_costs` can be `True`, and surface the executable sample size next to the claim.

## Attempted disproofs that did NOT hold up

- **Leakage via causal guard bypass**: traced `collect_due_forward` (`research_tracking.py:66-111`)
  — the `target < frozen_at` guard correctly marks any horizon predating the freeze as
  `invalid_predates_freeze` rather than backfilling it, and `frozen_at` (not the snapped-down
  `cutoff_at`) is used as the causal reference, which is the correct, stricter choice. Could not
  construct a scenario where a post-cutoff price enters a frozen entry or an early observation is
  recorded (`now < target` is checked before any quote fetch).
- **Duplicate entries within one cohort**: `add_entry` is idempotent on `(cohort_id, market_id,
  token_id)` both at the DB unique-constraint level and in application logic; could not produce two
  rows for the same market/token in one cohort.
- **Forward observation overwrite**: `upsert_forward` (`research_repository.py:225-264`) refuses to
  write over an existing `(entry, horizon)` row; could not backdate or replace a recorded
  observation.
- **Resolution flip-flopping**: `record_resolution` only fills an empty resolution, never overwrites
  an already-resolved market; could not simulate a silent resolution change.
- **Synthetic contamination of `/api/research/status`**: every read path
  (`_frozen_entries`, `count_cohorts_by_cadence`, `list_cohorts`) filters
  `provenance_class == "prospective"` explicitly, and (per finding #4) no code path currently
  creates a research cohort with any other provenance — could not get synthetic data into the status
  endpoint via the currently-wired code paths.
- **Frontend inflating or hiding the empty state**: `ResearchStatusSection`
  (`frontend/app/replay/page.tsx:615-651`) and `ResearchStatus`/`getResearchStatus`
  (`frontend/lib/api.ts:216-244`) render exactly the fields the backend returns with no synthetic
  fallback, reconstruction, or default substitution; the "not supported" banner and note text are
  driven directly by `data.edge.edge_supported`/`data.edge.message`. Could not find a path where the
  UI shows a rosier picture than the API.

## Compact summary

1. MAJOR | `research_analysis.py:156-168`, `research_predictors.py:59-64`, `research_engine.py:280` | `beats_momentum`/`beats_price_only` are mathematically unsatisfiable (Arepo's direction == momentum/price-only direction by construction), so `edge_supported` can never be `True` regardless of sample size — contradicts traceability doc's "awaiting data" framing | Redefine or drop these criteria in favour of `ablation_adds_value`, and correct the docs.
2. MAJOR | `research_service.py:136-137`, `research_walk_forward.py` (no production callers) | 3/10 edge criteria (`walk_forward_stable`, `ablation_adds_value`, `adversarial_passed`) are hardcoded `None`/unwired, not merely data-starved | Wire real computations into `status()` before claiming "awaiting data" is the only gap.
3. MAJOR | `research_service.py:60-179` | Cross-cadence aggregation (6h+daily+weekly) has no de-dup by `market_id`, letting one persistent market inflate `evaluable_sample`/Wilson CI with correlated, non-independent observations | De-duplicate by market or restrict the primary edge test to one cadence.
4. MAJOR (latent) | `research_engine.py:230-231` vs `research_repository.py:109-112` | `provenance_class` mutation on a cohort has no frozen-guard (unlike entries); `get_or_create_cohort` also ignores the caller's `provenance_class` on creation | Raise `CohortFrozenError` on a provenance mismatch against a frozen cohort; honour the parameter on creation.
5. MAJOR | `research_analysis.py:161-165`, `execution.py:74-83` | `positive_after_costs` has no minimum-sample gate on `executable_evaluated`, so it can pass on a handful of depth-available trades while `meets_minimum_sample` checks an unrelated, larger denominator | Add an explicit minimum on `executable_evaluated`.

Could not break: the causal forward-observation guard, cohort/entry/forward immutability and
idempotency, resolution overwrite protection, synthetic exclusion from `/api/research/status` (given
current callers), or the frontend's fidelity to the backend's honest-empty-state numbers.
