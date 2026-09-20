# AREPO v2 live checkpoint

Updated: 2026-09-20. Status: Phase 1 in progress; Phase 0 complete.

- Current phase: 01 — Feature Store foundations.
- Objective: implement exact types, isolated schema and guarded local migrations with preservation tests.
- Repository: `/Users/DayyanSheikh/Projects/astrolabe`, origin `https://github.com/dayyansheikh/Arepo.git`.
- Branch: `codex/arepo-v2-phase-1-feature-store`, stacked from Phase 0 tip `46799a7`.
- Latest safe commit: `46799a7` (complete Phase 0 including recovery metadata). Production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/13, open draft against arepo-free-production-v1; not merged.
- Completed: full Phase 0 design/reconciliation and implementation audit; master plan and 11 phase contracts; canonical 21-entity/452-field contract; all 140 research fields mapped; clock/identity/provenance, legacy loss and migration/archive specifications; AGENTS updated; self-review complete.
- Files changed: AGENTS.md; docs/research/2026-09-20; docs/architecture; docs/implementation; this checkpoint; backend/scripts/check_v2_contract.py. Unrelated untracked user files untouched.
- Tests run/results: 105 targeted backend tests passed on disposable SQLite; contract checker passed 13 hashes/140 mappings/60 cards/11 phase files; checker lint passed; disposable v1 schema check passed version 12. Authored-file whitespace passed; research source CRLF/Markdown spacing preserved byte-exact. See docs/implementation/PHASE_00_REVIEW.md for commands and initial environment-only test failure.
- Decisions: D000–D011 in docs/implementation/AREPO_V2_DECISIONS.md. Isolated v2 metadata/ledger; exact decimal text; immutable version records; stricter clock admission; no v1 repairs or automatic lean import.
- Unresolved questions: actual runtime source access/rights, safe local PostgreSQL execution for Phase 1, later event-count readiness. These do not block Phase 0 specification.
- Blockers: none for Phase 0. Desktop curated reads stalled; complete named package recovered from original local research-output. Excluded raw audit/catalogue subdirectories unavailable in curated package, explicitly recorded.
- Phase 1 progress: branch created; isolated 21-entity models, pinned schema, exact decimal/uint/UTC adapters and guarded migration/CLI implemented but not yet accepted. Exact-type tests: 26 passed. Repository/admission writer and migration integration tests remain unfinished. No v1 entry point imports the new store.
- Local PostgreSQL: Homebrew PostgreSQL 17.11 installed; no service started. Use a temporary cluster on a nondefault loopback port for integration tests, then stop it. Never use the default cluster or production database.
- Exact next action: validate local migrations on disposable SQLite and PostgreSQL, including rollback, drift, mutation guards and v1 preservation; then implement the immutable writer/admission checks and remaining Phase 1 acceptance tests. Current draft PR #13 remains open/unmerged; Phase 1 draft PR still to create after a tested commit.
- Next phase: 02 — Sources, clocks and identities, only after all Phase 1 acceptance criteria.
- Continuation: one active same-task heartbeat, `continue-arepo-v2-implementation`, every 305 minutes. Resume from this file; never create a second chain.

## Recovery and protected boundaries

Read AGENTS.md, the master plan, current phase plan and prerequisite outputs before edits. Inspect git status and commits; preserve unrelated changes. The local production branch initially pointed to `8dff5f5ee489f2e9b7ded648f1f18dc679138b51`, an ancestor of fetched production, with no local-only commits. It was not reset. The older lean branch is 3 ahead/0 behind fetched production and was not used as a base.

No production deployments, migrations, infrastructure/credential/retention changes, data deletion, production scan restarts, purchases or trades are authorised. Draft PRs and local tests are authorised. Existing production retention and auto-migration paths are not safe entry points for this programme. Do not run a scheduler/application CLI against inherited database settings.
