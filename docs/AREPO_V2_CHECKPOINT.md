# AREPO v2 live checkpoint

Updated: 2026-09-21. Status: Phase 3 in progress; tool access restored in the main task. Complete-frame data gate outstanding. Phases 0–2 complete.

- Current phase/objective: 03 — bounded prospective panel, with frozen sampling/control design, actual causal origins and measured target coverage.
- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin https://github.com/dayyansheikh/Arepo.git.
- Current branch: codex/arepo-v2-phase-3-prospective-panel, stacked from accepted Phase 2 `747485c6724fafd33b60aa222843d7d94116746b`.
- Latest safe implementation commit: `84cf4b132bfb9cca4772b0cce0a5a694c7e8ce57` — D035 finite sampler capacity, full **755 tests passed**; original-reader milestone `2eb7ec4`. Current evidence/checkpoint form the following docs-only commit. Earlier frame milestone `726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0`; accepted Phase 2 `747485c`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/16, open draft against Phase 2. Prerequisite https://github.com/dayyansheikh/Arepo/pull/15 complete, open draft/unmerged, stacked on #14/#13. Ultimate production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Completed: Phase 0 canonical foundation; Phase 1 isolated immutable store; Phase 2 source journals/admission, exact identities and bounded replay. Phase 3 milestones: pure sampling/control/receipt-target rules; isolated keyset frame journal, source+panel build binding, bounded CLI, raw/parsed/page manifests, cursor/scope/duplicate/conflict/clock/error checks, crash-safe read-only recovery, streaming verification and measured-capacity preflights.
- Files/modules changed: research_panel/{__init__,sampling,targets,frame,frame_cli,build_identity,original_reader}.py; planning/frame tests; isolated feature_store/{capture,sources}.py keyset support; phase/review/frame/panel-journal contracts, decisions D030–D035, three new evidence JSONs and recovery docs. No v1/config/API/scheduler/frontend changes.
- Tests/results: latest full backend **755 passed**, zero skipped, 72.43s, including actual disposable PostgreSQL 17.11; 39 frame tests, 10 original-reader tests and 21 planning tests (rerun after the golden assertion). Full Ruff, canonical contract checker and whitespace checks passed. Final committed-code synthetic capacity rerun also passed, with unchanged plan hash. One existing Starlette/httpx warning. Local test DBs only; email disabled. Initial global-Python launch error was corrected before the successful full regression.
- Measured first page: `bf734a0`, 100 rows, 557,140 raw bytes, 1,501,764 retained bytes, 157,199,875ns request-to-receipt; continuing cursor, incomplete. PHASE_03_FIRST_PAGE_EVIDENCE.json.
- Enumeration attempt 1: `f66dea1`, 410 attempts / 409 complete pages / 40,900 rows; stopped at 256MiB raw cap with partial 410th response preserved. Raw268,435,456 / retained 654,055,783 / peak resident 202,407,936 bytes. Incomplete. PHASE_03_ENUMERATION_ATTEMPT_1.json.
- Enumeration attempt 2: `726cec2`, 1,000 complete pages /100,000 distinct market IDs, still continuing. 99,956 eligible row identities and 44 unresolved, no observed duplicates/conflicts within prefix. Raw644,897,535 / retained 1,577,956,669 / peak resident 343,457,792 bytes. Request-cap stop; incomplete. PHASE_03_ENUMERATION_ATTEMPT_2.json. Final verification overlapped backend regression, so whole-command elapsed is not an isolated performance benchmark.
- Self-review: checked exact primitives and clocks, scope/cursor parentage, documented omitted-cursor termination, failed/torn attempts, conflicting market/condition/token identity, build drift, synthetic/live separation, capacity stops and bounded memory. All raw history retained. No source exhaustion, population inference, pilot acceptance, model result or predictive improvement is claimed.
- Decisions: D000–D035. Cost-based larger attempts are separately frozen; old failed attempts remain failed. Full frame manifest references immutable per-page rows rather than duplicating all data in memory/report. Exact rational inclusion weights retained from planning milestone. Source events are not independent economic groups.
- Required data gate: a complete sampling frame is still unavailable under the measured bounds. A 100,000-row prefix cannot establish representativeness. No protected user decision currently required. Historical allowance check was 85% primary / 29% weekly used; this is not current allowance evidence. The latest main-task allowance check found 87% primary and 45% weekly used, with ordinary usage allowed. Progress is checkpointed before the five-hour window is likely to end; this is not a claim of weekly exhaustion or a protected-access blocker. No exhaustion is inferred and no reset credit was redeemed.
- Exact next action: read `docs/implementation/PHASE_03_CAPACITY_REFINEMENT.md` and implement its separately gated finite 4,000-request capacity protocol. Verify current disk/RAM; retain existing defaults, require actual prior request-ceiling proof, test/self-review/commit before any new source request. The sampler now explicitly supports at most 400,000 members and its synthetic sizing passed. Do NOT rerun unchanged 1,000-page enumeration. Original-build consumption is resolved by D034 and actual read evidence. After a usable complete interval frame exists, follow the panel journal contract for durable protocol/seed/sample/actual read/computation/origin records, collectors/targets and the pilot. Phase 4 remains gated.
- New evidence: `PHASE_03_ORIGINAL_READ_EVIDENCE.json` records actual original-code verification of the existing 100,000-row journal without source requests. Its incomplete status and original hashes/clocks remain unchanged. D035 committed-code synthetic 400,000-member capacity used 320,897,024 resident bytes and 27,764,313,417ns; exact build/fixture/result in `PHASE_03_SAMPLING_CAPACITY_EVIDENCE.json`; synthetic capacity is not live source/panel evidence. Collection caps remain unchanged until the next tested milestone.
- Unresolved: complete population enumeration, interval freshness/churn, durable panel actual-read integration, durable panel facts/leases, family coverage, selected external-source admission and actual pilot timing/control/target acceptance. Economic grouping, native event-time and complete trade/depth coverage remain evidence-dependent.
- Next planned phase: 04 — baselines/experiments, only after full Phase 3 acceptance and sufficient clean data.
- Continuation: one same-task heartbeat `arepo-v2-continuation-at-18-13`, scheduled for 2026-09-21 18:13 Europe/London (+310 minutes from this continuation), with the user's exact prompt; target task `01a0bd77-ed42-79d3-8c5b-2c207b0ead04`. The prior 09:40 automation was removed before replacement. That separate task made docs-only commit `8a55335`; preserved and reconciled here. It is no longer running. No duplicate chain created.
- Preserved frame roots: data-dumps/fs2_capture_c63c72a0fe194f47824ccc862b0619cd; data-dumps/fs2_capture_95cbb8cdd4334bc1836249e7d7864473; data-dumps/fs2_capture_3a4f80db7fa94d248fc16e1397af4c71. Exact original code commits/hashes in the evidence JSONs. Original-build readers intentionally reject changed code; do not disable that guard or reinterpret old journals under new parsers.
- Earlier evidence: four Phase 2 evidence JSONs; admitted primary source run data-dumps/fs2_capture_ae0d089c24e24bc18f1e6f548c878432 uses exact source implementation `54be417`. SQL is an index; primary journals remain authority.
- Local PostgreSQL binaries: /usr/local/opt/postgresql@17/bin. Tests create/stop only their isolated temporary loopback cluster.

