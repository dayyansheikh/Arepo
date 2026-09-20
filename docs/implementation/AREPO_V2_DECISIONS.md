# AREPO v2 implementation decisions

2026-09-20, Phase 0. These are engineering/scientific-contract decisions, not claims of validated model performance.

| ID | Decision | Basis / consequence |
|---|---|---|
| D000 | Use existing repository and fetched production e50f063 as base | Matches research audit; local production behind, not divergent. Lean branch not imported. |
| D001 | Preserve all 13 supplied research artefacts unchanged with SHA-256 manifest | Durable memory; Desktop reads stalled, original ChatGPT research-output curated copies available. Attached documents supply evidence, user's programme supplies operational authority. |
| D002 | Canonical prose + concrete field catalogue + exhaustive 140-field reconciliation | Original dictionary omits whole logical entities and uses generic types; cannot serve as DDL alone. |
| D003 | Separate FeatureStoreBase and fs2 migration ledger | v1 auto-migrates during build/startup/scheduler and check may create a ledger table. Isolation prevents accidental activation. |
| D004 | Exact decimal text on both SQL dialects; raw strings separately | SQLite Numeric affinity risks binary conversion; typed adapters/explicit analytical casts preserve precision. Derived float64 encoded explicitly, never substituted for raw source values. |
| D005 | Append-only scientific records with database and repository guards | Corrections/reorgs/late labels retain previous evidence; observed interval end derived at cutoff. |
| D006 | Split market/condition/asset/outcome and economic-event mapping | Condition != Gamma event != independent economic cause. Unknowns remain unresolved; later grouping only for conservative evaluation. |
| D007 | Add legacy_unverified provenance and retain source provenance in legacy_reference | v1 recorded clocks do not establish v2 first receipt or availability. No retrospective prospective relabelling. |
| D008 | Preservation contract precedes any retention proposal | v1 archive checks count/hash only and microstructure pruning lacks archive equivalence. No retention action authorised. |
| D009 | Phase 3 is measurement/development pilot; Phase 4 locks comparative baseline protocol | Avoid claiming a prospective confirmatory trial started before model/target/sampling decisions were locked. |
| D010 | Later phases are evidence-gated; no automatic 'complete' on code-only output | Source availability, clean independent events and confirmation outcomes cannot be replaced by fixture tests. |
| D011 | Single 305-minute same-task continuation | Active automation continue-arepo-v2-implementation, no duplicate chain; preserve checkpoint before stopping. |

Future architecture changes append here with reason, affected contracts and migration/test consequences. Do not silently alter a frozen scientific definition; create a new version and retain prior trial evidence.

## Phase 1 refinements

- D012: preserve dictionary-compatible column declarations explicitly and test them against the canonical CSV; no runtime reads from docs or v1 metadata imports.
- D013: install PostgreSQL locally only for a disposable isolated test cluster; no system service or production connection. Record actual integration evidence before phase acceptance.
