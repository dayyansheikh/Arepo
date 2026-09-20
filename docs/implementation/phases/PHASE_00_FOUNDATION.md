# Phase 00 — Canonical foundation

Status: complete; draft PR https://github.com/dayyansheikh/Arepo/pull/13. Owner: current AREPO implementation task.

## Objective

Convert the completed research into an implementable, repository-grounded preservation and measurement contract.

## Why this phase exists

Permanent implementation memory and preservation must precede schema or retention changes.

## Research basis

All 13 curated documents; Feature Store prose and dictionary reconciled explicitly; report B/V/Z and audit limitations. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

None; verified production base and supplied research. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

Production SHA e50f063; branch created in original repository. v1 Float/JSON records, missing event identity propagation, collector-clock quotes, mutable minute microstructure, auto-migration and optional prune-only retention verified. No v2 store exists. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Convert the completed research into an implementable, repository-grounded preservation and measurement contract. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. No schema implementation, collection, models or public redesign.

## Ordered implementation tasks

1. Verify root/origin/status, fetch production and reconcile audit SHA. Preserve unrelated files; branch from current production, never lean branch.
2. Read handoff then every artefact; preserve unchanged copies with hashes and explicitly list unavailable supporting raw evidence.
3. Inspect v1 models, normalisers, discovery/scoring/flow, freeze/outcomes, migration/config/scheduler/API and tests. Record actual semantics, not docstring assumptions.
4. Reconcile all 140 dictionary fields and every prose entity into exact field/types, keys, relationships, units, clocks, version/missingness/provenance and retention contracts.
5. Document legacy mapping and irrecoverable history; specify migration isolation and archive equivalence before any destructive option.
6. Create master dependency map, detailed Phase 0–3 contracts, provisional Phase 4–10 contracts, decision log and checkpoint. Update AGENTS.md.
7. Configure exactly one 305-minute same-task continuation and record its ID. Run safe local checks with database settings isolated.
8. Self-review source-to-contract traceability, keys/types/FKs and phase dependencies. Commit coherent docs and open a draft PR against production; record final state.

## Likely modules/files

AGENTS.md; docs/research/2026-09-20; docs/architecture; docs/implementation; docs/AREPO_V2_CHECKPOINT.md.

## Data model, API and migration implications

Documentation only; canonical future schema and local migration sequence designed, not applied.

## Tests required

Package hashes/counts and 140-field exact coverage; CSV/Markdown experiment agreement; internal contract references, all 21 entities, all 11 phase plans; git diff whitespace/scope review; selected existing storage/migration/timing/freeze/flow/scheduler tests on temporary SQLite.

## Acceptance criteria

All 20 user Phase 0 outputs exist, safe tests pass, contracts self-reviewed, coherent commits and draft PR recorded; no runtime/production modification.

## Exit checklist

- [x] Prerequisites reloaded and plan refined against real outputs.
- [x] All scoped tasks and acceptance criteria satisfied; limitations explicit.
- [x] Required tests passed with exact command/target/result recorded.
- [x] Diff self-reviewed for causal leakage, data loss, unrelated changes and protected boundaries.
- [x] Documentation/decision log/master status current.
- [x] Coherent safe work committed; branch and draft PR/dependency recorded.
- [x] Checkpoint updated with safe commit, files, tests, blockers and exact next action.

## Protected boundaries

Never fabricate prospective observations, tune on final confirmation, or treat repeated rows as independent events. Preserve complete discovery separately from public limits and sampled deep collection. Archive equivalence does not authorise deletion. A protected action requires the user's explicit decision; record BLOCKED — USER DECISION REQUIRED with the concrete action. Missing access/data is a real blocker; synthetic fixtures are not a substitute for empirical acceptance.

## Handoff/output

Canonical contracts, legacy loss register, phase memory, tested docs commit and Phase 0 draft PR.

## Completion evidence

Implementation/specification commit 07ee1f5b704ea437f246488cf6cd61363338c94e. Draft PR #13 targets production e50f063 and remains unmerged. See ../PHASE_00_REVIEW.md for 105 passing local tests and contract validation. Recovery metadata is committed immediately after the reviewed foundation commit.
