# Phase 03 — Bounded prospective panel

Status: incomplete — attempt 5 cleared complete-frame gate; durable selection/origin/pilot work remains. Stacked from accepted Phase 2 tip `747485c`. Owner: current AREPO implementation task.

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

## Handoff/output

Frozen sampling/measurement protocol, bounded pilot dataset/manifests, timing/coverage/cost report and baseline-ready origins.