## Historical continuation access checkpoint — 2026-09-21 12:05 UTC

Resolved in the main task at 13:03 Europe/London: supported usage and automation tools
are callable, allowance verified and one next heartbeat saved. The separate task's
access failure and its docs-only commit `8a55335` are preserved below as historical facts.

**BLOCKED — REQUIRED ACCESS UNAVAILABLE.** The current run cannot read live usage limits or
manage the next continuation through supported app tools. A usage-tool call returned
unavailable; automation_update was not callable and disappeared from subsequent discovery.
The computer-use fallback explicitly denied access to Codex for safety reasons; no bypass
was attempted. This establishes unavailable verification/scheduling access, not exhausted
allowance. Under the user's stop condition, implementation and collection were stopped.
No protected approval is requested and no programme gate is waived.

Read checkpoint/master/AGENTS/current phase, frame and journal contracts, both enumeration
reports, current sampling/build code, relevant test coverage and configuration; inspected
Git status/history and draft PR #16. Branch still matches the existing Phase 3 stack, with
safe recovery tip `4d3d8a7` before this docs-only checkpoint. PR #16 remains open/draft against
Phase 2, with existing checks successful. Unrelated untracked files were preserved. No code,
data, database, source collection, deployment or production state was changed. The prior
743-test result remains historical; backend tests were not rerun for this documentation-only
checkpoint. Read-only canonical and whitespace checks validate this checkpoint. No new phase
acceptance, complete-frame evidence or research result is claimed. This recovery update is a
local docs-only commit; the existing remote draft PR was inspected and left unchanged.

## Recovery and protected boundaries

Read AGENTS.md, master/current phase plan, prerequisite outputs and relevant code/tests;
inspect Git status/branch/commits/draft PR. Preserve unrelated untracked prompts/logs/PIDs,
email docs and overnight residue. Never merge/deploy/migrate production, alter infrastructure/
credentials/retention, delete research data, restart scans, buy data or trade.
No production reset or lean-branch import occurred. Proposed research is not validated evidence.
