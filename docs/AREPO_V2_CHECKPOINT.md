# AREPO v2 live checkpoint

Updated: 2026-09-27. Status: Phase 3 incomplete — D056 runtime/recovery, D057 exact snapshot computation and D058 raw-window capture/recovery and D059 decoded receipt diagnostics and D060 pre-subscription binding and D061 post-window reconciliation and D062 fixed socket connector and D063 durable socket driver implemented as software milestones and D064 socket analysis accepted as software milestones. Numerical feature windows, measured controls, admitted external information and prospective pilot remain. Phases 0–2 complete.

- Current phase/objective: 03 — bounded prospective panel, with frozen sampling/control design, actual causal origins and measured target coverage.
- Previous continuation: 2026-09-27 05:25 UTC heartbeat resumed the same run. Local capacity restored (~25 GiB). Allowance reset verified: 0% primary /16% weekly used, ordinary usage allowed. D067 repairs early timer wakeups discovered by the completed regression; no empirical panel admission.
- Current continuation: 2026-09-27 10:35 UTC. Initial allowance 1% primary /32% weekly used; ordinary usage allowed. D069 bounded stratum sampler/declaration/selection implemented; 193 affected tests passed in 217.52s. Full original-code recovery and legacy defaults pass. No public collection or empirical acceptance.
- Current successor: same automation/task, 2026-09-27 16:45 Europe/London /15:45 UTC (+310 minutes); exact inner scalable-observation prompt saved and verified, no duplicate. Latest user observation guidance: prefer persistent pre-t0 and bounded concurrent/sharded observers where appropriate; no invented socket continuity or mandated artificial staggering.
- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin https://github.com/dayyansheikh/Arepo.git.
- Current branch: codex/arepo-v2-phase-3-prospective-panel, stacked from accepted Phase 2 `747485c6724fafd33b60aa222843d7d94116746b`.
- Latest safe implementation commit: D068 `3613fd3e9e82f26c4f12f79179678842050e9c50`, authenticated screening/control consumer; 64 affected tests passed in 140.15s. D067 `7a812d881b555e1ce4b23d88482606baa44bf4d5`, UTC scheduling fix; all 55 affected cases pass across recorded targeted runs. D066 `8e5f47755e6d6b20a988b7bee95aeb1a03f0005e` committed/pushed with 52 affected tests in 98.16s; full-regression gate blocked by local capacity. D065 `c9042eca9f9e2dc6f616b097836f259a32331dc5` accepted/pushed, 8 affected tests passed in 82.46s; one fixed public diagnostic completed and recovered, empirical panel gates still open. D064 `915165417e1c362c73136c8e65d54828b3235de7` accepted/pushed. D063 `742b65e90798d9f118ded87a9b924333b162f577` accepted/pushed. D062 `b00f0df4e8326be7d4c328239ddf9fc71d14ff08` accepted/pushed; D061 `73b1ccc` accepted/pushed. D060 `46e1249`, D059 `a75b71e`, D058 `8793fa5`, D057 `247c260`. Live collection and origin/SQL admission remain disabled.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/16, open draft against Phase 2; head/body updated through D068; attachment refreshed. Prerequisite https://github.com/dayyansheikh/Arepo/pull/15 complete, open draft/unmerged, stacked on #14/#13. Ultimate production base remains `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Completed: Phase 0 canonical foundation; Phase 1 isolated immutable store; Phase 2 source journals/admission, exact identities and bounded replay. Phase 3 milestones: pure sampling/control/receipt-target rules; isolated keyset frame journal, source+panel build binding, bounded CLI, raw/parsed/page manifests, cursor/scope/duplicate/conflict/clock/error checks, crash-safe read-only recovery, streaming verification and measured-capacity preflights.
- Files/modules changed: research_panel/{__init__,sampling,targets,frame,frame_cli,build_identity,original_reader,metadata,selection,selection_cli}.py; planning/frame/metadata/selection/original-reader tests; isolated feature_store/{capture,sources}.py; phase/review/frame/panel-journal contracts, decisions D030–D041 and measurement evidence JSONs. Latest D041 changes cover original_reader, selection_cli, original-selection tests, evidence and recovery docs. No v1/config/API/scheduler/frontend changes.
- Tests/results: D068 64 affected cases passed in 140.15s; exact command below. D066 unchanged full regression completed with 1,438 passed/4 failed in 1,468.63s, fingerprint unchanged. Three early-intent failures exposed the single-sleep UTC bug; one stale pre-binding followed a host pause. D067 all 55 selected cases now pass across targeted runs (details/evidence below), plus Ruff/canonical/whitespace checks. This is not a new all-green backend-wide run. Earlier accepted results remain historical.
- Measured first page: `bf734a0`, 100 rows, 557,140 raw bytes, 1,501,764 retained bytes, 157,199,875ns request-to-receipt; continuing cursor, incomplete. PHASE_03_FIRST_PAGE_EVIDENCE.json.
- Enumeration attempt 1: `f66dea1`, 410 attempts / 409 complete pages / 40,900 rows; stopped at 256MiB raw cap with partial 410th response preserved. Raw268,435,456 / retained 654,055,783 / peak resident 202,407,936 bytes. Incomplete. PHASE_03_ENUMERATION_ATTEMPT_1.json.
- Enumeration attempt 2: `726cec2`, 1,000 complete pages /100,000 distinct market IDs, still continuing. 99,956 eligible row identities and 44 unresolved, no observed duplicates/conflicts within prefix. Raw644,897,535 / retained 1,577,956,669 / peak resident 343,457,792 bytes. Request-cap stop; incomplete. PHASE_03_ENUMERATION_ATTEMPT_2.json. Final verification overlapped backend regression, so whole-command elapsed is not an isolated performance benchmark.
- Enumeration attempt 3: `5cdb2d2`, 74 attempts /73 complete pages /7,300 rows plus partial response 74. Incomplete, `page_error`/`TimeoutError` after 15s. Raw46,929,025 /retained112,224,334 /peak resident118,849,536 bytes. Original-code prior-capacity verification succeeded. Root `data-dumps/fs2_capture_ff7f05b057b647109b4239ca781e10fb`; full evidence in PHASE_03_ENUMERATION_ATTEMPT_3.json. 7,256 eligible rows, 44 unresolved; no terminal or population inference.
- Enumeration attempt 4: `b93f9aa`, 204 verified attempts /200 complete pages /20,000 rows, with 3 bounded retries (2 recovered). Incomplete, `retry_exhausted`; unrecovered `ConnectError` and `TimeoutError`. Raw132,580,143 /retained318,668,335 /peak resident141,836,288 bytes. 19,956 eligible rows, 44 unresolved, no duplicates/conflicts or terminal. Root `data-dumps/fs2_capture_8e6a8d4a22b846ae91ca70f70f6b3939`; evidence in PHASE_03_ENUMERATION_ATTEMPT_4.json.
- Self-review: source/clock/identity/raw preservation, internally frozen seed, actual read/projection/cutoff ordering, exact rational replay, unknown and unmapped inventory, duplicate handling, failed-run refusal, original-frame policy/page closure, bounded storage/time and changed-build refusal. Source exhaustion is established only for attempt 5. No population inference, pilot acceptance or predictive improvement is claimed.
- Decisions: D000–D069. D068 authenticates screening decisions and preserves conditional probabilities without enabling a collector. D067 rechecks UTC boundaries after early timer wakeups. D066 predeclared snapshot assessment/recovery passed 52 affected tests in 98.16s; no public assessment or control admission. D065 freezes one fixed-target diagnostic with committed-code/full-reservation checks and independent/original recovery; 8 affected tests passed in 82.46s. D064 consumes verified socket journals into durable exact coverage/post-request endpoint diagnostics with full original-code recovery; no public collection or admission. D063 supplies versioned durable socket capture/recovery with verified prebinding and explicit operation failures. D062 supplies a tested fixed-endpoint connector, not a durable collector. D061 verifies post-source primary request chronology and exact endpoint diagnostics without repairing gaps or admitting live sources. D060 binds verified pre-window identity before synthetic subscription with honest delayed-expiry state and original recovery. D059 preserves exact decoded receipt coverage and durable computation/recovery without native continuity or feature admission. D058 adds finite raw synthetic capture/recovery without a live connector or decoded feature admission. D057 preserves bounded exact F08/F09 snapshot components and actual computation/recovery without continuous-window or origin admission. D056 composes and replays the evolving origin/target queue and reads sealed runs through their exact original code. D055 preserves fixed due attempts, original deadlines, incomplete-evidence blockers and actual target-receipt availability; midpoint change is a diagnostic only. D054 binds frozen origin identity separately from fresh consistency and actual durable computation availability; explicit failures/closure remain distinct. D053 owns exclusive synthetic origin intents, preserves real read/freeze/save clocks and exact source/computation evidence, derives late/abstaining states without rewriting facts and refuses live transports. D052 seals actual selection consumption and immutable schedules from its save acknowledgement; source collection and origins remain disabled. D050 binds a new fresh selection to the declared seed and full capacity reservation, with exact assessment-aware all-unassessed inventory and cutoff/save freshness. Collection/origins remain disabled. D049 enforces opt-in source quotas before managed writes, preserves raw on later parsing refusal and makes failed guarded attempts terminal. D048 freezes actual declaration time/seed and full role/outcome reservation before reads; D049 supplies source quota enforcement; collection remains disabled until applied by the full panel writer. D047 preserves quote computations through their exact original committed decoder and a new read receipt. D046 adds an explicit opt-in targeted Gamma path and conservative lifecycle abstentions; no broad-frame filtering or old-policy expansion. D042 distinguishes measured negatives from unknown/stale assessments. D043 records actual source reads. D044 projects exact quotes with identities known before receipt. D045 freezes policy before those reads, records actual computation/durability, accounts for child storage and independently replays at the original cutoff. No live trigger/control evidence, feature-store records or origins admitted; original history stays intact.
- Required data gate: complete-frame blocker **cleared** by verified attempt 5. Earlier failures remain incomplete. No current protected approval/access blocker. Current allowance is recorded above; the preceding window's 93% primary /92% weekly snapshot is historical and no longer controls this continuation.
- Completed attempt 5: `data-dumps/fs2_capture_eaec9cd7e8684953952e1b683c33dd3a`, implementation `41fcb0170c7d71716873847639dc181ea12422aa`. 1,755 pages, 175,427 distinct markets, 175,383 mapped eligible rows, 44 unresolved; no retries, errors, duplicates or conflicting identities. State `exhausted_consistent`, terminal observed. Raw 1,115,618,904 /retained 2,728,778,097 /peak resident 478,052,352 bytes; whole-command 514,493,751,417ns. Actual interval 23:30:55–23:36:47 UTC on September 21; sealed at 23:37:32 UTC. Source/clock/manifest verification passed; CLI exited 0. See PHASE_03_ENUMERATION_ATTEMPT_5.json. Original capacity-read root `data-dumps/fs2_frame_read_b9ef454ed5e64e8f82fa623e464135b2`; CLI `data-dumps/fs2_attempt5_cli_20260921T233100Z.json`. No collector remains active.
- Completed local selection: `data-dumps/fs2_selection_56ff541cb2c74477b5ae56de1a78ad54`, implementation `018dbd3916448f922ef79425aead3d2b5aac735d`; CLI `data-dumps/fs2_selection_attempt1_cli.json`, exit 0 and independent replay passed. Retains 175,427 rows, 175,383 sampling members, 44 unresolved identities; 107 scheduled draws in 107 strata, exact weights. Category missing for all mapped rows; close missing 1,168, liquidity 25,879, metadata probability 65. No metadata-based exclusions or invented category mappings. Retained 566,741,238 /peak resident 294,977,536 bytes; elapsed 146,486,870,416ns. Reconstructed development only, no source requests/origins/controls. No active measurement remains. PHASE_03_SELECTION_ATTEMPT_1.json preserves clocks/hashes.
- Completed original-selection read: committed D041 `d24ed88` verified the saved D040 selection under its original `018dbd3`, exit 0. Root `data-dumps/fs2_selection_read_40ff23f9869d43c3bce9cab1b6585900`; CLI `data-dumps/fs2_original_selection_read_attempt1_cli.json`. Full original report/plan equality passed; 107 selected markets, old seed/weights/clocks and reconstructed status unchanged. New receipt available at 2026-09-22T04:56:02.327631Z; evidence PHASE_03_ORIGINAL_SELECTION_READ_EVIDENCE.json. No process remains active.
- Exact next action: D069 bounded stratum draw is implemented and validated (193 affected tests, 217.52s). Connect the bounded source worker with whole source/book/assessment/recovery/origin/control/target reservation, then verified-role activation/runtime. Historical all-strata two-per-cell screening would exceed available complete reservation; do not coarsen/truncate matching strata or silently omit recovery/targets. D068 screening declaration/verified consumer is accepted with 64 affected tests in 140.15s. Reserve all source/book/assessment/recovery/origin/control/target costs before public requests; verify actual role counts fit the frozen reservation. Do not repeat accepted diagnostics or tests without relevant changes. Live runtime, selected external admission and empirical pilot remain gated. Phase 4 remains for a fresh chat.
- Latest modules/files: D068 screening.py, original_reader.py, 15 screening tests, and screening integration contract; D067 scheduling.py, origin/due/runtime waits and six timer tests. D066 trigger_computation.py, original-reader support, 16 new assessment/recovery cases and trigger contract. D065 socket_diagnostic.py, fixed orchestration tests and frozen protocol. D064 socket_analysis.py, original_reader.py, shared pure endpoint algebra in window_reconciliation.py, two new socket-analysis test modules and phase/master/review/decisions/checkpoint/analysis contract. D063 socket_window.py/socket_window_journal.py and driver/recovery tests accepted at 742b65e. D061 window_reconciliation.py, original_reader.py and reconciliation/original recovery tests accepted at 73b1ccc. No v1/API/config/workflow/frontend/SQL/production changes.
- Current capacity observation (2026-09-27): 26,634,020 KiB free during regression; previous 4 GiB blocker cleared. Remeasure before collection. Preserve all raw/failed runs.
- Next-run constraints: category is absent in all mapped source rows; enrichment requires separate versioned source evidence, never a fallback invented from other fields. Local disk snapshot after D041: 9,133,616 KiB free, below the existing expanded-frame 8 GiB retained +2 GiB reserve preflight. Do not launch that mode unchanged, delete evidence or narrow the population. A separately designed/tested finite budget refinement may use the actual 2,728,778,097-byte complete-frame cost; remeasure disk first. No new collection budget has been frozen or authorized by this note.
- New evidence: `PHASE_03_ORIGINAL_READ_EVIDENCE.json` records actual original-code verification of the existing 100,000-row journal without source requests. Its incomplete status and original hashes/clocks remain unchanged. D035 committed-code synthetic 400,000-member capacity used 320,897,024 resident bytes and 27,764,313,417ns; exact build/fixture/result in `PHASE_03_SAMPLING_CAPACITY_EVIDENCE.json`; synthetic capacity is not live source/panel evidence. D036 larger collection caps were tested/committed before attempt 3; its timeout did not reach those caps.
- Unresolved: measured family/window coverage, durable trigger assessments and matched controls, selected external-source admission and actual pilot timing/control/target acceptance. Economic grouping, native event-time and complete trade/depth coverage remain evidence-dependent. Synthetic actual-read/origin/target scheduling is implemented but not a live accepted panel.
- Targeted runtime evidence: D046 `761d279`, root `data-dumps/fs2_target_probe_1646679dd37f444ba9185748c4bdc0c3`. Both fixed requests returned 200; identity available before book receipt; one observed receipt-time quote, independent replay and immutable source/computation checks passed. Raw 6,178 bytes, retained before report 81,737, peak resident 75,972,608, elapsed 1,046,331,792 ns. Computation available 2026-09-22T13:13:11.141974Z. Exact plan/script/build/clocks/acknowledgements in PHASE_03_TARGETED_QUOTE_EVIDENCE.json. No origin, feature-store admission or accepted panel; historical draw unchanged.
- Original quote read evidence: D047 `fc8389a` verified the saved D046 computation under original `761d279`, preserving exact full facts and summary, old clocks/cutoff/provenance and source/computation bytes. Root `data-dumps/fs2_quote_computation_read_c08fa81c7aab4fbc8197547591b57876`; actual new read available 2026-09-22T13:23:45.247836Z. PHASE_03_ORIGINAL_QUOTE_READ_EVIDENCE.json. No new source requests or origin admission.
- Scope override (user 2026-09-24): continue Phase 3 only in this task. Do not start Phase 4. On genuine Phase 3 acceptance finalise durable handover, cancel any pending successor, emit PHASE 3 COMPLETE — READY FOR FRESH CODEX HANDOVER and stop. Phase 4 begins in a fresh Codex conversation, with its data prerequisites still binding.
- Continuation: existing arepo-v2-continuation-at-05-10 updated for 2026-09-27 11:35 Europe/London (10:35 UTC; +310 minutes from the 05:25 UTC heartbeat), same task 01a0bd77-ed42-79d3-8c5b-2c207b0ead04, exact efficiency-focused Phase 3 prompt. No duplicate chain.
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

