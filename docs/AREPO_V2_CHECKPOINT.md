# AREPO v2 live checkpoint

Updated: 2026-09-20. Status: Phase 1 in progress; Phase 0 complete.

- Current phase: 01 — Feature Store foundations.
- Objective: implement exact types, isolated schema and guarded local migrations with preservation tests.
- Repository: `/Users/DayyanSheikh/Projects/astrolabe`, origin `https://github.com/dayyansheikh/Arepo.git`.
- Branch: `codex/arepo-v2-phase-1-feature-store`, stacked from Phase 0 tip `46799a7`.
- Latest safe commit: `0d35316` (tested Phase 1 schema milestone and draft PR recovery record). Writer/admission milestone being checkpointed next. Production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/14, open draft stacked against Phase 0 branch; prerequisite https://github.com/dayyansheikh/Arepo/pull/13 targets arepo-free-production-v1. Neither merged. Phase 1 remains incomplete.
- Completed: full Phase 0 design/reconciliation and implementation audit; master plan and 11 phase contracts; canonical 21-entity/452-field contract; all 140 research fields mapped; clock/identity/provenance, legacy loss and migration/archive specifications; AGENTS updated; self-review complete.
- Files changed: AGENTS.md; docs/research/2026-09-20; docs/architecture; docs/implementation; this checkpoint; backend/scripts/check_v2_contract.py. Unrelated untracked user files untouched.
- Tests run/results: 105 targeted backend tests passed on disposable SQLite; contract checker passed 13 hashes/140 mappings/60 cards/11 phase files; checker lint passed; disposable v1 schema check passed version 12. Authored-file whitespace passed; research source CRLF/Markdown spacing preserved byte-exact. See docs/implementation/PHASE_00_REVIEW.md for commands and initial environment-only test failure.
- Decisions: D000–D011 in docs/implementation/AREPO_V2_DECISIONS.md. Isolated v2 metadata/ledger; exact decimal text; immutable version records; stricter clock admission; no v1 repairs or automatic lean import.
- Unresolved questions: actual runtime source access/rights, safe local PostgreSQL execution for Phase 1, later event-count readiness. These do not block Phase 0 specification.
- Blockers: none for Phase 0. Desktop curated reads stalled; complete named package recovered from original local research-output. Excluded raw audit/catalogue subdirectories unavailable in curated package, explicitly recorded.
- Phase 1 progress: isolated 21-entity schema; exact adapters; append-only writer; structural admission; recursive manifest closure including book levels; revisions; clock/identity checks; local preservation codec; installed-schema/privilege fingerprint; natural-key/enum constraints implemented. Public generic writer rejects prospective writes pending Phase 2 durable receipt evidence. Scientific fixtures remain synthetic. No v1 entry point imports the store.
- Local PostgreSQL: Homebrew PostgreSQL 17.11 installed; no service started. Use a temporary cluster on a nondefault loopback port for integration tests, then stop it. Never use the default cluster or production database.
- Phase 1 validation: latest targeted run completed with 98 passed, including actual temporary PostgreSQL integration, writer concurrency and permission drift. Earlier full backend run passed 581 tests; later additions still need the final full regression run. Ruff passes. A legacy test's monitoring clock was pinned to its existing synthetic collection time; API regression uses a disposable SQLite file because separate legacy engine singletons do not share in-memory databases. Temporary PostgreSQL cluster stopped by fixture teardown.
- Exact next action: finish Phase 1 self-review, reconcile implemented admission/clock semantics with architecture documents, add any missing acceptance regression, run final full backend suite with explicit disposable SQLite and PostgreSQL, commit and update draft PR #14. Do not advance until every acceptance gate passes. The writer/admission work already exists; do not rebuild it.
- Next phase: 02 — Sources, clocks and identities, only after all Phase 1 acceptance criteria.
- Continuation: one active same-task heartbeat, `continue-arepo-v2-implementation`, every 310 minutes per user's revised request. Requested initial anchor: 2026-09-20 17:30 Europe/London. Current saved settings contain the interval but not the explicit start anchor (checked 17:39 London); do not claim exact execution timing without scheduler evidence. No duplicate chain.

## Recovery and protected boundaries

Read AGENTS.md, the master plan, current phase plan and prerequisite outputs before edits. Inspect git status and commits; preserve unrelated changes. The local production branch initially pointed to `8dff5f5ee489f2e9b7ded648f1f18dc679138b51`, an ancestor of fetched production, with no local-only commits. It was not reset. The older lean branch is 3 ahead/0 behind fetched production and was not used as a base.

No production deployments, migrations, infrastructure/credential/retention changes, data deletion, production scan restarts, purchases or trades are authorised. Draft PRs and local tests are authorised. Existing production retention and auto-migration paths are not safe entry points for this programme. Do not run a scheduler/application CLI against inherited database settings.
