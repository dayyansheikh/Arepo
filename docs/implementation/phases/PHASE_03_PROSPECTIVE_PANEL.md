# Phase 03 — Bounded prospective panel

Status: planned. Owner: current AREPO implementation task.

## Objective

Build and validate a deliberately sampled prospective collector with scheduled controls and causal target collection.

## Why this phase exists

A selected signal-only dataset cannot answer incremental-information questions.

## Research basis

Model protocol sections 2–5, Feature Store preservation matrix; H02/H08/H10/H14/H15/H24/H27/H28 and selected official-source cases. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 02 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

Complete discovery analyses all eligible markets; top-20 display is separate. Scan and collect leases/deadlines are separated; production scan schedule paused, collect remains scheduled. v1 forward targets are 1h/6h/24h/7d with 900s exact tolerance; not adequate for new minute-scale tests. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

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
