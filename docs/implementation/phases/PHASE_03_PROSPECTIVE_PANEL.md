# Phase 03 — Bounded prospective panel

Status: incomplete — D110 failed665.13s frame interval before selection, despite original audit passing. D108 processing improvements pass209 tests but do not guarantee full-run timing. Next D111 bounded transport diagnostic; follow live checkpoint.

## Objective

Build and validate a deliberately sampled prospective collector with scheduled controls and causal target collection.

## Why this phase exists

A selected signal-only dataset cannot answer incremental-information questions.

## Research basis

Model protocol sections 2–5, Feature Store preservation matrix; H02/H08/H10/H14/H15/H24/H27/H28 and selected official-source cases. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 02 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

2026-09-21: Phase 2 accepted at `747485c`. Phase 3 sampling/target rules plus standalone
Gamma keyset frame capture/verifier/CLI are implemented on draft #16. First-page cost and
first finite enumeration are preserved; the latter is incomplete at 256MiB after 40,900
complete rows and a partial 410th page. The second, separately frozen capacity attempt retained 100,000 rows but stopped incomplete
at its request limit. D034 original-build read receipts now permit verified consumption through
the exact original Git code without mutating source evidence (755 regression tests after D035). D035 measures explicit 400,000-member sampler capacity;
D036 larger finite bounds are implemented (766 tests). Attempt 3 stopped on a response timeout
after 7,300 complete rows; no complete frame exists. Follow the data gate and next-action
contract in ../PHASE_03_CAPACITY_REFINEMENT.md. See ../PHASE_03_FRAME_CONTRACT.md,
../PHASE_03_REVIEW.md and the evidence JSONs. No model-ready panel/origins exist yet.

D037 bounded retries were then tested (784 tests) and used in attempt 4. That attempt stopped
after 20,000 rows at retry exhaustion, with unrecovered ConnectError/TimeoutError. All retry
attempts and partial bytes remain preserved; no complete frame or representative population
was established. See PHASE_03_ENUMERATION_ATTEMPT_4.json and the live checkpoint.

The renewed continuation evaluates D038 opt-in connection reuse with unchanged finite bounds.
Loopback/fault tests, full regression, self-review and a committed protocol precede any fifth
attempt. This is a transport experiment, not a relaxation of the required complete-frame gate.
Attempt 5 then completed under `41fcb01`: 175,427 distinct source markets, 175,383 usable
outcome mappings, 44 unresolved, no duplicates/conflicts/errors. All verification passed.
The four original failures stay preserved. No collector is running. Next: durable policy,
seed, complete inventory, actual read/projection/selection records; see the panel contract.

D039's pure exact metadata projection is now implemented and tested (818 full backend tests,
including 23 new projection cases). It records no actual read or origin; integrating it with
the durable journal remains the next milestone. Unknown metadata must not exclude markets.

D040 now implements durable development policy/seed/full inventory/actual read/projection/
scheduled selection and read-only replay (841 full tests). The local measurement below
ran under committed code. This scheduled-only development selection
does not supply triggers, controls or fresh origins; those acceptance gates remain open.

Actual D040 measurement passed under `018dbd3`: all 175,427 source rows preserved, 175,383
eligible sampling members, 107 draws/strata and 44 unresolved rows retained. Reconstructed
development only. All mapped rows lack the explicit category field; unknown-category strata
remain, not inferred taxonomy. Costs/hashes: PHASE_03_SELECTION_ATTEMPT_1.json.

D041 `d24ed88` adds bounded original-build selection verification (851 full backend tests).
The actual saved selection read passed under original `018dbd3`, preserving the entire
report/plan, seed, weights, old clocks and reconstructed status. New actual read receipt
and hashes: PHASE_03_ORIGINAL_SELECTION_READ_EVIDENCE.json. Next refine freshness,
actual input-read/computation/origin boundaries, trigger/control evidence and a separate
prospective pilot protocol. All origins and pilot acceptance remain gated; current local
free disk is below expanded-frame preflight, so inspect checkpoint constraints first.

D042 adds explicit assessment-aware v3 sampling with 884 passing backend tests. Unknown,
unavailable and stale assessments stay scheduled but cannot masquerade as untriggered
controls. Legacy plan hashes remain unchanged. The next journal milestone must record
actual verified source reads; pure assessment declarations cannot establish those clocks.

D043 now records and verifies bounded actual reads of completed SourceRuns, preserving all
source facts and their original clocks. UTC/monotonic causality, closure and failure tests
pass within the **904-test** backend regression. Next build exact quote/identity feature
computation on these reads, with separate freshness and actual computation/durability clocks;
neither source availability nor this read receipt is itself a research origin.

