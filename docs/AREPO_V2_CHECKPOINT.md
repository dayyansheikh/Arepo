# AREPO v2 live checkpoint

Updated: 2026-10-08. Capacity restored before safe prompt cleanup; D096 explicit temporal deep-sample policy passes102 scoped cases. Phase3 incomplete; D094 remains failed.

- Current phase/objective: 03 — bounded prospective panel, with frozen sampling/control design, actual causal origins and measured target coverage.
- Previous continuation: 2026-09-27 05:25 UTC heartbeat resumed the same run. Local capacity restored (~25 GiB). Allowance reset verified: 0% primary /16% weekly used, ordinary usage allowed. D067 repairs early timer wakeups discovered by the completed regression; no empirical panel admission.
- Previous implementation continuation: 2026-09-27 10:35 UTC. Initial allowance 1% primary /32% weekly used; ordinary usage allowed. D069 bounded stratum sampler/declaration/selection implemented; 193 affected tests passed in 217.52s. Full original-code recovery and legacy defaults pass. No public collection or empirical acceptance.
- Current successor: one same-task continuation October8 19:18 Europe/London /18:18UTC, exact new general prompt in docs/implementation/PHASE_03_HEARTBEAT.md.
- Current continuation: October8 13:08UTC; initial allowance5% primary/48% weekly used, ordinary usage allowed. No reset credit redeemed.
- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin https://github.com/dayyansheikh/Arepo.git.
- Current branch: codex/arepo-v2-phase-3-prospective-panel, stacked from accepted Phase 2 `747485c6724fafd33b60aa222843d7d94116746b`.
- Latest safe evidence commit: 0979058 (D094 terminal evidence and capacity boundary), pushed. D094 executed under53c19a43d9784e7f98a41e22131799f5a63b7e1f; original audit passed.
- Latest safe implementation/evidence commit: 006b006 (D092 bounded observation integration and D091 retrospective evidence), pushed. The following documentation-only checkpoint commit records this boundary.
- Draft PR: https://github.com/dayyansheikh/Arepo/pull/16, open draft against Phase2. Head/body updated with each coherent commit; never merged.
- Completed: Phase 0 canonical foundation; Phase 1 isolated immutable store; Phase 2 source journals/admission, exact identities and bounded replay. Phase 3 milestones: pure sampling/control/receipt-target rules; isolated keyset frame journal, source+panel build binding, bounded CLI, raw/parsed/page manifests, cursor/scope/duplicate/conflict/clock/error checks, crash-safe read-only recovery, streaming verification and measured-capacity preflights.
- Files/modules changed: research_panel/{__init__,sampling,targets,frame,frame_cli,build_identity,original_reader,metadata,selection,selection_cli}.py; planning/frame/metadata/selection/original-reader tests; isolated feature_store/{capture,sources}.py; phase/review/frame/panel-journal contracts, decisions D030–D041 and measurement evidence JSONs. Latest D041 changes cover original_reader, selection_cli, original-selection tests, evidence and recovery docs. No v1/config/API/scheduler/frontend changes.
- Tests/results: D09224 affected cases passed172.73s; D09159 cases39.56s; D09034 cases49.65s plus51 after endpoint fix71.53s. Ruff/backend/canonical/whitespace pass. Synthetic validation only; D090 empirical diagnostic separately retained, no Phase3 acceptance.
- Measured first page: `bf734a0`, 100 rows, 557,140 raw bytes, 1,501,764 retained bytes, 157,199,875ns request-to-receipt; continuing cursor, incomplete. PHASE_03_FIRST_PAGE_EVIDENCE.json.
- Enumeration attempt 1: `f66dea1`, 410 attempts / 409 complete pages / 40,900 rows; stopped at 256MiB raw cap with partial 410th response preserved. Raw268,435,456 / retained 654,055,783 / peak resident 202,407,936 bytes. Incomplete. PHASE_03_ENUMERATION_ATTEMPT_1.json.
- Enumeration attempt 2: `726cec2`, 1,000 complete pages /100,000 distinct market IDs, still continuing. 99,956 eligible row identities and 44 unresolved, no observed duplicates/conflicts within prefix. Raw644,897,535 / retained 1,577,956,669 / peak resident 343,457,792 bytes. Request-cap stop; incomplete. PHASE_03_ENUMERATION_ATTEMPT_2.json. Final verification overlapped backend regression, so whole-command elapsed is not an isolated performance benchmark.
- Enumeration attempt 3: `5cdb2d2`, 74 attempts /73 complete pages /7,300 rows plus partial response 74. Incomplete, `page_error`/`TimeoutError` after 15s. Raw46,929,025 /retained112,224,334 /peak resident118,849,536 bytes. Original-code prior-capacity verification succeeded. Root `data-dumps/fs2_capture_ff7f05b057b647109b4239ca781e10fb`; full evidence in PHASE_03_ENUMERATION_ATTEMPT_3.json. 7,256 eligible rows, 44 unresolved; no terminal or population inference.
- Enumeration attempt 4: `b93f9aa`, 204 verified attempts /200 complete pages /20,000 rows, with 3 bounded retries (2 recovered). Incomplete, `retry_exhausted`; unrecovered `ConnectError` and `TimeoutError`. Raw132,580,143 /retained318,668,335 /peak resident141,836,288 bytes. 19,956 eligible rows, 44 unresolved, no duplicates/conflicts or terminal. Root `data-dumps/fs2_capture_8e6a8d4a22b846ae91ca70f70f6b3939`; evidence in PHASE_03_ENUMERATION_ATTEMPT_4.json.
- Self-review: source/clock/identity/raw preservation, internally frozen seed, actual read/projection/cutoff ordering, exact rational replay, unknown and unmapped inventory, duplicate handling, failed-run refusal, original-frame policy/page closure, bounded storage/time and changed-build refusal. Source exhaustion is established only for attempt 5. No population inference, pilot acceptance or predictive improvement is claimed.
- Decisions: D000–D073. D068 authenticates screening decisions and preserves conditional probabilities without enabling a collector. D067 rechecks UTC boundaries after early timer wakeups. D066 predeclared snapshot assessment/recovery passed 52 affected tests in 98.16s; no public assessment or control admission. D065 freezes one fixed-target diagnostic with committed-code/full-reservation checks and independent/original recovery; 8 affected tests passed in 82.46s. D064 consumes verified socket journals into durable exact coverage/post-request endpoint diagnostics with full original-code recovery; no public collection or admission. D063 supplies versioned durable socket capture/recovery with verified prebinding and explicit operation failures. D062 supplies a tested fixed-endpoint connector, not a durable collector. D061 verifies post-source primary request chronology and exact endpoint diagnostics without repairing gaps or admitting live sources. D060 binds verified pre-window identity before synthetic subscription with honest delayed-expiry state and original recovery. D059 preserves exact decoded receipt coverage and durable computation/recovery without native continuity or feature admission. D058 adds finite raw synthetic capture/recovery without a live connector or decoded feature admission. D057 preserves bounded exact F08/F09 snapshot components and actual computation/recovery without continuous-window or origin admission. D056 composes and replays the evolving origin/target queue and reads sealed runs through their exact original code. D055 preserves fixed due attempts, original deadlines, incomplete-evidence blockers and actual target-receipt availability; midpoint change is a diagnostic only. D054 binds frozen origin identity separately from fresh consistency and actual durable computation availability; explicit failures/closure remain distinct. D053 owns exclusive synthetic origin intents, preserves real read/freeze/save clocks and exact source/computation evidence, derives late/abstaining states without rewriting facts and refuses live transports. D052 seals actual selection consumption and immutable schedules from its save acknowledgement; source collection and origins remain disabled. D050 binds a new fresh selection to the declared seed and full capacity reservation, with exact assessment-aware all-unassessed inventory and cutoff/save freshness. Collection/origins remain disabled. D049 enforces opt-in source quotas before managed writes, preserves raw on later parsing refusal and makes failed guarded attempts terminal. D048 freezes actual declaration time/seed and full role/outcome reservation before reads; D049 supplies source quota enforcement; collection remains disabled until applied by the full panel writer. D047 preserves quote computations through their exact original committed decoder and a new read receipt. D046 adds an explicit opt-in targeted Gamma path and conservative lifecycle abstentions; no broad-frame filtering or old-policy expansion. D042 distinguishes measured negatives from unknown/stale assessments. D043 records actual source reads. D044 projects exact quotes with identities known before receipt. D045 freezes policy before those reads, records actual computation/durability, accounts for child storage and independently replays at the original cutoff. No live trigger/control evidence, feature-store records or origins admitted; original history stays intact.
- Required data gate: complete-frame blocker **cleared** by verified attempt 5. Earlier failures remain incomplete. No current protected approval/access blocker. Current allowance is recorded above; the preceding window's 93% primary /92% weekly snapshot is historical and no longer controls this continuation.
- Completed attempt 5: `data-dumps/fs2_capture_eaec9cd7e8684953952e1b683c33dd3a`, implementation `41fcb0170c7d71716873847639dc181ea12422aa`. 1,755 pages, 175,427 distinct markets, 175,383 mapped eligible rows, 44 unresolved; no retries, errors, duplicates or conflicting identities. State `exhausted_consistent`, terminal observed. Raw 1,115,618,904 /retained 2,728,778,097 /peak resident 478,052,352 bytes; whole-command 514,493,751,417ns. Actual interval 23:30:55–23:36:47 UTC on September 21; sealed at 23:37:32 UTC. Source/clock/manifest verification passed; CLI exited 0. See PHASE_03_ENUMERATION_ATTEMPT_5.json. Original capacity-read root `data-dumps/fs2_frame_read_b9ef454ed5e64e8f82fa623e464135b2`; CLI `data-dumps/fs2_attempt5_cli_20260921T233100Z.json`. No collector remains active.
- Completed local selection: `data-dumps/fs2_selection_56ff541cb2c74477b5ae56de1a78ad54`, implementation `018dbd3916448f922ef79425aead3d2b5aac735d`; CLI `data-dumps/fs2_selection_attempt1_cli.json`, exit 0 and independent replay passed. Retains 175,427 rows, 175,383 sampling members, 44 unresolved identities; 107 scheduled draws in 107 strata, exact weights. Category missing for all mapped rows; close missing 1,168, liquidity 25,879, metadata probability 65. No metadata-based exclusions or invented category mappings. Retained 566,741,238 /peak resident 294,977,536 bytes; elapsed 146,486,870,416ns. Reconstructed development only, no source requests/origins/controls. No active measurement remains. PHASE_03_SELECTION_ATTEMPT_1.json preserves clocks/hashes.
- Completed original-selection read: committed D041 `d24ed88` verified the saved D040 selection under its original `018dbd3`, exit 0. Root `data-dumps/fs2_selection_read_40ff23f9869d43c3bce9cab1b6585900`; CLI `data-dumps/fs2_original_selection_read_attempt1_cli.json`. Full original report/plan equality passed; 107 selected markets, old seed/weights/clocks and reconstructed status unchanged. New receipt available at 2026-09-22T04:56:02.327631Z; evidence PHASE_03_ORIGINAL_SELECTION_READ_EVIDENCE.json. No process remains active.
- Exact next action: commit reviewed D096 software/contract, then freeze one finite prospective measurement using the explicit temporal population with unchanged acceptance gates. Do not rerun D094 or rewrite its population. See PHASE_03_TEMPORAL_POPULATION.md. No Phase4.
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