D060 final acceptance (2026-09-24): **17 new tests passed in 87.37s**, plus **52 existing affected tests passed in 96.36s** (69 total across the two disjoint runs). No code changed between these runs. Ruff/canonical/whitespace pass. No test or collector remains running. D060 is accepted only as the pre-subscription synthetic binding/recovery milestone; Phase 3 is incomplete. Resume post-window chronology/reconciliation as specified above.

D061 final acceptance (2026-09-25): **63 affected tests passed in 300.57s**, covering both new reconciliation suites plus existing original-bound/window-computation/window/book recovery and receipt-coverage tests. Ruff/canonical/whitespace checks passed. Exact test selection is in the review. No public source requests or production changes. Full D056 1,202-test result remains historical; this is scoped software acceptance, not Phase 3 completion.

D062 final acceptance (2026-09-25): **23 affected tests passed in 64.86s**. Connector suite (17 cases), original-window-reconciliation (2) and original-bound-window (4). Actual loopback wire/redirect/oversize/timeout/close tests plus synthetic recovery; no public connection. Ruff/canonical/whitespace pass. No test or collector remains running. Transport primitive only; durable driver and all empirical Phase 3 gates remain.

D063 final acceptance (2026-09-25): **47 affected tests passed in 183.97s**: socket-window, original-socket-window, connector, original-bound-window and original-window-reconciliation suites. Ruff/canonical/whitespace pass. Actual local loopback only; no public requests, production/SQL changes or Phase 3 empirical acceptance. Driver/recovery milestone accepted; coverage/post-window integration remains next.

