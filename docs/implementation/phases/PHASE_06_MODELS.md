# Phase 06 — Bayesian and ML candidates

Status: provisional; refine after prerequisite evidence. Owner: current AREPO implementation task.

## Objective

Develop and lock one hierarchical Bayesian candidate and the strongest budgeted ML challenger using development data only.

## Why this phase exists

Complex models cannot repair bad clocks, insufficient events or biased sampling.

## Research basis

Model protocol Bayesian/ML sections, E24–E28/E31/E32; all challenger status remains unproven. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 05 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Requires sufficient clean prospective data; elapsed time/row count alone is not readiness. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

No trained/prospectively validated Bayesian or ML candidate is supplied. Existing heuristic scoring remains a baseline. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Develop and lock one hierarchical Bayesian candidate and the strongest budgeted ML challenger using development data only. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Verify independent-event sample/power and prerequisite family quality; freeze finite candidate search budget.
2. Implement hierarchical Bayesian and regularised baseline/boosted ML candidates with fold-local transformations and calibration.
3. Run prior/posterior checks, convergence/ESS/divergence, stability and chronological/grouped purging tests.
4. Select the strongest ML and one Bayesian candidate solely on development; save all trials/artifacts/manifests.
5. Lock model/target/calibration before new confirmation begins; do not retune on final panel.

## Likely modules/files

New research modelling modules with pinned optional dependencies and fold artifacts; no serving integration.

## Data model, API and migration implications

Use versioned v2 entities and immutable artifact manifests. Refine any additive schema proposal from observed prerequisite needs; no automatic production migration or serving API promotion.

## Tests required

Fold-local transforms/calibration, feature/time/group leakage; seeded reproducibility; prior predictive and numerical inference diagnostics; finite budget/trial ledger; untouched confirmation manifest.

## Acceptance criteria

Sufficient clean independent events; candidate budget honoured; diagnostics and development comparisons pass; exactly named constituents locked with versioned artifacts, no confirmation leakage.

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

Frozen Bayesian/ML artifacts, out-of-fold predictions and untouched confirmation design.
