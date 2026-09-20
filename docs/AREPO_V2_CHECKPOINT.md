# AREPO v2 live checkpoint

Updated: 2026-09-20. Status: Phase 1 accepted; Phase 2 next.

- Current phase: 01 — Feature Store foundations, complete at this checkpoint commit.
- Objective: isolated exact schema, immutable lineage, guarded local migrations and preservation tests.
- Repository: `/Users/DayyanSheikh/Projects/astrolabe`; origin `https://github.com/dayyansheikh/Arepo.git`.
- Branch: `codex/arepo-v2-phase-1-feature-store`, stacked from Phase 0 tip `46799a7`.
- Latest safe commit: `3e69d7f` is the prior tested milestone; this checkpoint's commit adds final reviewed fixes and 610-test acceptance. Resolve its hash with Git history. Production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/14 against Phase 0 branch. Prerequisite https://github.com/dayyansheikh/Arepo/pull/13 targets `arepo-free-production-v1`. Both open draft/unmerged.
- Completed: Phase 0 canonical research reconciliation/plans; Phase 1's 21 isolated entities, exact adapters, immutable writer, causal admission, manifest closure, revisions, local codec, guarded migrations and installed-schema/access drift detection. Final self-review complete.
- Files/modules: `backend/astrolabe/feature_store/`, associated unit/integration tests, one legacy test clock fixture, architecture/decision/phase/review documents. v1 code/configuration/API/scheduler unchanged. Unrelated user files untouched.
- Tests/results: full backend **610 passed, zero skipped**, including actual disposable PostgreSQL 17.11, 38.31s; one existing deprecation warning. Full backend Ruff, canonical checker and whitespace checks passed. See `docs/implementation/PHASE_01_REVIEW.md` for commands and evidence.
- Decisions: D000–D023 in decision log. Generic prospective writes fail closed until Phase 2 durable receipt evidence. Exact numerical storage, local-only explicit targets, immutable records, iterative closure, explicit outcome clocks. Local codec is not full archive equivalence.
- Unresolved questions: runtime source semantics/rights/access and durable receipt implementation belong to Phase 2; event-driven prediction protocols and empirical readiness remain later scope.
- Blockers: none for Phase 1. No validated predictive finding or live prospective collection is claimed.
- Exact next action: commit/push this final acceptance boundary, update draft PR #14 with 610-test results, then branch `codex/arepo-v2-phase-2-sources-clocks-identity` from the tested completion tip. Reload master, Phase 2, clock/identity contract and actual store/client code; refine the plan before implementing durable capture and bounded source verification. Do not repeat Phase 1 implementation.
- Next phase: 02 — Sources, clocks and identities.
- Local PostgreSQL: binaries `/usr/local/opt/postgresql@17/bin`; tests create/stop their own temporary authenticated cluster on a nondefault loopback port. No persistent service/default cluster started. Never substitute production.
- Continuation: one active same-task heartbeat `continue-arepo-v2-implementation`, every 310 minutes. Requested initial anchor 2026-09-20 17:30 Europe/London; saved settings checked at 17:39 contain the interval but no explicit anchor. Exact dispatch timing/cause of delay unverified. No duplicate chain.

## Recovery and protected boundaries

Read AGENTS.md, master/current phase plan, prerequisite outputs and current code/tests before edits. Inspect git status and history. The initial local production branch was an ancestor of fetched production and was not reset. The older lean branch was 3 ahead/0 behind and was never used as a base or imported.

No production merge/deployment/migration, infrastructure/credential/retention change, data deletion, production scan restart, purchase or trade is authorised. Draft PRs and local tests are authorised. Existing production retention and auto-migration paths are not safe v2 entry points. Never run application/scheduler CLIs with inherited database settings. Research candidates are not validated evidence.
