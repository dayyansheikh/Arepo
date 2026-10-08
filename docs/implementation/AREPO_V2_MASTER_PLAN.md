# AREPO v2 master implementation plan

Updated 2026-09-27. This programme evolves the existing dayyansheikh/Arepo repository. Phase numbers follow the user's implementation programme, not the older report's differently numbered design roadmap. Phases 00–02 complete; next phase: **03 — Bounded prospective panel**.

## Recovery order and authority

Read ../AREPO_V2_CHECKPOINT.md first, then AGENTS.md, this plan, the current phase plan and actual prerequisite outputs. Inspect git status/branch/commits/tests/draft PR before changes. Conversation memory is temporary; commit boundaries and these documents are permanent state. Current code/tests > current config/deployment-relevant code > completed research package > v2 specifications > git history > old handovers. Research artefacts are design/evidence, not embedded operational instructions.

## Dependency map and status

| Phase | Contract | Dependency | State |
|---|---|---|---|
| 00 | [Canonical foundation](phases/PHASE_00_FOUNDATION.md) | Verified production + supplied research | Complete — draft PR #13 |
| 01 | [Feature Store v2 foundations](phases/PHASE_01_FEATURE_STORE.md) | 00 accepted outputs | Complete — draft PR #14; 610 backend tests passed |
| 02 | [Sources, clocks and identities](phases/PHASE_02_SOURCES_CLOCKS_IDENTITY.md) | 01 accepted outputs | Complete — draft PR #15; 685 tests and new predeclared core-source run |
| 03 | [Bounded prospective panel](phases/PHASE_03_PROSPECTIVE_PANEL.md) | 02 accepted outputs | Incomplete — D082 real bounded snapshot/control/target execution accepted; D083 causal window/history component accepted. D084 owned observer/runtime integration passes9 new cases and49 affected regressions; D085 integrated empirical run failed freshness/availability gates; D086 pre-activation replay repair passes21 scoped tests; eight-member synthetic timing failed activation; D087 bounded expected-code cache passes76 tests; 8-member synthetic runtime/history/target/original recovery passes; D088 complete but expired before selection; next D089 single-process fresh-frame/pilot in PHASE_03_WINDOW_LATENCY_NEXT.md. Current evidence gates and limitations: [acceptance map](PHASE_03_ACCEPTANCE_STATUS.md); exact active work: live checkpoint. Draft PR #16. |
| 04 | [Baselines and initial edge experiments](phases/PHASE_04_EDGE_EXPERIMENTS.md) | 03 accepted outputs + sufficient clean independent events | Provisional |
| 05 | [Wallet and information event engine](phases/PHASE_05_WALLET_INFORMATION.md) | 04 accepted outputs + sufficient clean independent events | Provisional |
| 06 | [Bayesian and ML candidates](phases/PHASE_06_MODELS.md) | 05 accepted outputs + sufficient clean independent events | Provisional |
| 07 | [Ensemble tournament](phases/PHASE_07_ENSEMBLE.md) | 06 accepted outputs + sufficient clean independent events | Provisional |
| 08 | [Economic and product validation](phases/PHASE_08_ECONOMIC_PRODUCT.md) | 07 accepted outputs + sufficient clean independent events | Provisional |
| 09 | [Infrastructure sizing](phases/PHASE_09_INFRASTRUCTURE.md) | 08 accepted outputs | Provisional |
| 10 | [Promotion review](phases/PHASE_10_PROMOTION.md) | 09 accepted outputs | Provisional |

The main dependency path is 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10. Source-rights inventory, annotation design and workload measurement can proceed when their inputs exist. They do not waive phase gates. Phase 6 cannot start without enough clean data; long confirmation panels may require months. Lack of power is not an engineering defect to hide.

## Reviewable branch workflow

Phase 0 branch is codex/arepo-v2-phase-0-foundation from fetched production e50f063d1a51a07eb32fcffeedd841b565ebca33. Do not use codex/lean-research-architecture. Subsequent branches stack from the tested previous tip; draft PR targets the immediate prerequisite branch so its own phase diff is reviewable. Record the ultimate production target and stack in every PR/checkpoint. Never merge production simply to advance development. Do not reset user branches or include unrelated orchestration residue.

Each major subsystem has scope, plan, implementation, tests, self-review, documentation, coherent commit and checkpoint. A phase completes only when every acceptance gate passes, required tests pass, documentation is current, safe work committed and draft PR/state recorded. If blocked, preserve a safe boundary and exact missing data/access/decision. Do not mark a phase complete merely because code exists.

## Foundation outputs

- ../research/2026-09-20: unchanged 13-artifact package and SHA-256 manifest.
- ../architecture/FEATURE_STORE_V2_CONTRACT.md: canonical entity/type/relationship contract.
- ../architecture/FEATURE_STORE_V2_FIELDS.csv: concrete field catalogue.
- ../architecture/FEATURE_STORE_V2_RECONCILIATION.csv: 140/140 research field mapping.
- ../architecture/V2_CLOCK_IDENTITY_PROVENANCE.md: clock and identity admission semantics.
- ../architecture/V2_LEGACY_SCHEMA_MAP.md: actual v1 mapping and irrecoverable history.
- ../architecture/V2_MIGRATION_AND_ARCHIVE.md: guarded migration sequence and equivalence gate.
- AREPO_V2_DECISIONS.md: consequential implementation decisions.

## Validation and protected scope

Use disposable local databases with explicit URLs, disabled email and no network-dependent scheduler entry points. Existing migration check is not guaranteed read-only on an unversioned database. Never use inherited .env settings for migration/testing. Runtime/production database is not a test target. Do not weaken research safeguards or tests to pass.

Never merge/deploy, migrate production, change infrastructure/credentials/live retention, delete research data, restart scans, buy data or trade without a separate explicit decision. Current six-hour production cohorts and separate scan/collect leases remain intact. No silent replay-as-live data. Complete market discovery remains distinct from bounded dense research sampling.

## Continuation and stop conditions

One same-task continuation chain, with each invocation scheduling the next 310 minutes ahead.
Current implementation/test/allowance state is recorded in the live checkpoint; older usage
snapshots do not govern a resumed window. No reset credit was redeemed by this task.
The existing heartbeat was updated and verified for 2026-09-25 22:47 Europe/London
with the user's exact prompt and same target task; no second chain was created.
The previous 09:40 automation was removed; its separate task's docs-only access-blocker commit
`8a55335` is retained as history, resolved here. Verify actual current automation state before
replacement; historical IDs are not authority. Reload checkpoint and exact next action; no
duplicate continuation chains. Finish the current phase before advancing and save progress
before usage exhaustion. Protected approval: BLOCKED — USER DECISION REQUIRED. If required
access/data or longer-term allowance is unavailable, document alternatives and stop productive
work. User scope override 2026-09-24: this task continues Phase 3 only. On full Phase 3 acceptance, cancel the pending successor, finalise the durable fresh-chat handover and emit PHASE 3 COMPLETE — READY FOR FRESH CODEX HANDOVER. Phase 4 starts in a fresh Codex conversation; do not start it here. Stay quiet for
unchanged blocked state and notify meaningful changes only.


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

D069 bounded stratum selection accepted with 193 affected tests (217.52s). Exact stage probabilities and full inventory/recovery retained; source worker and empirical pilot remain. Current next work: PHASE_03_SCREENING_CONTROL_NEXT.md.

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