D064 final acceptance (2026-09-25): **70 affected tests passed in 471.27s**, explicit isolated
SQLite/email-disabled pytest on unit/test_research_panel_{socket_analysis,original_socket_analysis,
window_reconciliation,original_window_reconciliation,original_socket_window,window_coverage}.py.
No code changed during that run. Ruff/canonical/whitespace pass. Full D056 suite remains historical.
No public request, SQL/production change or empirical Phase 3 acceptance. All tests completed.

D065 measured diagnostic: `data-dumps/fs2_socket_diagnostic_20260925_1`, committed c9042ec,
CLI exit 0. Four HTTP requests and one 60-second socket completed. Initial book +5 PONGs;
1s covered /59s uncovered under the frozen 1s hold; unavailable terminal comparison preserved.
Independent/original-code recovery passed for pre/socket/analysis/post. Retained372,356 bytes,
HTTP raw12,378/socket raw1,470, elapsed88,618,854,542ns, parent peak80,150,528 bytes. Exact
clocks/hashes and limitations: docs/implementation/PHASE_03_SOCKET_DIAGNOSTIC_EVIDENCE.json.
No accepted panel, new source/feature admission or native continuity inference. Never rerun it.

D066 backend-wide validation stopped (2026-09-25): 728 passed, 19 failed, one existing
Starlette/httpx warning; interrupted after repeated local-capacity refusals. Every recorded
failure is in test_research_panel_activation.py at the unchanged full panel/control/target
reservation gate. The run ended 11:52:57 UTC, wrapper exit 2; pytest 196.14s, wrapper197.52s.
Code/tests fingerprint unchanged: 535f547291f7ae29ece085c80b67481de7df1b3d50179a732e70e6d78919f8ce.
Primary log/result remain /tmp/arepo_d066_full_validation.log and .json; durable summary is
docs/implementation/PHASE_03_FULL_REGRESSION_CAPACITY_EVIDENCE.json. No test remains active.
This does not establish an algorithmic regression or a full pass; remaining tests are unrun.

