# Edge-research quant / feature-ablation / walk-forward review

Independent review of `backend/astrolabe/evaluation/research_analysis.py`,
`research_predictors.py`, `research_walk_forward.py`, `research_calibration.py`,
`research_constants.py`, `replay_stats.py`, and `research_service.py`, against
`docs/edge-research-requirement-traceability.md` and `docs/edge-research-architecture-review.md`.
Tests: `cd backend && python -m pytest tests/unit/test_research_analysis.py -q` — 7 passed.

## Bottom line

- **Value beyond momentum**: the ablation machinery is structurally honest (it documents and
  demonstrates `full_arepo == momentum` by construction, and `without_momentum` correctly falls
  back to microstructure), but the "adds value" verdict is **not wired to the computed ablation
  table at all** — `research_service.status()` hardcodes `ablation_beats_momentum=None`
  (`research_service.py:136`), so `ablation_table()`'s real per-horizon diffs are computed and
  returned to the API but never consulted by `edge_verdict`. Today this is safe (it can only force
  "not supported"), but it means the edge verdict can **never** flip to supported even once real
  data accumulates, without a code change nobody has scheduled. The traceability doc's "Awaiting
  data" framing (row 9/14) undersells this — it is "awaiting data **and** wiring."
- **Dev/eval separation**: the walk-forward *primitives* (`assert_no_leakage`, `is_reportable`,
  `partition_for_backfill`, non-overlapping windows) are individually correct, but
  `is_reportable`/`assert_no_leakage` are **never called from any production code path**
  (`research_service._frozen_entries` / `horizon_analysis` read every frozen entry unconditionally,
  ignoring `walk_forward_partition`). Currently harmless only because nothing in the codebase yet
  writes a non-`live` partition. The guard is a landmine, not an enforced invariant.

## Findings (severity-ranked)

1. **MAJOR** — `research_service.py:60-86` (`_frozen_entries`, `horizon_analysis`): never filters
   by `walk_forward_partition` / `is_reportable`. If a future backfill/reconstruction path ever
   writes `PARTITION_THRESHOLD` or `PARTITION_DEVELOPMENT` entries into the same tables (exactly
   what `partition_for_backfill` in `research_walk_forward.py:29` exists to support), those rows
   would silently enter `evaluable`, the baseline/ablation tables, and the edge verdict — the
   no-leakage guardrail (`research_walk_forward.py:45`) is dead code from a call-graph perspective.
   Fix: `if not is_reportable(e.walk_forward_partition): continue` in `_frozen_entries`, and call
   `assert_no_leakage` wherever threshold-selection IDs and reported-eval IDs are assembled.

2. **MAJOR** — `research_predictors.py:55` / `research_analysis.py:47-82`: the `no_change` baseline
   (`fn: lambda e: None`) is scored through `score_predictor`/`classify_directional`, but
   `classify_directional` only returns `"correct"` when `direction in ("up","down")`. Since
   `no_change` always passes `direction=None`, it can **never** register a "correct" — `evaluated`
   is always 0 and `hit_rate` is always `None`, regardless of how many markets were genuinely flat.
   Reproduced: 5 flat observations -> `{'evaluated': 0, 'correct': 0, 'hit_rate': None, 'flat': 5}`.
   Contrast with `replay_stats.compare_baselines` (`replay_stats.py:156-174`), which special-cases
   `no_change` correctly. This baseline is non-functional as wired into the live/API path (does not
   affect `edge_verdict`, which never reads `no_change`, but degrades one of the required baselines
   in row 8 of the traceability matrix). Fix: give `no_change` a bespoke scorer mirroring
   `compare_baselines`, or add a "flat-predicting" `kind` that `score_predictor` handles specially.

3. **MAJOR** — `research_analysis.py:151,172`: `thresholds_unchanged: bool = True` (default) is
   never computed from anything — no caller anywhere passes a non-default value, and no code
   compares `MODEL_VERSION`/`CALCULATION_VERSION` across the evaluated sample. Unlike the other
   three not-yet-wired criteria (`walk_forward_stable`, `ablation_beats_momentum`,
   `adversarial_passed`, all correctly default to `None` -> `False`, i.e. fail-safe), this one
   defaults to automatically-satisfied. It is currently inert only because the other three force
   `supported=False` regardless. Fix: either compute it from stored `model_version`/
   `calculation_version` consistency, or default it to `False`/`None` like its siblings so it
   cannot silently pass once the other three are wired up.

