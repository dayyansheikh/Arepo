# AREPO v2 live checkpoint

Updated: 2026-09-20 22:57 UTC. Status: Phase 3 in progress; Phases 0–2 complete.

- Current phase/objective: 03 — bounded prospective panel, with frozen sampling/control design, actual causal origins and measured target coverage.
- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin https://github.com/dayyansheikh/Arepo.git.
- Current branch: codex/arepo-v2-phase-3-prospective-panel, stacked from accepted Phase 2 `747485c6724fafd33b60aa222843d7d94116746b`.
- Latest safe prerequisite: Phase 2 `747485c`; this tested Phase 3 milestone is being committed, exact hash/PR will be recorded in the following checkpoint commit.
- Draft PR: Phase 3 draft being opened against Phase 2; see following update. Prerequisite https://github.com/dayyansheikh/Arepo/pull/15 is complete, open draft/unmerged, stacked on #14/#13. Ultimate production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Completed: Phase 0 canonical foundation; Phase 1 isolated immutable store; Phase 2 source journals/admission, exact identities and bounded replay, accepted with 685 tests and new three-source runtime run. Phase 3 milestone: pure versioned sampling/control planner and causal receipt-time target rules; refined phase and frame-adapter contracts.
- Files/modules changed in Phase 3: new research_panel/{__init__,sampling,targets}.py, test_research_panel_planning.py, Phase 3 review/frame contract/plan, decision D030 and recovery docs. No v1/config/API/scheduler/frontend changes or additional runtime data collection.
- Tests/results: final full backend **704 passed**, zero skipped, 38.45s, including disposable PostgreSQL 17.11; 19 targeted planning tests. Ruff/contract/whitespace checks passed. One existing Starlette/httpx warning.
- Self-review: fixed future values/quality leaking through as-of inventory metadata, late identity use, ambient Decimal rounding and noncanonical timezones. Control inclusion and conditional matching weights are distinct; multiple roles do not create independent observations. All exclusions and control shortages remain explicit.
- Decisions: D000–D030. Exact rational inclusion probabilities retained; nonterminating decimals stay null with explicit representation state. Pure frame-status claims never confer population inference eligibility. No model, panel, economic or predictive result claimed.
- Unresolved: actual prospective frame adapter, population enumeration/cost, durable panel protocol/seed/frame/sample/feature-read/origin writing, separate leases, collectors and live pilot. Source-run build binding covers source modules; the panel needs its own immutable computation build. Phase 3 acceptance remains incomplete.
- Exact next action: read PHASE_03_FRAME_CONTRACT.md and PHASE_03_REVIEW.md, then implement/test an isolated Gamma keyset frame adapter with raw receipts, pinned source/parser, exact cursor parentage, unchanged scope, duplicate/conflict preservation and explicit incomplete states. Current official docs list after_cursor/next_cursor, max limit100, no offset; active is not in its parameter list. Test first, perform only a bounded first-page measurement, and use measured bytes/time to freeze a complete-frame budget. Do not call a partial page a representative universe. Then follow remaining Phase 3 milestones.
- Next planned phase: 04 — baselines/experiments, only after full Phase 3 acceptance and sufficient clean data.
- Blockers: none requiring user action. Saving before primary allowance exhaustion: 22:57 UTC primary91% / weekly14% used, ordinary usage allowed. No reset credit redeemed by this agent. Continue with available allowance; stop if longer-term allowance is unavailable.
- Continuation: one existing same-task heartbeat continue-arepo-v2-implementation, every310minutes. Explicit heartbeat arrived 22:23:10 UTC; no duplicate chain. Earlier requested17:30 London dispatch delay remains unverified.
- Preserved evidence: all roots in four Phase2 evidence JSONs. New primary source run data-dumps/fs2_capture_ae0d089c24e24bc18f1e6f548c878432 uses exact source implementation `54be417`; preserve original journals. SQL is an index. Do not reinterpret old runs under changed builds or promote earlier diagnostics.
- Local PostgreSQL binaries: /usr/local/opt/postgresql@17/bin; tests create/stop only their isolated temporary loopback cluster.

## Recovery and protected boundaries

Read AGENTS.md, master/current phase plan, prerequisite outputs and relevant code/tests;
inspect Git status/branch/commits/draft PR. Preserve unrelated untracked prompts/logs/PIDs,
email docs and overnight residue. Never merge/deploy/migrate production, alter infrastructure/
credentials/retention, delete research data, restart production scans, buy data or trade.
No production reset or lean-branch import occurred. Proposed research is not validated evidence.
