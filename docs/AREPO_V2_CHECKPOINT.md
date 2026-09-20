# AREPO v2 live checkpoint

Updated: 2026-09-20. Status: Phase 0 complete; ready to begin Phase 1.

- Current phase: 00 — canonical foundation.
- Objective: reconcile the supplied research with production code and freeze a reviewable implementation contract.
- Repository: `/Users/DayyanSheikh/Projects/astrolabe`, origin `https://github.com/dayyansheikh/Arepo.git`.
- Branch: `codex/arepo-v2-phase-0-foundation`.
- Latest safe implementation commit: `07ee1f5b704ea437f246488cf6cd61363338c94e`; recovery metadata follows in this commit. Production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/13, open draft against arepo-free-production-v1; not merged.
- Completed: full Phase 0 design/reconciliation and implementation audit; master plan and 11 phase contracts; canonical 21-entity/452-field contract; all 140 research fields mapped; clock/identity/provenance, legacy loss and migration/archive specifications; AGENTS updated; self-review complete.
- Files changed: AGENTS.md; docs/research/2026-09-20; docs/architecture; docs/implementation; this checkpoint; backend/scripts/check_v2_contract.py. Unrelated untracked user files untouched.
- Tests run/results: 105 targeted backend tests passed on disposable SQLite; contract checker passed 13 hashes/140 mappings/60 cards/11 phase files; checker lint passed; disposable v1 schema check passed version 12. Authored-file whitespace passed; research source CRLF/Markdown spacing preserved byte-exact. See docs/implementation/PHASE_00_REVIEW.md for commands and initial environment-only test failure.
- Decisions: D000–D011 in docs/implementation/AREPO_V2_DECISIONS.md. Isolated v2 metadata/ledger; exact decimal text; immutable version records; stricter clock admission; no v1 repairs or automatic lean import.
- Unresolved questions: actual runtime source access/rights, safe local PostgreSQL execution for Phase 1, later event-count readiness. These do not block Phase 0 specification.
- Blockers: none for Phase 0. Desktop curated reads stalled; complete named package recovered from original local research-output. Excluded raw audit/catalogue subdirectories unavailable in curated package, explicitly recorded.
- Exact next action: reload master/Phase 1 plan and canonical specification, inspect prerequisite outputs/code/tests, create codex/arepo-v2-phase-1-feature-store from the Phase 0 tested tip, then implement exact types and isolated schema locally. Investigate safe disposable PostgreSQL availability; no production substitute.
- Next phase: 01 — Feature Store v2 schema, explicit local migrations and preservation tests; only after Phase 0 acceptance.
- Continuation: one active same-task heartbeat, `continue-arepo-v2-implementation`, every 305 minutes. Resume from this file; never create a second chain.

## Recovery and protected boundaries

Read AGENTS.md, the master plan, current phase plan and prerequisite outputs before edits. Inspect git status and commits; preserve unrelated changes. The local production branch initially pointed to `8dff5f5ee489f2e9b7ded648f1f18dc679138b51`, an ancestor of fetched production, with no local-only commits. It was not reset. The older lean branch is 3 ahead/0 behind fetched production and was not used as a base.

No production deployments, migrations, infrastructure/credential/retention changes, data deletion, production scan restarts, purchases or trades are authorised. Draft PRs and local tests are authorised. Existing production retention and auto-migration paths are not safe entry points for this programme. Do not run a scheduler/application CLI against inherited database settings.