4. **MINOR** — `docs/edge-research-requirement-traceability.md:31` and
   `docs/edge-research-architecture-review.md` both say "ten edge acceptance criteria"; the
   `criteria` dict in `research_analysis.py:162-174` has **11** keys (`frozen_before_outcome`
   through `adversarial_passed`). Cosmetic (more criteria, not fewer, so still conservative) but
   the docs should match the code.

5. **MINOR** — `research_analysis.py:70,80` (`score_predictor`) imports `sample_verdict` from
   `replay_stats.py`, which gates on `MIN_MEANINGFUL_SAMPLE = 20` (`replay_stats.py:16`), while the
   edge-level gate in the same object graph uses `MIN_PROSPECTIVE_SAMPLE = 100`
   (`research_constants.py:85`). A per-baseline/ablation row can show `"verdict": "indicative"` at
   n=20 in the same API payload where `edge.criteria.meets_minimum_sample` correctly still requires
   100. Not exploitable (edge_verdict is the gating object) but inconsistent labeling that invites
   misreading a 20-sample row as meaningful. Fix: use one shared minimum, or rename the per-row
   field so it's clearly not the edge-acceptance bar.

6. **MINOR** — `research_service.py:133` (`edge_verdict(evaluable_sample=h24["evaluable"], ...)`):
   `h24["evaluable"]` (`research_service.py:80`, = `len(obs)` in `horizon_analysis`) counts entries
   with a forward midpoint **before** flat exclusion, whereas the hit-rate/CI actually used by
   `interval_supports_positive` is computed on `arepo["evaluated"]` (post-flat-exclusion, from
   `score_predictor`). A cohort dominated by flats could satisfy `meets_minimum_sample >= 100` on a
   much smaller effective n. In practice this is masked by the Wilson-interval criterion (small
   post-flat n produces a wide CI that rarely clears the 0.5 lower bound), so it is not currently a
   path to a false "supported" verdict, but the two counts should be the same denominator for the
   gate to mean what it says.

## Confirmed sound (PASS)

- Flat exclusion is symmetric across every predictor: `classify_directional` (`replay_stats.py:28`)
  decides "flat" from the realised move alone, before consulting direction, so all predictors
  scored on the same `HorizonObs` get identical flat treatment (finding #2 is a *no_change-specific*
  scoring bug, not an asymmetry).
- `edge_verdict` aggregation (`all(criteria.values())`, `research_analysis.py:175`) is genuinely
  conservative: any unmet or unknown (`None`) criterion forces `not supported`.
- `full_arepo == momentum_direction` by construction is real and honestly documented/exercised —
  both derive from the same z-score sign (`research_engine.py:280,290`, `anomaly.py:166-168`) — so
  `beats_momentum` is correctly unsatisfiable until Arepo's composite direction genuinely diverges
  from momentum on some entries; not a bug.
- `walk_forward_windows` never overlaps train/test (`research_walk_forward.py:71-76`, test-covered
  `train[1] < test[0]`); `partition_for_backfill` split (50/20/30) is deterministic and documented
  as not applying to live cohorts.
- Calibration (`research_calibration.py`) is properly guarded: `brier_score`/`log_loss` only
  computed on genuine probability pairs, unused anywhere in production (no probability head exists
  yet, consistent with docs); `calibration_status` gates on `MIN_CALIBRATION_SAMPLE=200`.
  `confidence_frequency_bins` binning logic is sound.
- `wilson_interval`/`sample_verdict` are textbook-correct on tiny/zero samples (n=0 -> (0,1)).
- `MIN_PROSPECTIVE_SAMPLE=100` / `MIN_CALIBRATION_SAMPLE=200` / `MIN_WINDOW_SAMPLE=30` are
  predeclared in `research_constants.py` with an explicit anti-drift comment, not derived from any
  observed result.
- No path found by which the framework can currently report a positive edge on a tiny/biased
  sample — `walk_forward_stable`, `ablation_beats_momentum`, `adversarial_passed` are all hardcoded
  `None` in the only real caller (`research_service.py:136-137`), so `edge_supported` cannot become
  `True` today regardless of sample size (arguably *too* conservative — see finding #1).

## Explicit answers

- **Can the framework determine value beyond momentum?** Not yet, and not by itself: the ablation
  table is computed correctly and honestly on real data, but `edge_verdict` never reads it
  (finding #1). Someone must wire `ablation_beats_momentum` from `ablation_table()`'s output before
  an "adds value" conclusion is even reachable.
- **Are development/threshold/evaluation properly separated?** Correctly *specified* (partitions,
  leakage assertion, reportability filter) but not *enforced* — the read path ignores partitions
  entirely (finding #1). Safe today only because no code currently produces non-`live` partitions.