Capacity alternatives inspected: /tmp shares the same filesystem; /Volumes exposes only the
existing Macintosh volume; all retained pytest temporary roots total roughly 232 MiB, insufficient
to satisfy the larger 5,969 MiB existing reservation even if reclaimed. No temporary or research
evidence was deleted, no volume/repository moved, no guard/test changed. Requested user-provided
non-research free space or an existing suitable local test volume. BLOCKED — LOCAL TEST CAPACITY
UNAVAILABLE. This is a resource blocker, not a request to waive research or production boundaries.
The same-task successor was updated once for 22:47 London; saved exact prompt/target/schedule
verified. On unchanged state, remain quiet and avoid redundant tests or meaningless repo edits.

## D067 current recovery — 2026-09-27

D067 safe implementation commit: `7a812d881b555e1ce4b23d88482606baa44bf4d5` (scheduling.py and six deterministic tests). It rechecks actual UTC after timer completion at
origin/target intent creation, runtime dispatch and terminal outcome cutoff. No early-start
or freshness tolerance was relaxed. Waits have an explicit one-day scope and a monotonic
budget for backward-clock divergence. Originals are recovered with their pinned code.

Validation: /tmp/arepo_d067_targeted.log ran scheduling, origin_worker, due_worker, runtime,
original_runtime and original_bound_window suites: 53 passed, 2 failed, 1 teardown error.
One failure/error was a new test replacing the shared time.monotonic function and disturbing
asyncio; fixed by replacing only the scheduling module's time reference. All six clock cases
then passed in 0.12s. The other failure was an expired origin after a ~16-minute host pause.
A targeted scheduling+due retry: 22 passed/1 failed in 229.48s; the remaining source request
expired across a ~206s UTC /1s monotonic gap. The exact remaining rate-limit case passed in
18.64s under process-scoped caffeinate -is (/tmp/arepo_d067_last.log). Thus all 55 selected
cases have passed; no journal was repaired, cutoff shifted, or test expectation weakened.
No active test remains. D066 full evidence is PHASE_03_REGRESSION_RECOVERY_EVIDENCE.json;
the earlier capacity failure evidence remains intact. Diff self-reviewed.