D044 pure exact quote/identity projection passes the **930-test** regression, including
actual D043 serialization, conflicting/late mappings, stale and invalid quotes. It creates
no actual computation clock or origin. Resume with
[the next writer contract](../PHASE_03_QUOTE_COMPUTATION_CONTRACT.md), then implement and
verify durable computation before advancing toward trigger/origin/pilot integration.

v1 complete discovery, separate scan/collect leases, public eligibility and target cadence
remain unchanged. No production scans were restarted. v2 collection uses isolated local
journals and public read endpoints only. Upcoming journal/consumer requirements are in
[the panel journal contract](../PHASE_03_PANEL_JOURNAL_CONTRACT.md).

## In scope

### Refinement after Phase 2 acceptance

Phase 2 supplied new receipt-time Gamma/book/trade source journals (685 tests), not a
population frame or model origins. Streams and Coinbase remain diagnostic-only. Native
event time, historical fill identity and economic independence are unresolved. Review
../PHASE_02_SOURCE_ADMISSION.md and ../../architecture/V2_PROSPECTIVE_SOURCE_ADMISSION.md.

Implement in reviewable milestones:

1. Pure versioned protocol, exact stratified sampling and matched control planner, then
   first-valid receipt-time quote target selection. No collection or evidence claim in this
   milestone. Preserve missing strata and all exclusions. Incomplete source pages cannot be
   labelled representative of the eligible universe. Preserve rational inclusion weights;
   a nonterminating probability is not rounded and called exact.
2. Build a prospective frame adapter with explicit scope, pagination/exhaustion evidence,
   byte/request deadlines and source-native identity. Inspect existing Gamma keyset code
   and current official protocol; do not call v1 application startup or alter its public
   eligibility. Complete discovery and the bounded deep sample remain separate.
3. Durable panel protocol/frame/sampling records, bounded leases and actual feature-read,
   computation/origin persistence. Reuse primary-journal semantics with separate later SQL
   indexing; no caller-payload prospective bypass. Pin source and panel build versions.
4. Bounded scheduled/triggered/control collector and due targets. Reserve control/outcome
   budgets in advance; budget stops retain missing labels, never drop inconvenient origins.
   Record family eligibility: complete flow, pre-trade depth, persistent imbalance, withdrawal,
   related markets and external information require their own measured evidence coverage.
5. Freeze the pilot protocol before collection. Run finite local tests and actual pilot,
   report timing/control/target coverage and exact numerical preservation. Never reinterpret
   a failed pilot by relaxing its thresholds afterward. No Phase 4 until all exit gates pass.

Initial target implementation follows the research proposal: first valid two-sided,
noncrossed quote at/after actual origin+horizon within a frozen tolerance, with receipt-time
basis on both ends. One-minute/5-second timing is a development pilot candidate, not a
proven guarantee or final confirmation protocol. Sparse quotes do not identify path extrema.

Build and validate a deliberately sampled prospective collector with scheduled controls and causal target collection. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Reload contracts and Phase 2 measured source matrix. Branch codex/arepo-v2-phase-3-prospective-panel; inspect source limitations before fixing panel scope.
2. Write and hash the panel protocol: enumerated population, sampled deep subset, inclusion probabilities/strata/seed, scheduled and trigger arms, matched untriggered controls, exclusions and source/byte/request/time ceilings.
3. Keep complete market-universe discovery and existing production eligibility intact. A bounded deep research sample is separately identified; record frame completeness and never claim sample coverage equals universe completeness.
4. Define price/context, books, raw trades, depth-normalised flow, persistent imbalance, withdrawal/resiliency, related markets and feasible external-source primitive windows. Ineligible family gets explicit missingness, not surrogate tags.
5. Implement standalone collector with separate discovery, dense-window and due-outcome leases/deadlines, idempotent commits, stop budgets and recovery. No automatic production scheduler edits.
6. Freeze origins, control sampling and primitive feature manifests before labels. Include quality/late/abstention records. Prospective model claims wait for Phase 4 locked baselines; Phase 3 pilot is measurement/development only.
7. Implement target definitions and collectors using first valid quote at/after target within registered tolerances; retain missed/late/closed windows. Dense path requirements for first passage/extrema cannot be faked from sparse polls.
8. Validate no-change and simple momentum recording fixtures only as plumbing, without choosing scientific winners. Pin reproducible v1 comparison inputs; full baseline contract lock belongs to Phase 4.
9. Run finite nonproduction replay/crash/retry tests. A bounded public read pilot is permitted only with admitted rights/access and measured local capacity; production scans, hosted schedules or paid sources require user approval.
10. Report observed timing distributions, source gaps, control coverage, bytes/rows, prediction-recording lag and target coverage. Set confirmatory thresholds before outcome inspection; failed timing redirects future protocol version, not relabelled past data.
11. Exit only with a timestamp-faithful pilot or an explicit access/data blocker. Commit and self-review, update all recovery docs and draft PR. Fresh confirmation accumulation is not synthetic replay.