D070 current boundary: screening_worker.py and 14 worker tests; existing 15 screening tests pass as well. No existing source module changed. Self-review, exact commands/results and limitations recorded in Phase 3 review and screening contract. Protected production boundaries unchanged.

D071 modules: activation.py, original_reader.py, shared role_capacity in panel_declaration.py, screening_worker import, 19 new screened-activation cases. 57 affected tests passed in 402.86s; self-review and Ruff/canonical/whitespace passed. No collector remains.

## D072 recovery — started 2026-09-27 15:45 UTC, verified 20:55 UTC

Bounded concurrent synthetic screened runtime implemented in concurrent_runtime.py, explicit
wrapper/layout routing in runtime.py and original-reader v2 dependency support. New tests in
test_research_panel_concurrent_runtime.py. Legacy APIs retained. Final targeted concurrent_runtime/runtime/original_runtime suites: 21 passed in 246.37s; /tmp/arepo_d072_final.log. No test remains running. Ruff/backend, canonical contract and whitespace checks pass. Self-review covered bounded isolated loops, ready-target priority/reserved capacity, dispatch/child/completion chronology, cancellation drainage and original-code dependency protection. Development test found a correctly retained late origin in an overly tight
three-market fixture; fixture now budgets 20s rather than 8s and deterministically delays the
second immutable dispatch. Production/pilot deadlines were not changed.

D072 synthetic runtime/replay milestone complete; no empirical panel admission. Files:
concurrent_runtime.py, runtime.py, original_reader.py and test_research_panel_concurrent_runtime.py.
No public acquisition, SQL or production changes. Exactly one successor is scheduled for
2026-09-28 03:05 London, same task and exact prompt. Continue the top-level exact next action.

D073 in progress: official rights review found Coinbase market-data terms restrict AI/automated-system use without consent; default policies still refuse it. Chose research-register XNOAA/NWS as the permitted alternative. Added opt-in fixed-host station observation policy/parser, exact typed native quantities/QC/missingness and original input-read recovery, plus a one-request measurement runner. Contract/frozen public protocol: PHASE_03_EXTERNAL_OBSERVATION.md. Development 67 tests passed in 38.45s. Final affected suite: 105 passed in 165.53s (/tmp/arepo_d073_final.log). A final explicit GeoJSON header correction then passed all 57 affected NWS/capture/source-run cases in 23.38s (/tmp/arepo_d073_headers.log). No test remains active. Ruff/canonical/whitespace and self-review pass. No public acquisition yet.

D073 public source measurement completed once under `77d6652` at data-dumps/fs2_nws_measurement_20260927_1. HTTP 200, observed prospective source facts, actual compact input-read and full original-Git recovery passed. Exact clocks/hashes/raw and retained cost, native observation clock, quantity missingness and limitations: PHASE_03_NWS_SOURCE_EVIDENCE.json. No collector remains active. This is an external-source interface measurement only; no market relevance, representative pilot or Phase 3 completion. Never rerun unchanged.