D068 supersedes the temporary screening drafts. The repository implementation now authenticates
D066 source decisions against the selected identity/rule/provenance and delegates matched-role
planning to the existing sampler. It preserves first-stage probabilities and conditional
second-stage weights, unknown/unavailable states, unfilled slots and immutable original-code
recovery. It makes no source request and admits no origin or SQL row. Partial/torn evidence is
retained; corrupt completed evidence refuses admission. Entire source-worker/runtime capacity
still requires a separate preflight. All 64 affected tests pass in 140.15s: screening (15),
assessments (33), trigger computation (16). Log: /tmp/arepo_d068_final.log. Initial 13-case
validation found the repository's tagged UTC encoding needed explicit decoding; corrected and
13 cases passed in 96.26s before adding source-failure and partial-screen coverage. No weakened
clock/type/identity guard. Ruff/canonical/whitespace checks and self-review pass. No active test.


Next-run sizing refinement: historical selection contains 107 strata (98 multi-member/nine
singletons), implying 205 two-per-stratum screens. Existing per-decision/book/recovery ceilings
already exceed current ~25 GiB capacity before sources and target journals. A bounded uniform
stratum draw preserves matching and nonzero inclusion; its exact probability/acceptance contract
is at the end of PHASE_03_SCREENING_CONTROL_NEXT.md. This design is not implemented or validated.
No public screening or new data was collected. The source worker remains the subsequent step.


Window shutdown: allowance last checked at 89% primary /30% weekly used, ordinary usage still
allowed. Coherent accepted work is committed/pushed and draft PR #16 updated; stop before
exhaustion rather than start an unfinishable schema/sampler change. This is not an access,
weekly-exhaustion or user-approval blocker. Exactly one successor remains at 11:35 London.
Before the future pilot, the next activation must address the documented same-boundary origin
queue starvation risk through predeclared spacing/timing validation; keep old schedules intact.

D069 self-review/validation: four existing modules (sampling, panel_declaration, panel_selection, screening) plus test_research_panel_bounded_sampling.py; 193 tests passed in 217.52s, Ruff/canonical/whitespace checks passed. Exact suites and remaining gates in PHASE_03_REVIEW.md. Full collector reservation remains unimplemented; no pilot cap was frozen.