## Likely modules/files

New backend/astrolabe/research_panel/{protocol,sampling,collector,targets,cli}.py; isolated scheduling helpers, new bounded panel tests. No workflow or frontend changes.

## Data model, API and migration implications

Append-only origins/observations/features/labels/manifests; standalone nonproduction collector. Existing production cadence and API unchanged.

## Tests required

Fixed-seed sampling reproducibility and nonzero control coverage; no top-N-only universe; exact inclusion probabilities and exclusions; clock and future-input traps; pre-trade depth; reconnect/gap invalidation; retries/crashes/duplicate leases; late/missing/closed targets, first valid quote selection; controls preserved during budget stop; cold round trip of registered windows; bounded pilot timing/volume report.

## Acceptance criteria

Bounded representative nonproduction pilot preserves scheduled controls, exact inputs and clocks; origins precede outcomes; target timing/coverage passes its frozen measurement contract. A replay-only run cannot satisfy the real prospective measurement gate.

## Exit checklist

- [ ] Prerequisites reloaded and plan refined against real outputs.
- [ ] All scoped tasks and acceptance criteria satisfied; limitations explicit.
- [ ] Required tests passed with exact command/target/result recorded.
- [ ] Diff self-reviewed for causal leakage, data loss, unrelated changes and protected boundaries.
- [ ] Documentation/decision log/master status current.
- [ ] Coherent safe work committed; branch and draft PR/dependency recorded.
- [ ] Checkpoint updated with safe commit, files, tests, blockers and exact next action.

## Protected boundaries

Never fabricate prospective observations, tune on final confirmation, or treat repeated rows as independent events. Preserve complete discovery separately from public limits and sampled deep collection. Archive equivalence does not authorise deletion. A protected action requires the user's explicit decision; record BLOCKED — USER DECISION REQUIRED with the concrete action. Missing access/data is a real blocker; synthetic fixtures are not a substitute for empirical acceptance.

## Next ordered integration contract

Read ../PHASE_03_PANEL_ORIGIN_CONTRACT.md before implementing panel declaration, fresh
selection/origins and due collection. D046 runtime evidence is
../PHASE_03_TARGETED_QUOTE_EVIDENCE.json. No accepted panel or model-ready origins yet.

## Handoff/output

Frozen sampling/measurement protocol, bounded pilot dataset/manifests, timing/coverage/cost report and baseline-ready origins.

### D050 fresh selection and next capacity refinement

Declaration-bound selection now uses its immutable seed, full capacity reservation, verified
original frame, exact complete inventory and explicit D042 not-assessed states. Freshness
is checked at actual cutoff and durable selection acknowledgement. No legacy draw is
promoted, no unknown becomes a negative control, and slot overflow fails without truncation.
See ../PHASE_03_FRESH_SELECTION_CONTRACT.md. No live collection used the new path.

Before sizing a live run, implement the separately tested optional compact writer profile in
../PHASE_03_COMPACT_COMPUTATION_CONTRACT.md; do not assume small observed responses imply
a small enforced cap. Then integrate actual origin intents, source/compute consumption and
due targets under the full panel contract. Phase 3 remains incomplete; Phase 4 stays gated.

D051 now implements explicit compact input-read/computation quotas and declaration/selection
binding. Default schemas and reservations remain unchanged. No collector uses this mode yet.
The next executable integration contract is ../PHASE_03_ORIGIN_WRITER_NEXT.md: actual activation,
exclusive per-slot intents, guarded fixed requests, computation consumption and immutable
origin/target records. Follow its tests before any new local live measurement.

D052 actual activation consumes/reverifies selection and selected identity/role lineage,
reserves additional runtime metadata, and anchors schedules to its actual durable save.
Twenty focused tests and 1,125 full backend tests passed. No source collector or origin is
enabled. Next execute the worker portion of ../PHASE_03_ORIGIN_WRITER_NEXT.md.

D053 now exercises the actual activation→intent→source→read→compute→origin path with
synthetic transports only. Nineteen focused and 1,144 full backend tests pass. Partial raw
evidence, abstentions, expired/late slots and original freeze/save times remain preserved.
See ../PHASE_03_ORIGIN_WORKER_CONTRACT.md. Next: frozen-identity target adapter and due worker;
live collection, measured controls and full pilot acceptance remain gated.