Usage shutdown: latest supported allowance 92% primary /77% weekly used, ordinary usage allowed. Save this coherent boundary rather than begin another integration that cannot finish in this window. One successor remains 2026-09-28 03:05 London, same task/prompt. No access or protected-approval blocker; next action above remains authorised.

## Active D074 recovery — 2026-09-28

Implemented opt-in feature-origin v2 / concurrent-runtime v3 with an exact bounded snapshot manifest, actual computation/freeze clocks, source lineage, explicit unavailable family reasons and original-code routing. Contract: PHASE_03_ORIGIN_FEATURE_MANIFEST.md. New tests in test_research_panel_origin_features.py. Final affected command currently running on origin_features/origin_worker/concurrent_runtime/original_runtime suites, /tmp/arepo_d074_final.log. Do not edit source package files until it ends. Development first test completed acquisition, due outcome and original recovery but then failed a test-helper invocation (dict passed to callback API); corrected without product guard changes. Immediate recovery: inspect final log, resolve failures, finish self-review/docs/commit/PR. No public data acquired in this run.

D074 acceptance: 44 affected tests passed in 615.56s; /tmp/arepo_d074_final.log. Ruff, canonical contract and whitespace checks pass. Safe implementation is the D074 commit containing this checkpoint (resolve by Git history). Changed origin_features/origin_worker/concurrent_runtime/runtime/original_reader and focused tests. No public measurement or collector remains active. Next D075 protocol is frozen documentation only until the public entry point and refusal tests are committed.

D074 safe commit `0fe87e8` pushed; D075 implementation/review is the commit containing this entry. Ruff/canonical/whitespace pass; /tmp/arepo_d075.log records 16 passed in 156.35s. No source package changed during validation. At 89% primary /92% weekly used, ordinary usage remained allowed. Public measurement still not run at this commit.

## Current recovery — 2026-09-28 07:15 UTC continuation

D074 safe commit **0fe87e8**: 44 affected tests passed in 615.56s. D075 safe commit
**e27149761b1fdc73ff10915fa7a331de30d03da7**: 16 worker tests passed in 156.35s.
Both pushed to open draft PR #16 on the same Phase 2 base. Ruff/canonical/whitespace pass.
No production state, SQL or automatic scans changed; unrelated untracked files untouched.

D075 measured once under e271497: eight Gamma 200, six book 200, two book 404; 41,576 raw bytes. All eight screens remain unavailable because targeted responses omit frame event IDs; all other identity fields match. Three positive/three negative snapshot calculations are not admitted roles. Original-Git recovery passed; no origins or accepted panel. Evidence: PHASE_03_SCREENING_MEASUREMENT_EVIDENCE.json. Next: PHASE_03_IDENTITY_COMPARISON_NEXT.md; do not rerun or reinterpret this attempt.

Root: data-dumps/fs2_panel_screening_measurement_20260928_1 with deterministic selection/worker
siblings; CLI data-dumps/fs2_screening_measurement_20260928_1_cli.log. Completed at
02:38:39 UTC, elapsed 660,032,069,917 ns including new selection and recovery.
Actual requests 02:34:24–02:34:45 UTC. Retained panel8,790 /selection566,742,776 /worker1,113,094
bytes; original complete frame unchanged. All 16 assigned requests made; no retries/redraw.
No collector or test remains running. Preserve exact identities, failed books and sampling seed.

07:15 heartbeat received during the same task; work resumed from the finished measurement,
not repeated. One existing successor updated to **13:25 Europe/London /12:25 UTC Sep28**,
+310 minutes, same exact prompt/task, no duplicate. Latest usage check: 11% primary /96% weekly
used, ordinary usage still allowed. Preserve this coherent checkpoint before further substantial
implementation consumes the remaining weekly reserve; do not falsely label allowance exhausted.
No protected approval is needed. Phase 3 remains incomplete; no Phase 4 implementation.

## Current recovery — 2026-09-28 12:25 UTC

Recovered checkpoint/master/AGENTS/phase/review/PR #16: clean tracked tree at12ce5c9,
open draft on unchanged Phase2 base. Allowance available at start:0% primary/97% weekly
used. Kept work bounded to the pure D076a comparison primitive; did not begin expensive
integration or new collection with only3% weekly reserve.

D076a comparison primitive implemented: 28 focused tests passed in 0.36s. Exact canonical frame-hash validation and current authenticated hash comparison distinguish full equality, only-event-omission equality, absent mapping and other differences. All core changes are rejected; event membership remains unavailable, economic grouping unresolved, and admission false. This pure helper is not wired into screening/origins/targets yet; no new collection or reinterpretation of D075.

Self-review: compare every canonical identity field except explicitly absent event IDs;
validate original hash and exact schema; no side effects or caller admission decision;
empty membership never proves independence. Ruff/canonical/whitespace checks pass.
No source/test process active. Commit containing this checkpoint is the safe D076a tip.
Exactly one successor updated to18:35 Europe/London /17:35 UTC Sep28 (+310minutes), same
prompt/task. No protected approval/access blocker, no exhaustion claim, no Phase4.

D076b opt-in screening identity policy accepted: 39 screening/screened-activation tests passed in 697.66s (/tmp/arepo_d076b_final.log). New schema freezes the comparator before collection, retains raw-backed comparison evidence and preserves v1 replay. Asymmetric endpoint original-Git recovery and tamper refusal pass; changed rules remain unavailable. Legacy activation explicitly refuses the new policy pending its versioned origin contract. Worker API wiring and new empirical validation remain; D075 is unchanged.
Self-review: explicit schema/policy correspondence, actual authenticated current mapping, immutable comparison replay, no current event-ID filling, and fail-closed downstream activation. Ruff/canonical/whitespace checks pass. Earlier interrupted test run passed15 then failed only an incorrect test-helper signature; corrected. A mistaken test filename caused one collection-error invocation with no tests run; final command uses the two actual suites. No public source requests or data changes.

## Current recovery — October2 22:45 UTC heartbeat

Tested implementation tip: f98f67a563ab05da58feafa0b854b4da339d0f83; branch codex/arepo-v2-phase-3-prospective-panel; draft PR #16 on Phase2, unmerged. D076b/C complete only as software milestones. Changed screening, activation guard, worker and focused tests.

All tests finished; no collector active and no new public requests this run. D077 protocol committed but unexecuted. Latest supported allowance94% primary/15% weekly used, ordinary usage allowed; preserve safe state before this window exhausts. No reset credit used. One existing successor is October3 04:55 London /03:55 UTC (+310minutes), same task/prompt; no duplicate. No protected approval/access blocker. Phase3 remains incomplete.

D077 completed once under c6f4891661a979ab91755714869288152b8679fb: exhausted-consistent refreshed Gamma frame,236618 distinct/236574 mapped markets,44 unresolved;2367 requests,no retries/errors. Collection interval558.428363s fits the frozen600s screening cap. CLI exit0; complete verification passed. Evidence PHASE_03_FRESH_FRAME_EVIDENCE.json. Old frame remains unchanged; no accepted panel or predictive claim.
D077 ended04:12:49UTC, wrapper elapsed964,766,408,250ns including capacity proof and final repeated CLI verification; acquisition interval is separately558.428363s. No collector remains active. D078 is predeclared, not run at this checkpoint.


