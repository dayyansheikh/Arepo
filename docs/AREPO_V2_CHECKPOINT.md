# AREPO v2 live checkpoint

Updated: 2026-09-21 03:49 UTC. Status: Phase 3 in progress; Phases 0–2 complete.

- Current phase/objective: 03 — bounded prospective panel, with frozen sampling/control design, actual causal origins and measured target coverage.
- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin https://github.com/dayyansheikh/Arepo.git.
- Current branch: codex/arepo-v2-phase-3-prospective-panel, stacked from accepted Phase 2 `747485c6724fafd33b60aa222843d7d94116746b`.
- Latest safe implementation commit: `bf734a0`; bounded frame adapter passed 732 tests; measured first-page evidence recorded; v2 streaming/full-frame budget refinement validated with 740 tests and being committed; accepted Phase 2 prerequisite `747485c`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/16, open draft against Phase 2. Prerequisite https://github.com/dayyansheikh/Arepo/pull/15 is complete, open draft/unmerged, stacked on #14/#13. Ultimate production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Completed: Phase 0 canonical foundation; Phase 1 isolated immutable store; Phase 2 source journals/admission, exact identities and bounded replay, accepted with 685 tests and new three-source runtime run. Phase 3 milestone: pure versioned sampling/control planner and causal receipt-time target rules, now bounded keyset frame adapter with pinned code, raw receipts, cursor/duplicate/incomplete handling and one-page CLI.
- Files/modules changed in Phase 3: research_panel/{__init__,sampling,targets,frame,frame_cli,build_identity}.py, frame/planning tests, isolated feature_store/{capture,sources}.py keyset support; Phase 3 contracts, decisions D030-D031 and recovery docs. No v1/config/API/scheduler/frontend changes or additional runtime data collection.
- Tests/results: final full backend **740 passed**, zero skipped, 40.32s, including disposable PostgreSQL 17.11; 36 frame tests; full Ruff/contract/whitespace checks passed. Ruff/contract/whitespace checks passed. One existing Starlette/httpx warning.
- Self-review: fixed future values/quality leaking through as-of inventory metadata, late identity use, ambient Decimal rounding and noncanonical timezones. Control inclusion and conditional matching weights are distinct; multiple roles do not create independent observations. All exclusions and control shortages remain explicit.
- Decisions: D000–D032. Exact rational inclusion probabilities retained; nonterminating decimals stay null with explicit representation state. Pure frame-status claims never confer population inference eligibility. No model, panel, economic or predictive result claimed.
- Unresolved: runtime frame measurement, population enumeration/cost, durable panel protocol/seed/frame/sample/feature-read/origin writing, separate leases, collectors and live pilot. Frame source and panel builds now pinned; actual origin/computation writer is still outstanding. Phase 3 acceptance remains incomplete.
- Exact next action: finish validating/commit the measured v2 streaming enumeration protocol, then run the isolated `frame_cli enumerate` with first-page journal `data-dumps/fs2_capture_c63c72a0fe194f47824ccc862b0619cd` as cost evidence. Frozen ceilings are in PHASE_03_FRAME_CONTRACT.md. Preserve any incomplete stop; do not call it a representative population. Then persist actual frame/sample/feature-read/origin data and remaining collectors/pilot gates.
- Next planned phase: 04 — baselines/experiments, only after full Phase 3 acceptance and sufficient clean data.
- Blockers: none requiring user action. Current allowance checked 03:30 UTC: primary5% / weekly16% used, ordinary usage allowed. No reset credit redeemed.
- Continuation: 04:30 London heartbeat ran at03:30:10 UTC. Replaced its consumed one-shot with one same-task heartbeat `arepo-v2-continuation-at-09-40`, due 2026-09-21 09:40 London (310 minutes after trigger). Prompt unchanged including scheduling instruction; one active chain only. No separate-task workaround.
- Preserved evidence: all roots in four Phase2 evidence JSONs. New primary source run data-dumps/fs2_capture_ae0d089c24e24bc18f1e6f548c878432 uses exact source implementation `54be417`; preserve original journals. SQL is an index. Do not reinterpret old runs under changed builds or promote earlier diagnostics.
- Local PostgreSQL binaries: /usr/local/opt/postgresql@17/bin; tests create/stop only their isolated temporary loopback cluster.

## Recovery and protected boundaries

Read AGENTS.md, master/current phase plan, prerequisite outputs and relevant code/tests;
inspect Git status/branch/commits/draft PR. Preserve unrelated untracked prompts/logs/PIDs,
email docs and overnight residue. Never merge/deploy/migrate production, alter infrastructure/
credentials/retention, delete research data, restart production scans, buy data or trade.
No production reset or lean-branch import occurred. Proposed research is not validated evidence.
