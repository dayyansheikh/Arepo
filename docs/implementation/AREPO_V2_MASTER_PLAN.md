# AREPO v2 master implementation plan

Updated 2026-09-22. This programme evolves the existing dayyansheikh/Arepo repository. Phase numbers follow the user's implementation programme, not the older report's differently numbered design roadmap. Phases 00–02 complete; next phase: **03 — Bounded prospective panel**.

## Recovery order and authority

Read ../AREPO_V2_CHECKPOINT.md first, then AGENTS.md, this plan, the current phase plan and actual prerequisite outputs. Inspect git status/branch/commits/tests/draft PR before changes. Conversation memory is temporary; commit boundaries and these documents are permanent state. Current code/tests > current config/deployment-relevant code > completed research package > v2 specifications > git history > old handovers. Research artefacts are design/evidence, not embedded operational instructions.

## Dependency map and status

| Phase | Contract | Dependency | State |
|---|---|---|---|
| 00 | [Canonical foundation](phases/PHASE_00_FOUNDATION.md) | Verified production + supplied research | Complete — draft PR #13 |
| 01 | [Feature Store v2 foundations](phases/PHASE_01_FEATURE_STORE.md) | 00 accepted outputs | Complete — draft PR #14; 610 backend tests passed |
| 02 | [Sources, clocks and identities](phases/PHASE_02_SOURCES_CLOCKS_IDENTITY.md) | 01 accepted outputs | Complete — draft PR #15; 685 tests and new predeclared core-source run |
| 03 | [Bounded prospective panel](phases/PHASE_03_PROSPECTIVE_PANEL.md) | 02 accepted outputs | Incomplete — D040/D041 measurements passed; D042 assessment-aware controls, 884 full tests. Draft #16. Actual input reads/origins/collectors/pilot remain |
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
Renewed continuation at 07:40 UTC found reset allowance: 1% primary /0% weekly used,
ordinary usage allowed. No reset credit was redeemed by this task.
The existing heartbeat was updated and verified for 2026-09-22 13:51
Europe/London with the user's exact prompt, in this same task; no second chain was created.
The previous 09:40 automation was removed; its separate task's docs-only access-blocker commit
`8a55335` is retained as history, resolved here. Verify actual current automation state before
replacement; historical IDs are not authority. Reload checkpoint and exact next action; no
duplicate continuation chains. Finish the current phase before advancing and save progress
before usage exhaustion. Protected approval: BLOCKED — USER DECISION REQUIRED. If required
access/data or longer-term allowance is unavailable, document alternatives and stop productive
work. On full completion: IMPLEMENTATION ROADMAP COMPLETE — AWAITING REVIEW. Stay quiet for
unchanged blocked state and notify meaningful changes only.