D078 measured once under9ea4e38b87ad242ea8d6d37e2536af2c15a69b2e: eight Gamma200 and eight book200 responses,44158 raw bytes. Eight scheduled/six triggered/two control roles across eight distinct markets; four unfilled control slots retained. All current event memberships unavailable; core identities match under the frozen explicit D076 rule. Stratum inclusion2/55 over110 strata; exact first-stage and conditional second-stage fractions retained. Full original-Git recovery passed; wrapper exit0. Screening cutoff04:24:04.526375UTC to recovery04:28:57.489384UTC is292.963009s, exceeding the120s age limit for future activation. No origin or accepted panel. Evidence: PHASE_03_SCREENING_REFRESH_EVIDENCE.json. Do not repeat this accepted measurement or backdate fresh origins; continue PHASE_03_PILOT_EXECUTION_NEXT.md.


D079 — owned pre-source screening context: screening v3/worker v4 retain an immutable bounded context minted by the actual complete selection read. Source completion no longer repeats population replay; cold/original audit still verifies all dependencies before worker return. Default legacy paths remain unchanged. Four new ownership/tamper/cold-recovery tests passed81.15s;39 existing screening/worker regressions passed500.62s. Ruff/backend, canonical and whitespace checks pass. Initial instrumentation replaced a protected function and correctly triggered build-integrity refusal; the test now observes real calls via profiling without replacing code. No public requests or new empirical claims. Activation/runtime wiring remains next; Phase3 incomplete.

Current window: usage84% primary/45% weekly; ordinary usage allowed. Preserve coherent work before exhaustion; no reset credit used. D080 keeps production/public-runtime admission closed. Exactly one successor remains15:15 London.


D080 — owned activation v3: the private screening finish operation can transition directly to activation using its authenticated bounded state. It retains full original frame identity, the explicit comparison policy, report hashes, exact roles and actual read/save clocks. Cold/original activation recovery still verifies the full frame/selection/screening chain. Legacy activation remains unchanged; existing origin workers explicitly refuse v3 until versioned origin identity handling is implemented.64 affected tests passed839.55s: owned_activation, owned_screening, activation, screened_activation and origin_worker. Initial new test expected the wrong original-reader envelope; corrected to compare report.summary, with no implementation/guard change. Ruff/backend, canonical and whitespace checks pass. No public collection or Phase3 acceptance.


## D081 accepted software boundary — October3 19:25 UTC continuation

D081 — owned causal pilot execution: origin v3, due v2, concurrent runtime v4 and pilot worker v5 now compose authenticated screening, activation, causal origins and targets before full original-code audit. Public entry points accept no source payload, clock, transport or provenance override. Full frame identity and current event-membership missingness remain distinct; targets compare exactly against actual frozen origin identity. Legacy versions remain strict. No production or SQL change.

Validation: six new owned-pilot cases passed across development logs (a wrong test-result key was corrected without changing safeguards); 87 affected regressions passed in1334.27s (/tmp/arepo_d081_regression.log). Self-review found runtime_concurrency=None could select the internal screening-only path; public/synthetic wrappers now reject it explicitly. Eight focused invalid-input cases passed0.63s after that guard; no redundant broad rerun. Ruff/backend, canonical contract and whitespace checks pass. Review covered authenticated private context, actual provenance/clock ordering, strict target identity, bounded due capacity, cancellation drainage, immutable dependencies and original-code replay. Synthetic success is not empirical panel acceptance.

Next: freeze PHASE_03_OWNED_PILOT_PROTOCOL.md and execute D082 once under the committed implementation. Preserve all failures/missing controls/windows/related/external values. Phase3 remains incomplete; no Phase4.

D082 launched19:32:58UTC October3 under c881288d80dbeddfc195c6eacceeb63b78f58e20. Preflight free19751321600bytes versus required4884267008bytes. Exclusive script is embedded in the committed protocol; wrapper records immutable launch/stdout/stderr/result. Collection is finite and process-scoped caffeinate prevents sleep. No source changes until process and original audit end. Measurement status must be recovered from those files, never inferred from elapsed time.

## D082 completed empirical execution gate

D082 executed once under c881288d80dbeddfc195c6eacceeb63b78f58e20 and passed its frozen execution gates: eight observed origins/eight valid targets, six triggered roles/two observed matched controls over eight distinct markets; four unfilled controls retained. All56 requests returned200 (24 Gamma/24 book/8 taker-trade),183036 raw bytes. Origin freeze delay8.084763–29.097624s within60s; freeze-to-save1.463–17.300ms within5s; target durable availability5.477850–8.155644s after due within15s. Exact probabilities and raw numerics/clocks preserved. Full original-code audit passed; independent evidence check verified107 artifact hashes/sizes, all eight timing pairs, both matched pairs and exact counts. No code tests repeated for evidence-only changes.

Evidence: PHASE_03_OWNED_PILOT_EVIDENCE.json. Run completed2026-10-03T19:49:41.661088UTC, exit0, elapsed1003342292167ns including selection/audits; no collector remains active. D082 is a successful execution pilot, not predictive evidence or full Phase3 acceptance. PHASE_03_ACCEPTANCE_STATUS.md maps remaining pre-origin windows/history, related/external eligibility and baseline plumbing to the exact D083 next action. Do not rerun D077/D078/D082 or retrofit richer inputs into those origins. No Phase4.

Window shutdown:89% primary/77% weekly used; ordinary usage remains allowed, not exhausted. Save the coherent accepted empirical boundary before starting another integration. Exact next action is D083 in PHASE_03_ACCEPTANCE_STATUS.md. Draft PR16 body updated for D082; one ACTIVE same-task successor verified for October4 01:35 London/00:35UTC. No active test/collector, production change, user-decision blocker or reset redemption. Unrelated untracked files remain untouched.


## D083 component accepted — October4 05:45UTC continuation

Recovered safe tip36d2bcd and open draftPR16 on unchanged Phase2 base. One successor is
scheduled for11:55London/10:55UTC. Latest allowance13% primary/95% weekly used; ordinary
usage remains allowed. Preserve this tested boundary before the larger runtime integration.

Implemented origin_window.py, owned window-origin v4 and manifestv2 in origin_worker/
origin_features. Exact prior/current prices and irregular receipt separation, explicit
identity/provenance/future/stale guards, coverage gaps and actual read/freeze clocks are
retained. Freeze-time expiry preserves numerical history but denies feature eligibility.
New tests: test_research_panel_origin_window.py and test_research_panel_window_origin.py;
reconciliation fixture gains an explicit bid_price parameter. Contract, acceptance map,
phase/master/review and decision D083 are current. Public runtime wiring remains closed.

Initial16 input tests passed122.87s; expanded21 window/origin tests passed255.10s. One initial
fixture mistook a bid-size parameter for bid price; corrected the fixture, no guard change.
Self-review added a final16KiB limit after freeze metadata. Final affected regression:
window_origin/origin_worker/origin_features/window_reconciliation,53 passed611.89s,
/tmp/arepo_d083_regression.log. Explicit isolated SQLite, disabled email, process-scoped
caffeinate; source fixed throughout. No new full-backend or empirical claim.

