# Phase 10 — Promotion review

Status: provisional; refine after prerequisite evidence. Owner: current AREPO implementation task.

## Objective

Assemble reproducibility, evidence, security, recovery and product-readiness reports for a separate production decision.

## Why this phase exists

Production changes require a concrete auditable review package and separate authority.

## Research basis

Model protocol promotion sequence and audit limitations; current repository security/recovery and product boundaries. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 09 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

Production deployment includes auto-migrate paths and prior security concerns require evidence-specific review. No v2 deployment authority. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Assemble reproducibility, evidence, security, recovery and product-readiness reports for a separate production decision. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Audit every phase acceptance record and stacked PR dependency against actual code/tests.
2. Reproduce locked analyses including failed/inconclusive arms and verify absence of final-panel retuning.
3. Review security, source rights, auth separation, migration rehearsal, recovery and explicit production rollout diff.
4. Produce review package with unresolved limitations, operational budgets and separately authorised deployment checklist.
5. Run final repository-wide review and mark IMPLEMENTATION ROADMAP COMPLETE — AWAITING REVIEW only when all authorised nonproduction criteria pass.

## Likely modules/files

Promotion report, migration/restore/security rehearsal evidence, phase/PR inventory and checkpoint.

## Data model, API and migration implications

Use versioned v2 entities and immutable artifact manifests. Refine any additive schema proposal from observed prerequisite needs; no automatic production migration or serving API promotion.

## Tests required

Entire relevant backend/frontend validation, dependency/security review, migration rehearsal against isolated restored fixture, reproducibility and recovery review; no production application.

## Acceptance criteria

All nonproduction phase gates complete, evidence/security/recovery/product package reviewed, final tests pass, checkpoint and PRs current; deployment awaits separate user approval.

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

Final review package and IMPLEMENTATION ROADMAP COMPLETE — AWAITING REVIEW checkpoint.
