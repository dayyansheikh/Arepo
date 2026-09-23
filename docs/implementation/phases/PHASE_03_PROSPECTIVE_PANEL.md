# Phase 03 — Bounded prospective panel

Status: incomplete — frame/development selection and D042–D047 controls/input-read/quote computation, targeted identity and original recovery implemented; two-read runtime measurement passed. D048 freezes panel declaration/reservation; D049 enforces source-write quotas; D050 binds fresh selection to the frozen declaration. D051 adds optional compact computation quotas. Origin/pilot work remains. Stacked from accepted Phase 2 tip `747485c`. Owner: current AREPO implementation task.

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