Self-review covered actual read/freeze age checks, identity and provenance, immutable hashes,
raw corruption, missing/negative/zero distinctions, incomplete coverage, final byte ceilings
and strict legacy defaults. Cold origin replay passes; full original-runtime integration for
the new dependency remains required. No public collection, production change, protected
approval blocker or Phase4 work. Next: owned window batch/runtime integration as stated above.

## D084 working continuation — October4 13:07UTC

Same task resumed during owned-window integration; no accepted work repeated. Allowance
1% primary/16% weekly used, ordinary usage allowed. One same-task successor updated to
19:17London/18:17UTC (+310minutes). Safe committed tip36dab48; working implementation not
yet accepted/committed. No public collection active.

Working files: new owned_windows.py and test_research_panel_owned_windows.py; modified
screening_worker/concurrent_runtime/runtime/original_reader and pre-origin contract. Worker
v6 reserves full40MiB socket+64MiB analysis per possible selected member before sources,
starts bounded per-member observers after real pre-books, retains unavailable pre-books,
and routes runtimev5 to originv4. Original-reader dependency closure is extended.

Initial targeted run session77475, /tmp/arepo_d084.log, explicit isolated SQLite and disabled
email. Prior development failures: invalid fixture horizon/tolerance corrected; sampled
member condition is in item.identity rather than member; canonical selected metadata
comparison now handles in-memory versus persisted representations without changing evidence.
Do not edit source packages until this run ends. Exact next action: consume result, fix real
failures, add cancellation/full-reservation/changed-dependency checks, review legacy runtime
regression, commit and update draftPR16. No empirical or Phase3 completion claim.

D084 targeted integration gates now pass: success/original recovery/tamper case passed;
8 remaining cases passed127.20s (/tmp/arepo_d084_remaining.log). Nine total. Regression
session97711 active: owned_pilot/concurrent_runtime/screening_worker/original_runtime;
/tmp/arepo_d084_regression.log. Source must remain fixed until it ends. Next: consume final
regression result, self-review, commit, update PR16, then freeze a new window pilot protocol.


## D084 — owned bounded windows and runtime (2026-10-04)

Worker v6 starts one bounded observer per actual selected pre-book in independent event
loops, before activation/origins. Whole socket40MiB+analysis64MiB costs per possible member
are reserved before requests with no overlap discount. Runtime v5 binds exact worker/member
hashes and routes actual dependencies to origin v4. Unavailable pre-books retain their
sampled member and explicit missingness; local integrity failures terminate without erasure.
Original-Git recovery authenticates window, analysis, pre-book and raw source dependencies.

Nine new integration cases pass across targeted runs: concurrent success/original replay/
dependency tamper; eight remaining cases127.20s. Final affected legacy regression49 passed
722.18s (/tmp/arepo_d084_regression.log): owned_pilot, concurrent_runtime, screening_worker,
original_runtime. Explicit isolated SQLite/email disabled; source remained fixed throughout.
Ruff/backend, canonical and whitespace checks pass. No full-backend or empirical claim.
Development fixture errors (timing bounds, streaming404 response, string-encoded duration)
were corrected; canonical selected metadata comparison handles saved versus in-memory types.
No causal guard, quota or deadline was weakened.

Self-review covered owned selection/provenance, actual pre-t0 clocks, strict dependency/root
binding, whole reservation, unavailable and disconnected members, terminal failure retention,
cancellation drainage, immutable numerical/gap evidence, original recovery and legacy defaults.
Next: separately committed PHASE_03_WINDOW_PILOT_PROTOCOL.md, execute once and preserve all
results. D082 is unchanged; receipt diagnostics never establish native venue continuity.
Phase3 incomplete; Phase4 remains reserved for a fresh conversation.


## D085 active empirical attempt

Launched under 1c27f31d6c526758d4b27cff4def7d2275de26b5 at 2026-10-04T18:19:01.864785Z.
Exclusive wrapper/script hashes and clocks are retained in data-dumps/fs2_window_pilot_20261004_1_*.
Script comes directly from the committed protocol; no second draw/retry/resume. Source files
must remain fixed until the wrapper result and original-code audit are terminal. Completion
requires inspecting the actual result and frozen gates, never inferring success from time.
DraftPR16 updated/attached. No Phase3 or predictive acceptance yet.


## D085 — failed integrated window pilot (2026-10-04)

Executed once under1c27f31d6c526758d4b27cff4def7d2275de26b5; completed18:38:34.217034UTC,
exit0 with full original-code audit. Forty-six HTTP responses:19Gamma200,11book200,8book404,
8taker-trade200;128019 raw bytes. Eight sampled members retained;3observed origins/3valid
targets, one observed matched trigger/control pair,2unfilled controls. Four completed socket
intervals, but zero histories passed frozen freshness. Source unavailability and replay delay
are distinct limitations. Execution gates fail; Phase3 is NOT accepted.

Evidence PHASE_03_WINDOW_PILOT_EVIDENCE.json preserves raw-linked clocks, exact probabilities,
all failure states, windows and target results;276 artifact hashes/sizes independently verified.
Window ages at read67.367183–103.429699s exceed60s. Prior quote ages at freeze121.217612–
155.643060s exceed120s. Three windows cover1s/10s, one4.196189209s/10s under the original
receipt hold rule; no native continuity claim. No relevant selected external information;
economic grouping remains unresolved. No rerun, redraw, retrospective limit change or Phase4.

Next: PHASE_03_WINDOW_LATENCY_NEXT.md. Remove measured redundant cold replay through bounded
process-owned writer outputs, retain full cold/original checks, then reassess availability and
freeze a separate protocol. The latency fix cannot erase unavailable books or manufacture edge.


Window shutdown:98% primary/47% weekly used, ordinary usage still allowed (not a weekly
exhaustion claim). No reset credit or protected action. All coherent implementation/evidence
committed; no test/collector active. D085 ended18:38:34UTC. DraftPR16 updated and attached.
One same-task successor remains October5 00:27London/October4 23:27UTC. Exact next action is
D086 step1–2 in PHASE_03_WINDOW_LATENCY_NEXT.md, including its narrow private ownership
design. No D084 regression or D085 public run should be repeated without a relevant change.
Unrelated untracked orchestration files remain untouched. Phase3 incomplete; no Phase4.

## D086 recovery — 2026-10-05

Branch codex/arepo-v2-phase-3-prospective-panel, draft PR16 stacked on Phase2. Pre-change safe
commit836f4566a9f0bdd90ca34b893d4843fd25c95878; the commit containing this section is the new
implementation boundary. Changed owned_windows.py, screening_worker.py and two window test
modules. Private acquisition/finish proof removes pre-activation full replay; bounded byte
seals and unchanged full cold/original checks preserve evidence. No original/schema changes.

Validation:19 cases338.88s (/tmp/arepo_d086_final.log) +2 verification-to-proof mutation cases
38.92s (/tmp/arepo_d086_seal.log); final code identical across runs. Ruff/backend, canonical
contract and whitespace pass. Self-review: assignment isolation, source substitution, provenance,
exact missing-member closure, bounds/symlinks, mutation both after and between verification/reuse,
one-shot slots, no detached cancellation writes, unchanged freshness, full original recovery.
No broad unchanged regression repeated and no public source request.

