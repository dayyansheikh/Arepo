# Phase 01 — Feature Store v2 foundations

Status: planned. Owner: current AREPO implementation task.

## Objective

Implement the isolated additive core store, exact values, immutable lineage, explicit local migrations and preservation tests.

## Why this phase exists

Exact causal records must exist before collecting evidence or fitting models.

## Research basis

FEATURE_STORE_V2.md numerical preservation, missingness, lineage and archive equivalence; full dictionary; canonical v2 contract. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 00 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

v1 uses storage.db.Base and metadata-diff migrator SCHEMA_VERSION=12. New Base imports would be auto-created by existing entry points. v1 tests exercise SQLite and PostgreSQL DDL, not a full live PostgreSQL integration suite. No v2 code exists at Phase 0. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Implement the isolated additive core store, exact values, immutable lineage, explicit local migrations and preservation tests. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Reload checkpoint/master/Phase 1 and canonical contracts; inspect Phase 0 tested tip/PR. Create codex/arepo-v2-phase-1-feature-store stacked from that tip.
2. Implement exact decimal text, uint256 identifier, UTC and schema-tagged vector adapters with explicit finite/range/precision checks. Preserve raw source spelling independently.
3. Add FeatureStoreBase in astrolabe/feature_store, deliberately absent from v1 Base/migrator/API. Model 21 contract entities and natural key constraints in dependency order.
4. Add FK and manifest closure checks, stable deterministic keys, transactionally idempotent append writer, payload conflict rejection and self-revision cycle/subject checks.
5. Implement dedicated migration ledger with explicit disposable local target. Preview/check must be read-only, no inherited DATABASE_URL or automatic startup integration. Require explicit nonproduction guard before any local PostgreSQL connection.
6. Create SQLite and PostgreSQL immutability guards and new-table access restrictions. Keep v1 table contents/constraints/version untouched; no historical backfill.
7. Implement structural source/feature/origin/prediction/label admission invariants. Runtime source semantics and actual collectors remain Phase 2–3; schema fixtures are synthetic.
8. Test migration fresh and upgrade fixtures twice; injected failure rollback; untouched v1 hashes including float/null/JSON/category; no v2 imports through v1 entry points.
9. Execute PostgreSQL integration on an isolated local service if available; never use Supabase production as a substitute. Record a real blocker if no safe equivalent is available, not a false pass based on DDL compilation.
10. Add local manifest/preservation fixtures covering missing/zero/precision/revision/corruption; full archive backend is deferred but evidence must be exportable without loss.
11. Run targeted and backend regression checks; self-review, update spec if implementation forces a documented change, commit and open/update stacked draft PR. Mark complete only when all acceptance gates pass.

## Likely modules/files

New backend/astrolabe/feature_store/{types,models,repository,migrations,cli}.py; backend/tests/unit/test_feature_store*.py; backend/tests/integration/test_feature_store_postgres.py. Existing v1 metadata unchanged.

## Data model, API and migration implications

Isolated fs2_ schema and ledger; versioned exact typed payloads; explicit local migration only. No public API change.

## Tests required

Exact Decimal (including long mantissas/trailing zeroes), uint256, UTC/timezone and submicro raw preservation; zero/null/NaN/invalid; enum/range/FK/cycle constraints; immutable update/delete including direct SQL; duplicate retry and conflict/concurrency; causality and late labels; fresh/idempotent/failed local migration; populated v1 before/after equality; SQLite AND disposable PostgreSQL execution; v1 metadata isolation and full backend regression.

## Acceptance criteria

All 21 schema entities/types/relations match the canonical catalogue; all required local SQLite/PostgreSQL tests pass; v1 values and metadata unchanged; explicit migration guards pass; no production connections; tested commit and stacked draft PR recorded.

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

Tested schema, exact adapters, guarded local migrations and immutable repositories; hand off source-envelope interfaces and schema/version manifest.
