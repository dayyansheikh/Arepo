# Phase 05 — Wallet and information event engine

Status: provisional; refine after prerequisite evidence. Owner: current AREPO implementation task.

## Objective

Add historical as-of public wallet state and rule-aware information features only after valid panel evidence exists.

## Why this phase exists

Current wallet rankings and retrospective text do not establish as-of information.

## Research basis

Report N/O, external register, H03–H07/H13/H16–H22/H33–H35/H45–H55 as prerequisites permit. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 04 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

analytics.flow has current concentration, relative size, cluster and limited-history diagnostics; it is not a point-in-time wallet intelligence store. No Information Event Engine. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Add historical as-of public wallet state and rule-aware information features only after valid panel evidence exists. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Inspect actual residual evidence and source rights/coverage; select justified wallet/information families.
2. Implement as-of balances/flows including transfers/splits/merges and mature-label-only skill with uncertainty.
3. Implement versioned claim extraction, exact numbers, prerelease expectations, rule matching, syndication lineage, novelty/surprise and decay.
4. Create blinded annotation/latency audit; deterministic text baselines, historical-LLM-leakage controls and no person-identity claims.
5. Measure common-panel ablations and cost; preserve failed approaches; lock retained definitions only with evidence.

## Likely modules/files

New wallet/information subpackages and typed store writers; analytics.flow reference; annotation fixtures/reports.

## Data model, API and migration implications

Use versioned v2 entities and immutable artifact manifests. Refine any additive schema proposal from observed prerequisite needs; no automatic production migration or serving API promotion.

## Tests required

Future-label wallet leakage; transfer/fill dedup and coverage; revised/prerelease number clocks; negation/units/date/rule matching; syndicated duplicate controls; historical LLM contamination labels; blinded extraction audit and common-panel ablations.

## Acceptance criteria

Selected families pass coverage, as-of, annotation and latency gates; eligible common-panel evidence is recorded; absent required data blocks completion.

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

Validated as-of wallet/information measurement and common-panel family evidence.