PHASE_03_WINDOW_AVAILABILITY_REVIEW.json verifies D085's8 Gamma payload hashes: all4 missing
pre-books accompanied fresh closed/non-accepting lifecycle. Any future lifecycle/frame remedy
must precede a new draw and preserve the full population; never change D085 denominators.
Allowance last read65% primary/58% weekly used; ordinary usage allowed. One existing same-task
successor updated to2026-10-05 05:37 Europe/London (04:37UTC), exact prompt, no duplicate.
Next planned phase remains04 only in a fresh chat after genuine Phase3 acceptance.

## D086 eight-member result and next action — 2026-10-05

Implementation531c3c38b511069e1c2a5d13d9766f9385cfe2e6. Finite synthetic measurement
`data-dumps/fs2_synthetic_latency_20261005_1` is terminal and must not be rerun/resumed.
Eight10s windows retained; activation refused stale screened roles before any origin/target.
No public request, complete runtime audit, predictive evidence or Phase3 acceptance.

Saved context equals complete post-failure cold replay. Last entry durable availability to
runtime declaration0.622521s; cold replay29.326286833s. This is an observed handoff interval
versus later replay, not randomized A/B or isolated CPU timing. First-batch windows already
81.319464–81.385908s old at declaration (limit60s); second batch22.160243–26.437577s.
Prior quotes49.88355–113.198221s old then; further activation processing caused the stale-role
refusal. These clocks show remaining acquisition/analysis delay; the handoff repair alone is
insufficient. The wrapper lost in-memory profiler timings on exception; those are unavailable,
not reconstructed. Full script, failure trace, clocks and artifact hashes are retained in
PHASE_03_WINDOW_LATENCY_EVIDENCE.json. First extraction needed a tagged-UTC decoding fix;
final independent cold/context equality and evidence extraction passed. Raw runs unchanged.

Exact next action (D087): read this evidence, then make one bounded local read-only CPU/call
profile of existing pre-book/binding/socket-analysis verification over the retained synthetic
inputs. Persist profiling output even on failure. Quantify repeated build/source replay and
queue costs before choosing the smallest repair (owned verified inputs, or persistent/sharded
observation with a causal freeze if required). Keep existing60s/120s freshness, full original
recovery, one observer per token unless measured reliability justifies duplication, complete
population inventory and explicit missingness. Do not repeat accepted21 tests without changes.
No new public run until the repair and separately frozen lifecycle/frame protocol are ready.
The four closed D085 markets remain in their failed draw; no retrospective filtering/redraw.
Phase3 stays incomplete, Phase4 only in a fresh conversation after genuine acceptance.

Shutdown: implementation531c3c3 pushed to draft PR16; evidence/checkpoint commit follows.
No collector/test remains active. Allowance last observed86% primary/61% weekly used before
final evidence/checkpoint work; save coherent state for the single05:37 London successor.

## D087 — measured compilation overhead and bounded expectation cache

Read-only cProfile of retained D086 member000: pre-book487130500ns, with162 compilations
consuming363913126ns; socket analysis2013804375ns, with666 compilations consuming1541182456ns.
Profiling overhead included; not an end-to-end or empirical market measurement. Full script/
results: PHASE_03_VERIFICATION_PROFILE.json. Evidence supports a small verifier optimization
before new observer infrastructure.

Cache at most256 immutable expected-code tuples keyed by exact source bytes AND filename,
with a lock for concurrent first use and LRU eviction. Do not cache successful verification:
every call still hashes current package files, checks the import-time build, checks actual
loaded functions and reads dependency versions. Changed bytes/paths never reuse expectations;
warm function replacement still fails. Output schema, numerical/source recovery and all causal
clocks/freshness remain unchanged. This is not an owner-tamper security boundary.

76 targeted tests passed119.88s: research_build_cache, feature_store_source_run,
research_panel_frame, research_panel_owned_windows, research_panel_window_context. Includes
cold/warm compile counts, mutation after warmup, source byte changes, key separation, threads,
eviction, public override refusals, missingness, cancellation and original-code recovery.
Ruff/backend, canonical and whitespace checks pass. Self-review covered cache mutability/
bounds/concurrency, freshness and unchanged per-call code/file checks. No public request.
Next: one fresh eight-member synthetic measurement at fs2_synthetic_latency_20261005_2,
script /tmp/arepo_d087_benchmark.py, after commit. Same4 workers,10s windows,60s window/120s
history freshness; preserve timing even on failure. Failed D086 roots remain untouched.


D087 measurement completed under5678b10:8/8 observed origins,8/8 histories eligible at freeze,
8/8 observed targets and complete original-code recovery;56 synthetic HTTP calls, no public
requests. Elapsed149.854142709s; owned finish0.177550291s and post-target cold read6.686687208s.
Synthetic diagnostic, not alpha or full Phase3 acceptance. Full clocks, code, script and1270
artifact hashes: PHASE_03_VERIFIER_CACHE_TIMING_EVIDENCE.json. The old failed D086 is unchanged.
Next D088: freeze/execute one complete lifecycle-fresh frame per
PHASE_03_LIFECYCLE_FRAME_PROTOCOL.md, then a separately frozen public pilot. No new observer
infrastructure or freshness relaxation is justified by this successful scoped measurement.

D088 active acquisition launched 2026-10-05T04:45:24.985867+00:00 under f5eee00a6f294b0ce040b94ca95cec71b258dc94.
Preflight free18124161024bytes. Exactly one bounded public frame enumeration;
no production jobs/DB. Source packages must stay fixed through acquisition/recovery.

## D088 complete frame; D089 unattended fresh-frame/pilot boundary

D088 finished2026-10-05 04:58:57UTC underf5eee00, exit0. Rootfs2_capture_0da49550169349f9adc9947dcaecc76f:
235224 distinct rows,235180 mapped,44 unresolved;2353 requests, zero retries/errors/conflicts.
Source interval04:46:15–04:53:20UTC (425.282097s), raw1524579122/retained3739809659bytes,
peak583254016bytes. Full CLI verification passed; report/metadata/wrapper hashes preserved in
PHASE_03_LIFECYCLE_FRAME_EVIDENCE.json. No collector remains. The next assistant continuation
arrived09:47UTC, outside the prospective1h rule. Do not re-age or use this frame for that pilot.

D089 freezes one end-to-end process so verified fresh frame immediately feeds selection and
pilot without an assistant-turn boundary. Existing APIs only; no production/scheduler change.
New frame allocation7GiB (~2x observed retained cost), same4000 requests/3GiB raw/900s/limits,
universe and retries. Full combined reserve13308526592bytes includes frame, all panel/selection/
window/target/original-recovery budgets,2GiB free reserve and34MiB frame-capacity read overhead.
Observed free14327640064bytes; launcher must recheck. Quota/incomplete source stops the chain,
never admits a partial universe. No old evidence deleted or live retention changed.
Exact code and unchanged five pilot gates: PHASE_03_FRESH_WINDOW_PILOT_PROTOCOL.md.
Offline syntax/API budget validation and canonical/whitespace checks pass; unchanged76 tests
are not repeated for orchestration. Review: exclusive roots/logs, immutable build, all-stage
reservation, source completion and real clock gates, no redraw, complete original recovery.
One successor updated to15:57London/14:57UTC, same task/prompt; initial allowance0% primary/
79% weekly used. Phase3 only; no Phase4 or full acceptance claim.