D054's versioned target adapter retains origin mapping availability, fresh identity/lifecycle
consistency, exact source-quality states and durable computation availability. Thirty-two new
cases and 1,176 full tests pass. Next execute ../PHASE_03_DUE_WORKER_NEXT.md; this pure helper
does not authenticate or persist outcomes and does not enable a live collector.

D055 now implements separate synthetic due collection and full recovery: fixed attempts,
original deadlines, verified origin-before-request causality, preserved failed/late/closed
states and incomplete-evidence blocking. Outcome availability includes target/adapter
durability; signed midpoint change is a price diagnostic only. All 1,193 backend tests pass,
including 17 new due-worker cases. Next refine the interleaved orchestration boundary in
../PHASE_03_DUE_WORKER_NEXT.md. No live collector, SQL labels or accepted pilot exists yet.

D056 composes the origin and due writers into a serialized queue with immutable per-origin
plans, actual dispatch clocks and full evolving-queue replay. Original-build recovery is
covered separately. Acceptance results belong in the live checkpoint/review. The next ordered
work is [numerical features and windows](../PHASE_03_FEATURE_WINDOWS_NEXT.md): snapshot
primitives and actual computation first, then measured dense-window coverage and controls.
The existing family limitations remain explicit; Phase 4 is still gated.

D057 now preserves exact F08/F09 snapshot components, source-ordered levels, explicit missingness
and actual durable computations with original-build recovery. 170 affected regression checks
passed. See ../PHASE_03_BOOK_COMPUTATION_CONTRACT.md. Next implement the bounded capture and
coverage contract ../PHASE_03_DENSE_WINDOW_NEXT.md; keep native sequence gaps explicit. This
milestone does not supply the registered continuous-window features or admit the live pilot.

D058 adds finite synthetic raw-window capture, fixed heartbeats and original-code recovery;
40 affected tests pass. See ../PHASE_03_WINDOW_CAPTURE_CONTRACT.md. Next: decoded coverage
and honest numerical replay, then causal identity/pre/post reconciliation and bounded live
transport. Duration completion is not gap-free coverage or pilot acceptance.

D059 now records decoded receipt-window diagnostics with exact time weighting, missing intervals and actual read/computation/durability clocks. Ninety affected checks passed, including original-code recovery. Next execute ../PHASE_03_WINDOW_IDENTITY_NEXT.md. Phase 3 remains incomplete; Phase 4 will begin only in a fresh conversation after the required handover.

D060 adds actual pre-window source reads, durable ordered identity binding and derived synthetic subscription, with original-code recovery. Seventeen new tests passed; final affected regression is recorded in the checkpoint/review. Next implement steps 4–6 of ../PHASE_03_WINDOW_IDENTITY_NEXT.md: post-window request chronology and endpoint comparison. Live transport and full Phase 3 pilot acceptance remain gated.

D061 implements post-window primary request-start verification and exact best-quote endpoint
reconciliation with retained changed/closed/failed/stale/gap states and original-Git recovery.
See ../PHASE_03_WINDOW_RECONCILIATION_CONTRACT.md; final validation is in the checkpoint/review.
Next implement ../PHASE_03_SOCKET_TRANSPORT_NEXT.md before a public diagnostic. No live or
empirical acceptance is inferred from these synthetic tests. Phase 4 remains a fresh-chat task.

D062 supplies the fixed socket connection primitive and actual loopback fault tests, with no
collector/journal integration or public connection. See ../PHASE_03_SOCKET_TRANSPORT_NEXT.md for
the remaining versioned durable driver, source/coverage/reconciliation integration and required
committed diagnostic. The primitive alone does not satisfy those tasks or Phase 3 acceptance.

D063 adds the versioned durable socket driver with verified prebinding, actual send/receive/record/
fsync clocks, finite wire/storage budgets, explicit failures and original recovery. Forty-seven
affected checks passed. Next execute ../PHASE_03_SOCKET_ANALYSIS_NEXT.md before a public diagnostic.
No measured source/pilot admission is claimed; Phase 4 remains a fresh-conversation task.

D064 adds versioned durable consumption of D063 socket evidence into exact receipt coverage and
a separately authenticated optional post-window comparison. Refused/early/missing/changed/failed
states, provenance, actual computation clocks and full original-code recovery remain explicit.
See ../PHASE_03_SOCKET_ANALYSIS_CONTRACT.md and ../PHASE_03_REVIEW.md for acceptance. No public
socket measurement or live panel admission yet; separately frozen diagnostic protocol is next.

