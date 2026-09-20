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
- D014: keep public prospective writes closed in Phase 1. A timestamp taken before a transaction commits is not proof of durable model availability. Phase 2 must establish a durable receipt/clock boundary before opening a prospective ingestion path; no caller-supplied flag may waive it. Structural chronology is exercised with explicit synthetic fixtures now.
- D015: manifests use schema `fs2-manifest-v1`, entity-qualified roots and exact transitive closure. Book levels are constituents of a book and must be included in preservation closure; their parent FK is composition, not a scientific revision cycle. Nonempty training manifests declare an as-of cutoff and admit only mature labels available by that cutoff.
- D016: schema installation fingerprints actual columns, constraints, indexes, trigger definitions, RLS/policies and grants, including the migration ledger. A mismatch causes refusal, never an automatic repair. Database owners can defeat these controls; production privilege review remains separate.
- D017: scalar natural keys receive SQL unique constraints; nullable/JSON-list key semantics additionally require the validated deterministic non-null SHA primary key. The isolated writer checks payload identity and retries concurrent identical submissions without changing stored clocks.
- D018: local preservation codec roundtrips exact decimal tuples, timestamps, raw strings, nulls, units and keys; its verification state is `local_codec_only`. It is not the complete archive-equivalence gate and authorises no deletion or retention change.
- D019: JSON integers outside JavaScript's exact integer range require string encodings. Exact probability-sum validation retains small components rather than rounding them away; exponent spans exceeding 10,000 digits are rejected for validation budget, with raw evidence retained separately. This does not reduce the precision of accepted decimal storage.
- D020: use a disposable file for full v1 API regressions because legacy startup and route engines have separate singleton in-memory databases. Pin the old forward-backlog test to its declared synthetic time, not today's date. No production logic changes.
- D021: user's revised continuation interval is 310 minutes, with requested initial 17:30 Europe/London start on 2026-09-20. Maintain the existing automation ID. Saved configuration later showed only the interval; do not infer a successful punctual run from configuration alone.
- D022: iterative graph discovery and cycle checking replace recursive path expansion. Shared descendants are visited once per graph, book-level composition is explicit, and 1,500-node chains/diamond graphs have regression coverage. Phase 3 still has to measure and bound total graph/batch size.
- D023: outcome clock admission explicitly selects receipt/source-event/source-published time from the pinned target and source envelope. Unknown clocks are rejected for observed outcomes, not substituted. Event-driven prediction admission stays closed pending the relevant target protocol; Phase 1 supports fixed positive horizons.
