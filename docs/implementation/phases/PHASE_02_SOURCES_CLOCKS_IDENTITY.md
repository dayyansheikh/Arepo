# Phase 02 — Sources, clocks and identities

Status: complete, stacked from accepted Phase 1 tip `43999b5`. Owner: current AREPO implementation task.

## Objective

Prove identity and timestamp semantics for a bounded set of public sources before admitting their observations to research.

## Why this phase exists

A timestamp or identifier column alone does not establish trustworthy semantics.

## Research basis

Source catalogue documented/runtime distinction; Feature Store clock and identity contracts; report B/F/G; H57 quality pilot. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 01 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

Gamma keyset/event reconciliation, REST books and public trade clients and CLOB WebSocket already exist. Normalisation uses floats and missing timestamp fallbacks; public Data API trade meaning must be verified per protocol era. No complete timestamp envelope or event graph. This is the Phase 0 inventory; refresh this section from actual code before starting.

Reload 2026-09-20: Phase 1 is accepted (610 tests). Existing v1 clients parse JSON before
returning and import application settings; they cannot provide raw receipt chronology to
v2. Keep them unchanged. Use isolated allowlisted read-only adapters with explicit budgets.
Three diagnostic requests returned HTTP 200: Gamma markets, Data API v2 trades and CLOB
server time. These preflight checks retained hashes/field inventory only, so they are not
prospective research. Current official documentation confirms v2 snake_case/cursor envelopes;
the v1 trade client is not silently upgraded.

Implementation refinement: first build an exclusive append-only local capture directory.
Persist raw bytes plus receipt metadata, fsync both and their directory, then record the
post-durability acknowledgement; parse only afterward. Persist parsed output before sampling
its availability acknowledgement. Retain separate receipt, parse and recovery clocks. A
crash leaves partial artefacts intact and unadmitted; recovery never recreates an old parse
time. This establishes availability of the referenced raw/parsed artefacts, not the later
Feature Store index transaction. The generic writer remains closed until the separately
tested bridge verifies these artefacts and source contracts. Test this boundary before live
capture; subsequent probes remain finite, opt-in and disconnected from all schedulers.

## In scope

Second milestone: diagnostic source/identity imports and bounded live stream verification
are implemented; 674 backend tests pass. See ../PHASE_02_SOURCE_ADMISSION.md and review.
The final source-only admission path, loaded-code binding and journal-versus-index clocks
are accepted at implementation 54be417: 685 tests passed, and a new three-source predeclared
runtime run passed. See the final review and admission matrix; Phase 2 exit gate passed.

Prove identity and timestamp semantics for a bounded set of public sources before admitting their observations to research. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Reload prerequisite outputs and inspect actual store invariants. Branch codex/arepo-v2-phase-2-sources-clocks-identity from tested Phase 1 tip.
2. Pin source registry definitions for Gamma identity/rules, public CLOB books, public trades and one feasible official/reference source. Record allowed use, endpoint/protocol/schema, native units, timestamp/side meaning and documented-only status.
3. Wrap raw clients with receipt-before-parse envelope capture, session monotonic ordinal, parser/ingestion completion, request/page lineage, rights-aware raw payload and explicit error states. Preserve v1 normalisers for v1 behaviour.
   First establish a durable raw receipt/acknowledgement boundary and crash/retry tests. Phase 1's
   generic writer deliberately rejects prospective records: pre-commit transaction time is not
   evidence of durable model availability. Refine the canonical contract if an explicit receipt
   artifact/link is needed, preserve the acknowledgement evidence, and open live admission only
   through the validated source path. Do not add a Boolean bypass to the generic writer.
4. Implement exact identity mapping: Gamma market/event, condition/question/chain/collateral, token/outcome order and metadata/rules revisions; unresolved links remain excluded from dependent research.
5. Implement two versioned group views and as-of selection; corrected current metadata cannot become old as-known evidence. Graph connected-component split helpers must report unresolved dependence.
6. Build bounded fixture replay and opt-in public read-only source probe (finite requests/time/bytes, no scans/schedules). Verify current official docs before adapters; no authenticated order/wallet credential use or access bypass.
7. Exercise stream full snapshots/deltas, gaps/reconnects and timestamp uncertainty. Do not call a sequence complete if source never supplied enough information to prove it.
8. Produce runtime coverage/clock/rights report: observed, blocked, undocumented and deferred by field. If live access fails, retain replay coverage as synthetic and keep runtime acceptance unmet.
9. Run source and identity tests plus v1 client/normalisation regression. Freeze admitted source versions, commit, self-review and draft PR; hand off a measured admissibility matrix.

## Likely modules/files

New feature_store source/envelope/identity/group modules; clients/{gamma,clob_rest,clob_ws,data_api}.py only through isolated adapters; ingest/normalize.py preserved for v1; new fixture/source tests.

## Data model, API and migration implications

Additive version records in v2 store; no rewrites of legacy identities/clocks. No browser-driven probes/scans.

## Tests required

Native timestamp missing/malformed/unit ambiguity; future timestamps and clock regression; first-receipt immutability; latency/dependency ordering; page duplicates/truncation; reconnect/delta gaps; reordered outcomes and label changes; chain/collateral unknown; as-known vs reconstructed groups; current metadata leakage; runtime status changes/versioning; regression on existing clients.

## Acceptance criteria

At least the admitted core identity/book/trade sources have observed runtime field/clock evidence, or the phase is explicitly blocked; missing sources remain unadmitted. As-of identity/clock tests pass and limitations have a measured report.

## Exit checklist

- [x] Prerequisites reloaded and plan refined against real outputs.
- [x] All scoped tasks and acceptance criteria satisfied; limitations explicit.
- [x] Required tests passed with exact command/target/result recorded.
- [x] Diff self-reviewed for causal leakage, data loss, unrelated changes and protected boundaries.
- [x] Documentation/decision log/master status current.
- [x] Coherent safe work committed; branch and draft PR/dependency recorded.
- [x] Checkpoint updated with safe commit, files, tests, blockers and exact next action.

## Protected boundaries

Never fabricate prospective observations, tune on final confirmation, or treat repeated rows as independent events. Preserve complete discovery separately from public limits and sampled deep collection. Archive equivalence does not authorise deletion. A protected action requires the user's explicit decision; record BLOCKED — USER DECISION REQUIRED with the concrete action. Missing access/data is a real blocker; synthetic fixtures are not a substitute for empirical acceptance.

## Handoff/output

Admitted source/rights/clock matrix, evidence-linked as-of identities/groups and source adapters for the panel.