D065 composes one fixed-target public diagnostic with Git-verified code, full capacity reservation,
explicit source/window/post branches and original-code recovery. Eight affected tests passed;
see ../PHASE_03_SOCKET_DIAGNOSTIC_PROTOCOL.md. Run once only after this protocol/runner is committed
and the draft PR updated. A source diagnostic cannot satisfy the representative pilot gate.

D066 supplies predeclared exact snapshot-imbalance assessment journals with authenticated primary
request chronology, genuine measured negatives, explicit unavailable states and full original-Git
recovery. 52 affected tests pass; no measured assessment/control run or sampler admission yet.
See ../PHASE_03_TRIGGER_ASSESSMENT_CONTRACT.md. D065 historical socket result remains immutable.

Current validation blocker (2026-09-25): full backend attempt stopped at 728 passed/19 local
capacity failures. Required disk reservations remain unchanged. See ../PHASE_03_FULL_REGRESSION_CAPACITY_EVIDENCE.json
and checkpoint; obtain sufficient local test capacity before rerunning, then continue the
screening/control contract. Phase 3 remains incomplete.


2026-09-27 recovery: local capacity blocker cleared. Unchanged full regression: 1,438 passed,
4 failed (three early UTC intents, one pause-staled pre-binding). D067 now rechecks UTC after
timer completion without weakening causal deadlines; all 55 affected cases pass across the
recorded targeted runs. Full evidence and commands are in the checkpoint/review. Resume
screening/control integration; Phase 3 remains incomplete and Phase 4 stays in a fresh chat.


D068 screening declaration and authenticated matched-role consumer pass 64 affected tests
(140.15s). They reuse the existing selection/sampler, preserve conditional weights and explicit
unknown/unfilled states, and recover through original code. No source worker, origin/runtime
admission or empirical acceptance yet. Continue PHASE_03_SCREENING_CONTROL_NEXT.md; Phase 3
remains incomplete, and Phase 4 begins only in a fresh conversation.

D069 bounded stratum selection passes 193 affected tests (217.52s); full inventory and exact first-stage probabilities retained. Continue the full-reservation source worker and verified-role/runtime integration. This remains synthetic software validation, not pilot acceptance.

D070 bounded synthetic screening worker passes 29 affected tests (189.01s). Whole current-runtime/recovery reservation, bounded concurrency and cancellation drainage implemented. Next: authenticated screened-role activation, scalable runtime and empirical pilot. Phase 3 incomplete.

D071 screened-role activation accepted with 57 affected tests (402.86s). Actual evidence availability/freshness and role capacity verified; legacy/original recovery passes. Next: bounded concurrent screened runtime. Empirical Phase 3 gates remain open.

D072 bounded concurrent screened runtime accepted as a synthetic software milestone: 21 affected tests passed in 246.37s. Reserved target capacity, actual queue/child replay and cancellation drainage pass. No public runtime or empirical admission. Next resolve numerical-window and selected-external observation integration before the bounded pilot; Phase 3 remains incomplete.

D073 NWS external source path is implemented/tested (105 affected cases, then 57 after the final GeoJSON header change). Current Coinbase rights exclude its admission. Frozen one-request NWS protocol: PHASE_03_EXTERNAL_OBSERVATION.md; empirical result pending. Station data has no automatic market/rule relevance, forecast or daily-extreme admission. Phase 3 remains incomplete.

D073 measured once under `77d6652`: HTTP 200 observed prospective NWS response, actual input read and original-Git recovery passed. Evidence: PHASE_03_NWS_SOURCE_EVIDENCE.json. The fixed KNYC reading has no automatic selected-market relevance and does not complete Phase 3. Do not repeat this measurement. Resume the live checkpoint's numerical-family/origin integration step.

D074 numerical origin integration accepted as a synthetic software milestone: 44 affected tests passed in 615.56s. Exact snapshot ratios, actual computation/freeze clocks, ineligible-origin preservation, due targets, original-Git recovery and legacy compatibility pass. No public runtime or predictive admission. Next execute PHASE_03_SCREENING_MEASUREMENT_PROTOCOL.md to measure source/control limitations before further window orchestration; all full pilot gates remain.

D075 public screening entry point accepted as software only: 16 screening-worker tests passed in 156.35s. Public API accepts no transport/provenance override; prospective assignment lineage is checked before source construction, while synthetic API still requires MockTransport. Existing concurrency, budgets, raw failures, cancellation and original recovery pass. No public measurement yet. Execute the single frozen script in PHASE_03_SCREENING_MEASUREMENT_PROTOCOL.md; no redraw/retry.

