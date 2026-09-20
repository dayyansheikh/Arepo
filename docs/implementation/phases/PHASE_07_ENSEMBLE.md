# Phase 07 — Ensemble tournament

Status: provisional; refine after prerequisite evidence. Owner: current AREPO implementation task.

## Objective

Compare constituents and combinations prospectively on identical origins and decide whether combination earns promotion.

## Why this phase exists

An ensemble must earn its complexity by beating its stronger constituent.

## Research basis

Model protocol tournament and gate; E22/E23; H60 disagreement. Proposed 1% margin requires preregistration, not hindsight. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 06 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

No validated constituent or ensemble supplied; acceptance depends on Phase 6 locks and fresh data. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Compare constituents and combinations prospectively on identical origins and decide whether combination earns promotion. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Inspect frozen constituent artifacts and identical-origin output coverage.
2. Implement B/M/E50/EW/ES; allow EG only after a documented mechanism/sample gate.
3. Fit weights/stacking only on genuinely forward out-of-fold predictions; lock calibration and margins.
4. Compare against both constituents with simultaneous event/time-aware uncertainty, calibration and two future blocks.
5. If combinations fail or are underpowered, record rejection/inconclusive and retain simpler constituent without inventing a win.

## Likely modules/files

New research ensemble/comparison modules; candidate prediction manifests and prospective reports.

## Data model, API and migration implications

Use versioned v2 entities and immutable artifact manifests. Refine any additive schema proposal from observed prerequisite needs; no automatic production migration or serving API promotion.

## Tests required

Identical origins/horizons/group/target joins, no in-sample stacking, probability simplex/calibration, stronger-constituent comparisons with multiplicity; insufficient-events outcome.

## Acceptance criteria

Locked prospective comparison complete with prespecified precision/stopping rules and explicit promote/reject/inconclusive verdict; no requirement to manufacture a successful ensemble.

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

Prospective constituent/ensemble verdicts and exact comparable prediction manifests.
