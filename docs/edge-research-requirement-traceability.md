# Edge-research requirement traceability (prompt section 17A)

One row per substantive requirement. Statuses: **Verified** (implemented and exercised by a test or
the dry run), **Awaiting data** (framework complete and tested; the live conclusion needs real
prospective outcomes), **Blocked** (needs external setup), **Not implemented**. The completion claim
rests on this matrix, not on documentation or placeholders.

| # | Requirement | Status | Code | Schema | Route / CLI | Job | Test | Limitation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | Freeze EVERY valid directional signal (not just top-10) | Verified | `research_engine.build_entry_inputs` | `research_entries` | `research-freeze` | 3 freeze crons | `test_full_universe_frozen_with_roles`, dry run (60-market universe) | — |
| 2 | Explicit roles (public/shadow/observation/abstention) | Verified | `build_entry_inputs`, `research_constants.ROLES` | `research_entries.role` | — | — | `test_full_universe_frozen_with_roles`, dry run | — |
| 3 | 6h / daily / weekly immutable cohorts, unique key, idempotent | Verified | `cadence_cutoff`, `get_or_create_cohort`, `freeze_cohort` | `research_cohorts` unique (cadence,cutoff) | `research-freeze --cadence` | 3 crons | `test_distinct_cadences_are_independent`, `test_freeze_is_idempotent_and_immutable`, dry run | — |
| 3 | Immutable model + calculation version per cohort | Verified | `MODEL_VERSION`, `CALCULATION_VERSION` | `research_cohorts.model_version/calculation_version` | freeze | — | dry run status shows model_version | — |
| 4 | Full screened universe frozen (not only selected) | Verified | `build_entry_inputs` keeps all | `research_entries` | freeze | — | dry run `universe_size=60` incl 38 abstentions | — |
| 4 | All cut-off fields incl Research Priority, families, component availability | Verified | `EntryInput`, `research_engine` | `research_entries.*` | — | — | `test_research_pipeline` asserts fields | — |
| 4 | Revision record instead of mutating a frozen cohort | Verified | `ResearchRepository.add_revision` | `research_revisions` | — | — | frozen-guard tests | no revision UI yet |
| 5 | Outcomes at 1h/6h/24h/7d + final resolution | Verified | `RESEARCH_HORIZONS`, `collect_due_forward`, `record_resolution` | `research_forward_observations`, `market_resolutions` | `research-forward`, `research-resolve` | research-forward, arepo-resolve | `test_forward_collection_is_causal_and_idempotent`, dry run | 7d needs 7 days elapsed |
| 5 | Rich forward fields (mid/bid/ask/spread/depth, exact-vs-nearest, delay, unavailable) | Verified | `ResearchForwardRow`, `collect_due_forward` | `research_forward_observations.*` | — | — | `test_forward_unavailable_reason_when_no_quote` | — |
| 5 | Distinct result states incl flat/invalid | Verified | `classify_directional`, causal guard | forward `unavailable_reason` | — | — | flat + `test_horizon_predating_freeze_is_invalid` | — |
| 6 | Depth-aware executable performance (spread/slippage/fees) | Verified | `execution.evaluate_execution`, `slippage_points` | uses depth/spread fields | status API | — | `test_execution_costs_reduce_a_favourable_move`, `test_execution_unavailable_without_depth` | slippage coeff is a declared assumption |
| 6 | Midpoint vs executable reported separately; missing depth stays missing | Verified | `research_analysis.score_predictor` | — | `/api/research/horizon` | — | dry run `mean_executable_move`; unit tests | — |
| 7 | Separate short-term repricing vs final resolution | Verified | `research_analysis` (repricing) vs `market_resolutions` (resolution) | distinct tables | status API | — | dry run resolves 1 market separately | resolution analysis surfaced minimally |
| 7 | No directional call treated as probability | Verified | `probabilistic_metrics_note`, calibration guard | — | — | — | `test_baselines_score_and_agreement` | — |
| 8 | Baselines incl order-book-only, trade-flow-only, full-without-momentum | Verified | `research_predictors.BASELINES` | frozen per-family directions | `/api/research/horizon` | — | `test_baselines_score_and_agreement`, dry run (10 baselines) | flow direction often None until flow evidence present |
| 9 | Feature ablation (value beyond momentum), deterministic | Verified | `research_predictors.ABLATIONS`, `research_analysis.ablation_table` | — | `/api/research/horizon` | — | `test_ablation_reports_diffs_vs_full_and_momentum`, dry run (9 variants) | conclusion Awaiting data |
| 10 | Walk-forward partitions + no-leakage guardrail + windows | Verified | `research_walk_forward` | `research_entries.walk_forward_partition` | — | — | `test_walk_forward_partitions_and_leakage`, `test_walk_forward_windows_...` | live conclusion Awaiting data |
| 11 | Calibration guarded; Brier/log-loss only with a probability + min sample | Verified | `research_calibration` | — | status API `calibration` | — | `test_calibration_guarded_until_minimum_sample` | Awaiting a probability head + resolved sample |
| 12 | Synthetic excluded from all real performance/edge | Verified | status reads `provenance='prospective'`; `/cohorts/latest` excludes synthetic | `provenance_class` | — | — | `test_provenance_not_mixed`, empty-DB status | — |
| 13 | Research-status API with real stored values | Verified | `research_service.status` | reads all research tables | `/api/research/status`, `/horizon`, `/edge` | web service | dry run + empty-DB status | executable-perf columns surfaced via /horizon |
| 13 | Product surface makes state obvious | Verified | `ResearchStatusSection` | via API | Replay page | web | `next build`; live API | — |
| 14 | Edge acceptance criteria (10) + conservative verdict | Verified | `research_analysis.edge_verdict` | — | status `edge` | — | `test_edge_verdict_not_supported_on_empty_sample`, dry run | Awaiting data to ever flip to supported |
| 15 | Tests for all of the above | Verified | `tests/unit/test_research_*` | — | — | — | 27 research tests (338 total) | — |
| 16 | Independent reviewers, fix critical/major | Verified | `docs/edge-research-*-review.md` | — | — | — | see reviewer docs | — |
| 17 | Deployment handoff | Verified (local) / Blocked (external) | `render.yaml`, handoff in final report | — | crons | — | dry run headless | needs Render/Supabase accounts |
| 17B | Production-equivalent dry run | Verified | `test_research_dry_run.py` + live run | — | CLI | — | `docs/edge-research-end-to-end-dry-run.md` | real time cannot be simulated |
| 17C | Auto-collection without a browser | Verified (mechanism) / Blocked (deploy) | crons + CLI | Postgres-portable | 4 research crons | — | dry run B headless | needs external services enabled |

## Summary

- **Verified**: every framework, schema, job, API and the causal guards — the collection machine is
  complete and headless.
- **Awaiting data**: the *conclusions* of ablation, walk-forward, calibration and the edge verdict.
  These are correctly guarded to stay inconclusive until a real prospective sample exists.
- **Blocked**: only the external deployment (Render service, Supabase Postgres, enabling the crons).

No requirement is marked complete on the basis of documentation, a placeholder, an unpopulated field,
an undefined cron, a mocked-only test, or synthetic data.