D075 measured once under e271497: eight Gamma 200, six book 200, two book 404; 41,576 raw bytes. All eight screens remain unavailable because targeted responses omit frame event IDs; all other identity fields match. Three positive/three negative snapshot calculations are not admitted roles. Original-Git recovery passed; no origins or accepted panel. Evidence: PHASE_03_SCREENING_MEASUREMENT_EVIDENCE.json. Next: PHASE_03_IDENTITY_COMPARISON_NEXT.md; do not rerun or reinterpret this attempt.

D076a comparison primitive implemented: 28 focused tests passed in 0.36s. Exact canonical frame-hash validation and current authenticated hash comparison distinguish full equality, only-event-omission equality, absent mapping and other differences. All core changes are rejected; event membership remains unavailable, economic grouping unresolved, and admission false. This pure helper is not wired into screening/origins/targets yet; no new collection or reinterpretation of D075.

D076b opt-in screening identity policy accepted: 39 screening/screened-activation tests passed in 697.66s (/tmp/arepo_d076b_final.log). New schema freezes the comparator before collection, retains raw-backed comparison evidence and preserves v1 replay. Asymmetric endpoint original-Git recovery and tamper refusal pass; changed rules remain unavailable. Legacy activation explicitly refuses the new policy pending its versioned origin contract. Worker API wiring and new empirical validation remain; D075 is unchanged.

D076c worker policy integration accepted: 19 worker tests passed in 205.20s, followed by 3 focused asymmetric-policy/original-recovery tests in 51.65s after import/line-format cleanup. Explicit identity_policy selects worker v3 and frozen screening v2; public/synthetic provenance still derives from actual transport. Defaults retain strict legacy behavior. Whole reservations, source failures, original-code recovery and no-redraw behavior pass. No new public collection; legacy activation remains barred from the new policy.

D077 completed once under c6f4891661a979ab91755714869288152b8679fb: exhausted-consistent refreshed Gamma frame,236618 distinct/236574 mapped markets,44 unresolved;2367 requests,no retries/errors. Collection interval558.428363s fits the frozen600s screening cap. CLI exit0; complete verification passed. Evidence PHASE_03_FRESH_FRAME_EVIDENCE.json. Old frame remains unchanged; no accepted panel or predictive claim.


D078 measured once under9ea4e38b87ad242ea8d6d37e2536af2c15a69b2e: eight Gamma200 and eight book200 responses,44158 raw bytes. Eight scheduled/six triggered/two control roles across eight distinct markets; four unfilled control slots retained. All current event memberships unavailable; core identities match under the frozen explicit D076 rule. Stratum inclusion2/55 over110 strata; exact first-stage and conditional second-stage fractions retained. Full original-Git recovery passed; wrapper exit0. Screening cutoff04:24:04.526375UTC to recovery04:28:57.489384UTC is292.963009s, exceeding the120s age limit for future activation. No origin or accepted panel. Evidence: PHASE_03_SCREENING_REFRESH_EVIDENCE.json. Do not repeat this accepted measurement or backdate fresh origins; continue PHASE_03_PILOT_EXECUTION_NEXT.md.


D079 — owned pre-source screening context: screening v3/worker v4 retain an immutable bounded context minted by the actual complete selection read. Source completion no longer repeats population replay; cold/original audit still verifies all dependencies before worker return. Default legacy paths remain unchanged. Four new ownership/tamper/cold-recovery tests passed81.15s;39 existing screening/worker regressions passed500.62s. Ruff/backend, canonical and whitespace checks pass. Initial instrumentation replaced a protected function and correctly triggered build-integrity refusal; the test now observes real calls via profiling without replacing code. No public requests or new empirical claims. Activation/runtime wiring remains next; Phase3 incomplete.


D080 — owned activation v3: the private screening finish operation can transition directly to activation using its authenticated bounded state. It retains full original frame identity, the explicit comparison policy, report hashes, exact roles and actual read/save clocks. Cold/original activation recovery still verifies the full frame/selection/screening chain. Legacy activation remains unchanged; existing origin workers explicitly refuse v3 until versioned origin identity handling is implemented.64 affected tests passed839.55s: owned_activation, owned_screening, activation, screened_activation and origin_worker. Initial new test expected the wrong original-reader envelope; corrected to compare report.summary, with no implementation/guard change. Ruff/backend, canonical and whitespace checks pass. No public collection or Phase3 acceptance.


D081 — owned causal pilot execution: origin v3, due v2, concurrent runtime v4 and pilot worker v5 now compose authenticated screening, activation, causal origins and targets before full original-code audit. Public entry points accept no source payload, clock, transport or provenance override. Full frame identity and current event-membership missingness remain distinct; targets compare exactly against actual frozen origin identity. Legacy versions remain strict. No production or SQL change.

