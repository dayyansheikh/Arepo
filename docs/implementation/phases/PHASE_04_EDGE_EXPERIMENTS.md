# Phase 04 — Baselines and initial edge experiments

Status: provisional; refine after prerequisite evidence. Owner: current AREPO implementation task.

## Objective

Freeze reproducible no-change, momentum, richer price/context and v1 baselines; test a small registered feature subset.

## Why this phase exists

Strong baselines and falsifiable protocols distinguish information from impact and overfitting.

## Research basis

Experiment cards H02/H08/H09/H10/H14/H15/H24/H27/H28; model protocol baselines, splitting, power and multiplicity. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 03 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

research_predictors.py exposes momentum-derived v1 directions and historical ablations. No-change/price/context probability candidates and locked v2 common-panel experiments are not implemented. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Freeze reproducible no-change, momentum, richer price/context and v1 baselines; test a small registered feature subset. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Inspect Phase 3 admissibility and sample composition; specify common origin/target panel and frozen baseline definitions.
2. Implement B0/B1/B2/B3 and v1 replay with exact versions; fit baseline transforms only in development.
3. Prioritise the registered book/flow/related/reference experiments; refine ambiguous sign/unit/window details before lock.
4. Register all trials, chronological/grouped splits, actual-label purging, quote-age/source-outage and future-shift placebos, family multiplicity and pilot power.
5. Run analyses only on eligible real data; preserve positive, negative, inconclusive and invalid verdicts with effective event/time counts.
6. Freeze a small confirmation subset and publish reproducibility report; do not advance data-dependent work without sufficient clean events.

## Likely modules/files

New research_panel baseline/experiment/split modules; evaluation/research_predictors.py used as pinned baseline reference; experiment artifacts.

## Data model, API and migration implications

Use versioned v2 entities and immutable artifact manifests. Refine any additive schema proposal from observed prerequisite needs; no automatic production migration or serving API promotion.

## Tests required

Baseline equal-origin and target parity; flat/abstain distinction; fold leakage/future-shift; purging by actual label availability; event/market deduplication; all-trial retention and uncertainty; known synthetic effects for machinery only, never scientific evidence.

## Acceptance criteria

Four baselines reproducible and frozen; initial registered experiments honestly evaluated with adequate predeclared evidence or explicit data blocker; negative/inconclusive results preserved; no winner invented.

## Exit checklist

- [ ] Prerequisites reloaded and plan refined against real outputs.
- [ ] All scoped tasks and acceptance criteria satisfied; limitations explicit.
- [ ] Required tests passed with exact command/target/result recorded.
- [ ] Diff self-reviewed for causal leakage, data loss, unrelated changes and protected boundaries.
- [ ] Documentation/decision log/master status current.
- [ ] Coherent safe work committed; branch and draft PR/dependency recorded.
- [ ] Checkpoint updated with safe commit, files, tests, blockers and exact next action.

## Protected boundaries

Never fabricate prospective observations, tune on final confirmation, or treat repeated rows as independent events. Preserve complete discovery separately from public limits and sampled deep collection. Archive equivalence does not authorise deletion. A protected action requires the user's explicit decision; record BLOCKED — USER DECISION REQUIRED with the concrete action. Missing access/data is a real blocker; synthetic fixtures are not a substitute for empirical acceptance.

## Handoff/output

Locked baselines, experiment ledger, initial evidence/negative results and data-readiness report.
