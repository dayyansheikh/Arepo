# AREPO v2 live checkpoint

Updated: 2026-09-20 21:43 UTC. Status: Phase 2 in progress; Phases 0–1 complete.

- Current phase: 02 — Sources, clocks and identities.
- Objective: durable receipt capture, source semantics, evidence-linked identity and as-of dependence views before prospective collection.
- Repository: `/Users/DayyanSheikh/Projects/astrolabe`; origin `https://github.com/dayyansheikh/Arepo.git`.
- Branch: `codex/arepo-v2-phase-2-sources-clocks-identity`, stacked from accepted Phase 1 `43999b5`.
- Latest safe commit: `d870e0792c360e5c8709cd8d52e6833725ad19b8` — tested Phase 2 capture/parser milestone; accepted Phase 1 prerequisite is `43999b5`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/15, open draft against Phase 1 branch, unmerged. Prerequisites: https://github.com/dayyansheikh/Arepo/pull/14 (Phase 1, complete), https://github.com/dayyansheikh/Arepo/pull/13 (Phase 0, complete). Both draft/unmerged; ultimate production base `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Completed: Phase 0 canonical specification/plans; Phase 1 isolated 21-entity store, immutable lineage, migrations and preservation, accepted with 610 tests. Phase 2 milestone: allowlisted source contracts, bounded raw-before-parse journal, post-fsync acknowledgements, exact source parsers, as-of identity/dependence helpers, four preserved successful public diagnostics.
- Files/modules: new `feature_store/{sources,capture,source_parsers,identity_views}.py`, three unit-test files, Phase 2 review/runtime evidence, plans and decisions. No v1/client/config/API/scheduler modifications in Phase 2. Unrelated user residue untouched.
- Tests/results: full backend **649 passed, zero skipped**, 39.20s, including disposable PostgreSQL 17.11; one existing Starlette/httpx warning. 39 targeted new tests passed; full backend Ruff, contract checker and whitespace checks passed. See `docs/implementation/PHASE_02_REVIEW.md`.
- Live evidence: four bounded public GETs returned 200 (Gamma, CLOB book, Data API v2 trades, Coinbase ticker). Raw/receipt/parse/ack artefacts preserved at `data-dumps/fs2_capture_2d3194413f0d4429ad65603a2e8f6102`, excluded from Git; committed summary hashes in `PHASE_02_RUNTIME_EVIDENCE.json`. All are diagnostic, **not research-admitted**. Preserve this directory.
- Decisions: D000–D025. Source/parse artefact durability differs from later index transaction durability. Generic prospective writer remains closed. New trade source uses v2; v1 untouched. Chain/collateral/economic groups and fill identity stay unresolved without evidence.
- Unresolved questions: receipt-to-store bridge and registry admission; source-specific parse-completion clock; chain/collateral evidence; native timestamp unit/semantics where ambiguous; rights beyond diagnostics; stream gaps/reconnect verification. Phase 2 is not complete.
- Blockers: none at recovery. At 21:43 UTC the five-hour allowance was 1% used, weekly 79% used, ordinary usage allowed. Resumed after the prior window checkpoint; no reset credit consumed. The previous checkpoint's 17:15 timestamp was an approximate administrative entry, later than its 17:11 commit; it is not research timing evidence.
- Exact next action: read Phase 2 review's remaining-work list; finish cursor/deadline/filesystem-failure regression, then design/test the durable receipt-to-store bridge and registry admission against actual Phase 1 writer constraints. Inspect current code and the preserved four captures. Never label the earlier generic JSON parse time as completion of a later source-specific parse. Continue identity/stream and admission matrix work; keep prospective writes gated until evidence checks pass.
- Next planned phase: 03 — bounded prospective panel, only after complete Phase 2 acceptance/tests/self-review/commit/draft PR.
- Local PostgreSQL: binaries `/usr/local/opt/postgresql@17/bin`; test fixture creates/stops only its own authenticated temporary loopback cluster. No persistent service/default cluster or production database used.
- Continuation: one existing same-task heartbeat `continue-arepo-v2-implementation`, every 310 minutes. Requested initial anchor was 17:30 Europe/London; saved settings checked at 17:39 contain interval but no explicit anchor. Dispatch delay cause unverified. No duplicate chain.

## Recovery and protected boundaries

Read AGENTS.md, master/current phase plan, prerequisite outputs and current code/tests. Inspect status/history/draft PR before edits. Production and the older lean branch were never reset/merged/cherry-picked. Never merge/deploy/migrate production, change infrastructure/credentials/retention, delete research data, restart scans, buy data or trade. Do not run application/scheduler CLIs with inherited database settings. Source access is not evidence of predictive edge; candidate research remains unvalidated.