Validation: six new owned-pilot cases passed across development logs (a wrong test-result key was corrected without changing safeguards); 87 affected regressions passed in1334.27s (/tmp/arepo_d081_regression.log). Self-review found runtime_concurrency=None could select the internal screening-only path; public/synthetic wrappers now reject it explicitly. Eight focused invalid-input cases passed0.63s after that guard; no redundant broad rerun. Ruff/backend, canonical contract and whitespace checks pass. Review covered authenticated private context, actual provenance/clock ordering, strict target identity, bounded due capacity, cancellation drainage, immutable dependencies and original-code replay. Synthetic success is not empirical panel acceptance.

Next: freeze PHASE_03_OWNED_PILOT_PROTOCOL.md and execute D082 once under the committed implementation. Preserve all failures/missing controls/windows/related/external values. Phase3 remains incomplete; no Phase4.


D082 executed once under c881288d80dbeddfc195c6eacceeb63b78f58e20 and passed its frozen execution gates: eight observed origins/eight valid targets, six triggered roles/two observed matched controls over eight distinct markets; four unfilled controls retained. All56 requests returned200 (24 Gamma/24 book/8 taker-trade),183036 raw bytes. Origin freeze delay8.084763–29.097624s within60s; freeze-to-save1.463–17.300ms within5s; target durable availability5.477850–8.155644s after due within15s. Exact probabilities and raw numerics/clocks preserved. Full original-code audit passed; independent evidence check verified107 artifact hashes/sizes, all eight timing pairs, both matched pairs and exact counts. No code tests repeated for evidence-only changes.

Evidence: PHASE_03_OWNED_PILOT_EVIDENCE.json. Run completed2026-10-03T19:49:41.661088UTC, exit0, elapsed1003342292167ns including selection/audits; no collector remains active. D082 is a successful execution pilot, not predictive evidence or full Phase3 acceptance. PHASE_03_ACCEPTANCE_STATUS.md maps remaining pre-origin windows/history, related/external eligibility and baseline plumbing to the exact D083 next action. Do not rerun D077/D078/D082 or retrofit richer inputs into those origins. No Phase4.


D083 origin-window component tested (2026-10-04):21 new cases plus53 affected regressions
pass; exact causal history, coverage gaps, freeze-time eligibility and cold origin replay
are preserved. Phase3 remains incomplete. Next: internally owned bounded window batch/runtime
with full reservation, failed-member retention and original-runtime recovery, then a separate
frozen empirical protocol. Reuse PHASE_03_PRE_ORIGIN_WINDOW_CONTRACT.md and the acceptance
map; do not repeat D082 or begin Phase4.


D084 owned window/runtime integration accepted as software:9 new cases and49 affected
regressions pass, including original-code recovery and cancellation drainage. Next freeze
and execute PHASE_03_WINDOW_PILOT_PROTOCOL.md once; empirical window/history and remaining
family eligibility review still govern Phase3 exit. No Phase4 or production action.


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

D086 removes pre-activation full window replay through a tested bounded owned context (21 cases).
Cold/original recovery and frozen ages remain unchanged. Next: eight-member synthetic timing;
Phase3 stays incomplete. Current scope/evidence: ../PHASE_03_WINDOW_LATENCY_NEXT.md.

D086 implementation531c3c3 passes21 scoped tests, but its eight-member synthetic measurement
failed stale-role activation before any origins. Owned/cold contexts agree; handoff0.622521s
versus later cold replay29.326286833s. First-batch windows already~81s old (60s limit).
Next D087: bounded local CPU/call profile and acquisition/analysis repair per
PHASE_03_WINDOW_LATENCY_NEXT.md. Preserve failed runs and original freshness; Phase3 incomplete.

D087 measured compilation overhead (~75% of two profiled reads); bounded immutable expected-code
cache retains all per-call build checks.76 targeted tests pass; next fresh synthetic8-member
measurement. Phase3 remains incomplete; see ../PHASE_03_WINDOW_LATENCY_NEXT.md.

D088 complete frame expired before its1h selection gate at the next assistant continuation.
D089 single-process frame/selection/pilot protocol removes that orchestration gap while
preserving existing causal/measurement gates; see ../PHASE_03_FRESH_WINDOW_PILOT_PROTOCOL.md.