D089 active launch 2026-10-05T09:53:37.618990+00:00 under404ad5efd12c6913ff062aa3f702db1630c08ea4.
Exact script SHA256 2d41c8ef97fb09ec6a9e1bc099e21a78ba86110d667b1bc4391698f59d875bc1. Wrapper/result and stage logs are durable;
source package must stay fixed until terminal. Earlier D088 is complete, not active.

## D089 final empirical result — 2026-10-05

Complete under404ad5efd12c6913ff062aa3f702db1630c08ea4, wrapper exit0 at10:22:50.943457UTC.
No collector/test remains active. Fresh frame236887 distinct/236843 mapped/44 unresolved,
2369requests, no retries/errors/conflicts, full source and original-code audit. Selection
uniformly chose4of109strata (4/109), with exact conditional member/role fractions preserved.
Eight scheduled/three triggered/one control roles span eight unique markets; two unfilled
control slots remain. Five observed origins/five fresh completed histories/five valid targets,
one actually observed matched pair. Six-of-eight origin/history gates FAIL. Phase3 incomplete.
Full immutable clocks, receipts, values,258 independently checked window/origin/report artifacts,
additional target hashes and extraction scripts: PHASE_03_FRESH_WINDOW_PILOT_EVIDENCE.json.

All50HTTPrequests returned200 (21Gamma,21book,8trades),191706raw bytes. The three absent
histories came from genuine one-sided pre-books:5233594 has67bids/0asks;5299067 has74/0;
628957 has0/54. All three Gamma records were active/nonclosed/accepting orders. Thus refreshing
the frame did not cure this limitation; no transport failure, freshness relaxation, retrospective
filtering or repeat-draw-until-success is justified. Five available histories passed unchanged
clock gates after D087. Native continuity remains unproven; these are receipt-time diagnostics.
None of eight questions matches the KNYC quantity. France/Spain EURO2028 questions suggest a
possible relation but do not establish a rule-aware economic group or causal related-price input.
F01/F02/F10/F27, related/external and v1 rolling-z-score inputs remain honestly unavailable.

Self-review: original audit, exact rational stage weights, all8denominators, actual freeze
eligibility, matched IDs, target deadlines, source raw hashes/level counts, gaps and missingness.
No new implementation; prior76D087 tests remain accepted, not rerun. Canonical/whitespace and
JSON/hash checks validate this evidence change. D085 prose previously copied4of110 from D082;
its immutable evidence actually records4of108 (1/27). No old protocol/data was rewritten.

Next action: read this evidence and PHASE_03_ONE_SIDED_NEXT.md. Do not rerun D089 or reinterpret
one-sided books as midpoint observations. Source data cannot retroactively supply the missing
three histories. Develop only the smallest prospective identity-bound observation refinement
needed to measure recovery from one-sided state; preserve failed pilots and all strict gates.
Phase4 stays in a fresh conversation after genuine full acceptance.

## D090 — one-sided diagnostic observation binding (2026-10-08)

Recovered unfinished D090 work after allowance interruption. New observation_binding reader
verifies original targeted identity/book computation while preserving null midpoint for one-sided
and empty books. Explicit socket binding_mode=observation selects a new v2 journal; default
v1 behavior stays strict. Freshness is rechecked at actual read/save/connect/subscription,
with all actual clocks, raw bytes, failure states and original-code recovery preserved.
No caller transport override, origin/history admission or continuity inference. Endpoint
comparison returns unavailable for an unavailable pre-quote instead of converting null to decimal.

34 targeted socket/binding/original-socket tests passed49.65s. Expanded analysis initially found
the null endpoint bug; after its fix51 binding/socket-analysis/endpoint/original-analysis tests
passed71.53s. Initial reader fixture import error corrected before these runs. Logs:
/tmp/arepo_d090b_tests.log and /tmp/arepo_d090d_tests.log. Explicit isolated /tmp SQLite,
AUTO_MIGRATE=false and disabled email. Ruff/backend, canonical and whitespace checks passed.
Self-review covered opt-in version/event consistency, unavailable arithmetic, legacy defaults,
source identity, fresh subscription and old evidence preservation. These are synthetic software
tests, not empirical Phase3 acceptance. No collector/test active before the next launch.

Next: execute once the committed PHASE_03_ONE_SIDED_DIAGNOSTIC_PROTOCOL.md; fixed three
D089 cases, six bounded HTTP reads, at most three60s subscriptions, all failures retained.
No full-frame redraw, retrospective D089 repair or production action. Then preserve measured
availability/coverage and decide the next prospective design from actual evidence.

D090 empirical diagnostic completed once under e8021098b19cb9d6d8651b14c378767ea54a2200,
2026-10-08 02:49:40–02:50:54UTC, exit0. Six HTTP requests,14188 raw bytes; two closed/nonaccepting
Gamma markets with book404, one active market with an observed one-sided book. The active case
completed60s, one book frame/five PONGs, no received two-sided recovery. Original book/socket/
analysis recovery passed;183 artifact hashes preserve519491bytes. Full result:
PHASE_03_ONE_SIDED_DIAGNOSTIC_EVIDENCE.json. No collector remains; D089 remains failed.
Legacy coverage labels the valid one-sided frame invalid_or_conflicting_message and60s uncovered.
Next D091: distinguish valid one-sided/empty state from malformed input in an explicitly versioned
receipt-coverage diagnostic, with zero midpoint/imbalance admission and unchanged legacy output.
Use synthetic transition tests plus read-only checksum-bound reanalysis; no new collection needed
for this parser distinction. Preserve D090's original analysis and never assert socket continuity.

## D091 — distinguish one-sided receipt state from malformed messages

Explicit window-coverage policy v2 is selected only for D090 observation sockets. Valid one-sided
or empty books retain exact side counts/state hash and replay lineage, while midpoint/imbalance
remain unavailable and the entire interval is uncovered until an actual two-sided update arrives.
Malformed/conflicting input still invalidates replay and requires a fresh full snapshot. PONGs
do not refresh any quote. Legacy policy v1 and its old numerical output remain unchanged.
59 targeted coverage/binding/socket-analysis/original-analysis cases passed39.56s, including
one-sided/empty states, delta recovery, side removal, malformed gaps, no invented history and
original-code recovery. Source formatting corrected afterward only; no behavior change.
Ruff/backend, canonical/whitespace checks pass. Self-review: explicit version selection, bounds,
state invalidation/recovery, exact receipt durations, all source/phase admission flags remainfalse.
Next perform checksum-bound retrospective reanalysis of D090 once under this committed code,
preserving its old analysis. No new external request or empirical acceptance is implied.


