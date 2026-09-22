# AREPO v2 live checkpoint

Updated: 2026-09-22. Status: Phase 3 incomplete — D040 durable development selection passed its local full-frame measurement: 107 draws/strata, all rows retained. Original-build selection consumption and origins/collectors/pilot remain. Phases 0–2 complete.

- Current phase/objective: 03 — bounded prospective panel, with frozen sampling/control design, actual causal origins and measured target coverage.
- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin https://github.com/dayyansheikh/Arepo.git.
- Current branch: codex/arepo-v2-phase-3-prospective-panel, stacked from accepted Phase 2 `747485c6724fafd33b60aa222843d7d94116746b`.
- Latest safe implementation commit: `018dbd3916448f922ef79425aead3d2b5aac735d` — D040 durable development selection, **841 tests passed**. Original frame implementation remains `41fcb0170c7d71716873847639dc181ea12422aa`; complete-frame evidence `13dd2cb`. Accepted Phase 2 `747485c`.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/16, open draft against Phase 2. Prerequisite https://github.com/dayyansheikh/Arepo/pull/15 complete, open draft/unmerged, stacked on #14/#13. Ultimate production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Completed: Phase 0 canonical foundation; Phase 1 isolated immutable store; Phase 2 source journals/admission, exact identities and bounded replay. Phase 3 milestones: pure sampling/control/receipt-target rules; isolated keyset frame journal, source+panel build binding, bounded CLI, raw/parsed/page manifests, cursor/scope/duplicate/conflict/clock/error checks, crash-safe read-only recovery, streaming verification and measured-capacity preflights.
- Files/modules changed: research_panel/{__init__,sampling,targets,frame,frame_cli,build_identity,original_reader}.py; planning/frame tests; isolated feature_store/{capture,sources}.py keyset support; phase/review/frame/panel-journal contracts, decisions D030–D037, original-read/sampler sizing and three enumeration evidence JSONs and recovery docs. No v1/config/API/scheduler/frontend changes.
- Tests/results: latest full backend **851 passed**, zero skipped, 105.20s, including disposable PostgreSQL 17.11 and 10 new original-selection cases. Earlier 53 focused reader/selection/capacity checks passed before the last canonical-source-path case was added. Full Ruff, canonical contract checker and whitespace checks pass. One existing Starlette/httpx warning. Local test DBs only; email disabled.
- Measured first page: `bf734a0`, 100 rows, 557,140 raw bytes, 1,501,764 retained bytes, 157,199,875ns request-to-receipt; continuing cursor, incomplete. PHASE_03_FIRST_PAGE_EVIDENCE.json.
- Enumeration attempt 1: `f66dea1`, 410 attempts / 409 complete pages / 40,900 rows; stopped at 256MiB raw cap with partial 410th response preserved. Raw268,435,456 / retained 654,055,783 / peak resident 202,407,936 bytes. Incomplete. PHASE_03_ENUMERATION_ATTEMPT_1.json.
- Enumeration attempt 2: `726cec2`, 1,000 complete pages /100,000 distinct market IDs, still continuing. 99,956 eligible row identities and 44 unresolved, no observed duplicates/conflicts within prefix. Raw644,897,535 / retained 1,577,956,669 / peak resident 343,457,792 bytes. Request-cap stop; incomplete. PHASE_03_ENUMERATION_ATTEMPT_2.json. Final verification overlapped backend regression, so whole-command elapsed is not an isolated performance benchmark.
- Enumeration attempt 3: `5cdb2d2`, 74 attempts /73 complete pages /7,300 rows plus partial response 74. Incomplete, `page_error`/`TimeoutError` after 15s. Raw46,929,025 /retained112,224,334 /peak resident118,849,536 bytes. Original-code prior-capacity verification succeeded. Root `data-dumps/fs2_capture_ff7f05b057b647109b4239ca781e10fb`; full evidence in PHASE_03_ENUMERATION_ATTEMPT_3.json. 7,256 eligible rows, 44 unresolved; no terminal or population inference.
- Enumeration attempt 4: `b93f9aa`, 204 verified attempts /200 complete pages /20,000 rows, with 3 bounded retries (2 recovered). Incomplete, `retry_exhausted`; unrecovered `ConnectError` and `TimeoutError`. Raw132,580,143 /retained318,668,335 /peak resident141,836,288 bytes. 19,956 eligible rows, 44 unresolved, no duplicates/conflicts or terminal. Root `data-dumps/fs2_capture_8e6a8d4a22b846ae91ca70f70f6b3939`; evidence in PHASE_03_ENUMERATION_ATTEMPT_4.json.
- Self-review: source/clock/identity/raw preservation, internally frozen seed, actual read/projection/cutoff ordering, exact rational replay, unknown and unmapped inventory, duplicate handling, failed-run refusal, original-frame policy/page closure, bounded storage/time and changed-build refusal. Source exhaustion is established only for attempt 5. No population inference, pilot acceptance or predictive improvement is claimed.
- Decisions: D000–D040. New modules/tests: research_panel/{selection,selection_cli}.py and tests/unit/test_research_panel_selection.py. D040 records full inventory and actual clocks, with internally generated seed, exact scheduled draws and explicit reconstructed/synthetic provenance. No origins/triggers/controls are admitted. Original history is unchanged; source events are not independent economic groups.
- Required data gate: complete-frame blocker **cleared** by verified attempt 5. Earlier failures remain incomplete. No current protected approval/access blocker. Latest allowance check this continuation: 28% primary /82% weekly used; ordinary usage available, no reset credit redeemed.
- Completed attempt 5: `data-dumps/fs2_capture_eaec9cd7e8684953952e1b683c33dd3a`, implementation `41fcb0170c7d71716873847639dc181ea12422aa`. 1,755 pages, 175,427 distinct markets, 175,383 mapped eligible rows, 44 unresolved; no retries, errors, duplicates or conflicting identities. State `exhausted_consistent`, terminal observed. Raw 1,115,618,904 /retained 2,728,778,097 /peak resident 478,052,352 bytes; whole-command 514,493,751,417ns. Actual interval 23:30:55–23:36:47 UTC on September 21; sealed at 23:37:32 UTC. Source/clock/manifest verification passed; CLI exited 0. See PHASE_03_ENUMERATION_ATTEMPT_5.json. Original capacity-read root `data-dumps/fs2_frame_read_b9ef454ed5e64e8f82fa623e464135b2`; CLI `data-dumps/fs2_attempt5_cli_20260921T233100Z.json`. No collector remains active.
- Completed local selection: `data-dumps/fs2_selection_56ff541cb2c74477b5ae56de1a78ad54`, implementation `018dbd3916448f922ef79425aead3d2b5aac735d`; CLI `data-dumps/fs2_selection_attempt1_cli.json`, exit 0 and independent replay passed. Retains 175,427 rows, 175,383 sampling members, 44 unresolved identities; 107 scheduled draws in 107 strata, exact weights. Category missing for all mapped rows; close missing 1,168, liquidity 25,879, metadata probability 65. No metadata-based exclusions or invented category mappings. Retained 566,741,238 /peak resident 294,977,536 bytes; elapsed 146,486,870,416ns. Reconstructed development only, no source requests/origins/controls. No active measurement remains. PHASE_03_SELECTION_ATTEMPT_1.json preserves clocks/hashes.
- Exact next action: commit reviewed/tested D041 original-selection reader and run one local `selection_cli inspect-original` on the saved D040 selection under original `018dbd3916448f922ef79425aead3d2b5aac735d`. Preserve old plan/seed/clocks and record only a new actual read receipt. Do not edit panel/source Python while that verification runs. Then refine explicit freshness/trigger/control/origin contracts and pilot, including category-data and local-capacity limitations. No retrospective origin admission; Phase 4 remains gated.
- New evidence: `PHASE_03_ORIGINAL_READ_EVIDENCE.json` records actual original-code verification of the existing 100,000-row journal without source requests. Its incomplete status and original hashes/clocks remain unchanged. D035 committed-code synthetic 400,000-member capacity used 320,897,024 resident bytes and 27,764,313,417ns; exact build/fixture/result in `PHASE_03_SAMPLING_CAPACITY_EVIDENCE.json`; synthetic capacity is not live source/panel evidence. D036 larger collection caps were tested/committed before attempt 3; its timeout did not reach those caps.
- Unresolved: interval freshness/churn, durable panel actual-read integration, durable panel facts/leases, family coverage, selected external-source admission and actual pilot timing/control/target acceptance. Economic grouping, native event-time and complete trade/depth coverage remain evidence-dependent.
- Next planned phase: 04 — baselines/experiments, only after full Phase 3 acceptance and sufficient clean data.
- Continuation: existing same-task heartbeat `arepo-v2-continuation-at-05-10` was updated and saved configuration verified for 2026-09-22 10:36 Europe/London (+310 minutes from this heartbeat), with the user's exact prompt; target task `01a0bd77-ed42-79d3-8c5b-2c207b0ead04`. No duplicate chain created.
- Preserved frame roots: data-dumps/fs2_capture_c63c72a0fe194f47824ccc862b0619cd; data-dumps/fs2_capture_95cbb8cdd4334bc1836249e7d7864473; data-dumps/fs2_capture_3a4f80db7fa94d248fc16e1397af4c71; data-dumps/fs2_capture_ff7f05b057b647109b4239ca781e10fb. Exact original code commits/hashes in the evidence JSONs. Original-build readers intentionally reject changed code; do not disable that guard or reinterpret old journals under new parsers.
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