D089 final: original audit passes, but only5/8 observed origins and fresh histories;5/5 targets
and one matched control pair. Three HTTP200 books are genuinely one-sided despite active,
nonclosed Gamma flags. All8denominators and exact4/109stratum weights retained. Phase3 remains
incomplete; see PHASE_03_FRESH_WINDOW_PILOT_EVIDENCE.json, review and PHASE_03_ONE_SIDED_NEXT.md.
Do not rerun or filter the failed sample. No Phase4 in this conversation.

D090 software gate passed (34 socket cases, then51 analysis/endpoint cases after the null-comparison fix). Next execute the fixed one-sided diagnostic protocol once; Phase3 remains incomplete.


D090 diagnostic is terminal: two closed/book404, one active one-sided receipt, no two-sided
recovery. D091 preserves this as explicit retrospective classification with zero coverage.
D092 opt-in owned observation integration passes24 affected tests172.73s, including original
runtime audit and no invented history after later two-sided arrivals. Phase3 remains incomplete.
Current next action: PHASE_03_ONE_SIDED_NEXT.md current-state section; family-eligibility review
then a justified finite prospective design. No D089/D090 rerun or Phase4 in this conversation.


D094 is terminal: original audit and new observer-accounting gate pass, but5/8observed origins/
fresh histories fail the unchanged6/8gates. Five valid targets and one observed matched pair;
all8members retained. Complete source/rule/clock evidence: PHASE_03_OBSERVATION_PILOT_EVIDENCE.json.
Current full-run reserve13.31GB exceeds9.51GB free; no deletion or redraw. Phase3 remains
incomplete. Resume only per the live checkpoint's capacity/temporal-eligibility next action;
do not rerun D094 or start Phase4. Prior pending-execution statements are historical.


D095 capacity restored; safe prompt cleanup audited without evidence deletion. D096 explicit
future-or-unknown stated-end deep population tested (101+1cases), full inventory/defaults
preserved. See PHASE_03_TEMPORAL_POPULATION.md and current checkpoint. Phase3 incomplete;
next one separately frozen finite measurement, no alteration of old failed gates or Phase4.

## Current status — D097 / D098, October8

D097 passes6/8origin/history and6/6target gates plus original/temporal audit, but fails
matched controls (6triggered,0negative,2unavailable). Phase3 remains incomplete. Full evidence
and411artifact checks: PHASE_03_TEMPORAL_PILOT_EVIDENCE.json; gate map: PHASE_03_ACCEPTANCE_STATUS.md.
Safe cleanup still leaves10.34GB versus13.31GBrequired. Exact next action and future control
pool review: PHASE_03_CONTROL_AVAILABILITY_NEXT.md and live checkpoint. No redraw or Phase4.

Current capacity update D099: storage blocker cleared with exact-byte transparent filesystem
compression; original-reader equivalence passed. See PHASE_03_STORAGE_COMPRESSION_EVIDENCE.json
and live checkpoint. D097 control failure remains; no new pilot or Phase4 started.

## D101 terminal / D102 verification profile — October9

D101 failed before selection: the complete276795-row frame was captured under884adb6,
but original-code verification exceeded300s. No origins/targets or control-design result.
Failure, raw evidence and original clocks preserved; no retry, relaxed deadline or redraw.
PHASE_03_CONTROL_POOL_PILOT_EVIDENCE.json records14 verified artifact hashes/sizes.

D102 read-only32-page ordinal-spread profile localises substantial cost in canonical
serialisation/page-fact re-derivation (7.393s total with profiler overhead). It is not a
full-verification benchmark or repaired pilot. Next evaluate exact-byte-preserving
serialisation improvements with hostile-type/equivalence and affected parser/recovery
tests before any source change is accepted. Old records must still use pinned code.
PHASE_03_FRAME_VERIFICATION_PROFILE.json contains page hashes, timings and script.

Phase3 remains incomplete; D097 controls still fail. No source changed, accepted tests
not repeated, no production or Phase4 action. Current capacity9.535GB<13.309GBrequired;
no collection until full reservation restored. Follow live checkpoint for next action.

Current D104–D106: strict-input row hashing passes97 targeted tests and full offline
equivalence (226.301→210.875s; no original-reader deadline claim). D105 preserves all
bytes with verified lossless compression, restoring full reservation. D106 freezes one
integration with unchanged D101 design/gates; see PHASE_03_VERIFIED_HASH_PILOT_PROTOCOL.md
and live checkpoint. Phase3 remains incomplete; no Phase4.

Current D108: D106 failed642.42s frame interval (600s gate), despite successful original
verification. Measured strict capture optimisations pass209 tests and32-page exact-byte
comparison; they do not establish full-run compliance. See live checkpoint for capacity
recovery and next integration decision. Phase3 remains incomplete; no Phase4.