D091 reanalysis completed under282ed360d58730809fb5a194dd733f51e368cc41. All183 original
artifacts verified by hash/size before read-only projection. PHASE_03_ONE_SIDED_REANALYSIS.json
retains the script, input/build hashes and actual new analysis clock. Explicit retrospective
classification changes invalid-message to valid one-sided state; covered duration stays0,
uncovered duration stays60000000000ns. Original D090 analysis/raw clocks remain unchanged.
No source request, new observation, history, acceptance or predictive evidence.


## D092 — explicit one-sided observation in the owned panel worker

Opt-in OwnedWindowPolicy.binding_mode=observation selects worker v7 and observation socketv2;
legacy quote mode retains worker v6 and its persisted policy shape. Verified one-sided/empty
pre-books can now be observed without filtering sampled members. The worker checks policy/socket
version consistency, current lifecycle/core identity and all existing acquisition/cold-replay
seals. Real source clocks, freshness, quotas, cancellation and original-code audits stay binding.
Origins still require actual eligible quotes; a two-sided frame received after an unavailable
pre-book never retroactively supplies its midpoint or an eligible price history.

24 affected owned_windows/window_context tests passed172.73s, including two complete synthetic
one-sided pilot variants (remains one-sided versus later two-sided), original runtime recovery,
unavailable histories, policy tamper rejection, legacy behavior, reservations, cancellation and
byte-seal mutation checks. Log /tmp/arepo_d092_tests.log; explicit isolated /tmp SQLite/emailoff.
One line was wrapped after tests for lint only. Ruff/backend, canonical and whitespace pass.
Self-review: explicit mode/version dispatch, legacy serialization, full missing-member accounting,
no history/continuity inference, authenticated dependency chain and unchanged capacity bounds.
No public run under D092, no Phase3 acceptance, no Phase4 or production action.

Next: PHASE_03_ONE_SIDED_NEXT.md current-state section. Reconcile remaining family eligibility
with measured source/selected-question evidence, then freeze a separately justified finite
prospective design before any new requests. Do not repeat D089/D090, weaken old6/8gates or
implement speculative services. Latest disk snapshot13915540KiB free; remeasure and reserve the
entire proposed run before launch. No test/collector remains active.

October8 window shutdown: D092 implementation/evidence006b006 pushed; draftPR16 body rewritten
around current results and remaining gates. Allowance94% primary/31% weekly used, ordinary usage
still allowed; save before primary exhaustion, not a claim of weekly exhaustion. No reset credit
redeemed. No test/collector active. One existing same-task successor remains08:58Europe/London
(07:58UTC), five hours ten minutes after this run. Exact next action is the current checkpoint
bullet and PHASE_03_ONE_SIDED_NEXT.md current-state section. Preserve all empirical failures;
Phase3 incomplete, Phase4 not started. Unrelated untracked orchestration residue untouched.


D094 launched once at2026-10-08T08:01:51.229052UTC, implementation53c19a43d9784e7f98a41e22131799f5a63b7e1f.
Script SHA2565eede31105dcff85d3685f2d1a3103143a33a805b7443c0ea8e5dae09616bee0.
Frame root data-dumps/fs2_capture_cb25bb8e990e43c38d0215decfc43768; subsequent roots use
observation_pilot_20261008_1. Free14128500736bytes exceeded reserved13308526592 at launch.
Wrapper files data-dumps/fs2_observation_pilot_20261008_1_launch.json, _stdout.log, _stderr.log,
_result.json (terminal only). No assistant-stage gap. Source packages remain frozen through
original recovery. This record is activity, not a completion or acceptance claim.


## D094 terminal evidence — October8

Single attempt under53c19a43d9784e7f98a41e22131799f5a63b7e1f completed08:33:57.532132UTC,
exit0, full original-code audit passed. Complete frame267180 distinct/267136 mapped/44unresolved;
2672requests, no retries/errors/conflicts, source interval531.668300s, raw1722038541bytes,
retained4220053077bytes. Four of109 strata sampled (4/109) with exact conditional weights.
Eight scheduled/one triggered/one matched control roles over eight markets; zero unfilled
control slots. Five observed origins/five eligible completed histories/five valid targets.
Both six-of-eight gates FAIL. Original audit, observer-attempt accounting, matched control,
target coverage, origin clocks and reporting pass. Phase3 remains incomplete.

50HTTPrequests:21Gamma200,17book200,4book404,8taker-trade200;142618raw bytes. Six subscriptions
completed their10s intervals. TyroneTracy market3400453 remained one-sided (0bids/20asks at
pre-read); coverage0. Five other windows have bounded receipt coverage (four1s, one1.068165750s).
Two Bitcoin markets5424711/5424716 are closed/nonaccepting with book404; their specified08:00UTC
candle was already past before this frame's08:02:40 start. All eight remain in the denominator.
One-sided deltas reported best_bid0 against an empty bid side and were conservatively marked
conflicting; do not silently reinterpret0 as an empty-side sentinel or invent a prior quote.

PHASE_03_OBSERVATION_PILOT_EVIDENCE.json preserves full manifests, exact timing/numerics,
321 independently checked artifacts, source receipts/raw hashes, all8resolution descriptions,
extractor scripts and gate results. Related Bitcoin thresholds share a candle rule, but no
pre-origin related-price input was bound. Sports/Bitcoin quantities do not match KNYC weather.
No new external source rights/admission; unsupported families and v1 components stay unavailable.
Self-review checked exact sampling products, all denominators, source failures, actual clock
ordering, observed matched IDs, target selection, original recovery and no retrospective repair.
Evidence-only change: no accepted code tests repeated; JSON/hash checks and canonical/whitespace
checks pass. No collector/test active, production/retention untouched, Phase4 not started.

BLOCKED — CAPACITY AND REQUIRED EMPIRICAL DATA UNAVAILABLE for another full measurement at
current bounds. Free9511227392bytes versus required13308526592 (short3797299200bytes).
No repeated draw, source-universe narrowing, destructive cleanup, paid/production storage or
missing-history manufacture is an acceptable workaround. Preserve this failed run. A future
protocol must first reconcile sampling-time lifecycle/close eligibility with its intended
population while retaining the complete discovery inventory and all old denominators; it may
not merely redraw until6/8passes. Then remeasure/reserve capacity before collection.

Exact next action: recheck capacity once on continuation. If unchanged, stop quietly without
new commits/tests/collection. After capacity is available, review that temporal-eligibility
question against current sampling/metadata code and raw frame evidence before designing any
separate prospective attempt. Do not rerun D094. Any additional storage/deletion or production
change requires its own applicable authorisation; no such approval is implied here.

Allowance84% primary/45% weekly used; ordinary usage allowed. Stopping at the data/capacity boundary, not claiming allowance exhaustion. One existing same-task successor14:08London/13:08UTC. No reset credit redeemed.


D095 capacity review:~15GB free before cleanup; current full reservation13.31GB is available.
Deleted only35151bytes of verified unreferenced obsolete prompt text; hashes/audit in cleanupJSON.
User's current safe-cleanup authorisation supersedes older blanket local-residue restrictions;
all research evidence/recovery dependencies remain protected. No test/collector active after
D096 validation (101+1cases). D096 contract records exact code scope and self-review. The old
capacity blocker is historical, not a reason to stop this run. One general same-task heartbeat
retained; no duplicate chain. Prior D094/D089 failure gates remain immutable.
