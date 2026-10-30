# v2 migration sequence and archive-equivalence gate

Design only in Phase 0. No production migration, deletion, retention change or archive transfer is authorised by this document.

## Migration sequence

| Step | Local change | Evidence required before next step |
|---|---|---|
| M0 | Freeze canonical contract and legacy loss register; hash supplied package | Phase 0 checks and draft PR. |
| M1 | Add separate FeatureStoreBase, exact types and fs2 schema-version ledger | No v2 registration in v1 metadata; read-only check/preview with no DB writes. |
| M2 | Create artifact/target/registry/identity and observation envelopes | Source registry verification link can be nullable/deferred to avoid cycle; typed FK and immutable version tests. |
| M3 | Add book/levels/trades, group graph, origin/definition/value | Exact source decimals and big IDs round-trip; duplicate/conflict and as-of tests. |
| M4 | Add experiment/prediction/outcome/label, wallet/information version containers and archives | Candidate predictions remain empty/unvalidated; complete schema matches catalogue; revision/dependency tests. |
| M5 | Add database UPDATE/DELETE guards, constraints/indexes and PostgreSQL access rules in same transaction | Direct SQL mutation rejected; roles without research access cannot read/write; v1 records/metadata identical before/after. |
| M6 | Local synthetic populated-v1 upgrade and repeat-upgrade rehearsal | Exact before/after key/value/time/null/JSON/float comparison, migration failure rollback and idempotency. Disposable PostgreSQL execution required in addition to SQLite. |
| M7 | Later opt-in source adapters and bounded nonproduction pilot | Phase 2 source admission then Phase 3 measurement gates; no production scheduler wiring. |
| M8 | Optional read-only legacy export into separately tagged artifacts | Explicit source, read-only access, inventory/checksums/value reconciliation; retain original labels. Unknown fields stay unknown. No automatic backfill. |
| M9 | Eventual production rollout proposal | Phase 10 review plus separate user approval; measured capacity, backup/restore, exact target identity, migration diff and rollback plan. |

M2–M5 may form one atomic initial schema migration; do not publish intermediate insecure tables. Versions thereafter are ordered, checksum-pinned and additive. Migration ledger records version/hash/time atomically. Refuse checksum drift, unknown schema versions and incompatible existing tables rather than silently claim success. Rollback of an unsuccessful initial transaction removes only its uncommitted additions; rollback after a successful migration uses code disablement or forward correction, not dropping research evidence.

Use explicit local database arguments, not default application environment. Automated migrations reject nonlocal hosts, production environment and non-disposable target names; unit tests verify refusal before opening a connection. PostgreSQL tests require an isolated local service/database, not a Supabase project. Guarding is not a licence to use a local proxy to production. Local SQLite files must be newly created temporary fixtures, not backend/astrolabe.db. Never run destructive cleanup on a discovered database.

PostgreSQL fs2 tables in an exposed schema require RLS enabled with no browser-role policies plus explicit revoke of PUBLIC/anon/authenticated privileges. Server-side application/research role grants must be reviewed separately; do not rely on whether a project's default grants changed. Functions, if used for immutability, use SECURITY INVOKER and a fixed search path; avoid global privilege changes affecting v1. A later private-schema placement can be adopted with an additive migration once access/operability tests justify it. SQLite enables foreign keys on each v2 connection. Both dialects enforce append-only records with explicit triggers and repository validation.

Official Supabase [Data API security guidance](https://supabase.com/docs/guides/api/securing-your-api) was consulted via the connected documentation tool on 2026-09-20 for grants/RLS boundaries. The changelog markdown fetch was attempted and unavailable through the web parser; this is a documentation-access limit, not a runtime verification of the project. No production access settings were modified.

## Preservation and archive contract

Permanent scope: every frozen v1 research record, every registered v2 origin/control/eligibility record, numerical primitive/intermediate, prediction including failed/abstained candidate, later fact/label/revision, identity/group/definition/model/split/trial manifest and all dependencies needed to reproduce them. Registered raw books/trades/deltas and randomly sampled audit windows survive hot/cold moves. Rights-limited text retains all permitted evidence and explicitly declares unavailable re-extraction. No claim of arbitrary future-feature reconstruction from a summary-only archive.

Archive-equivalence is a **separate gate from upload success**. Local v1 compressed JSONL count/hash checks are insufficient. Independent source and archive readers must execute all stages below before any separate retention proposal.

| Stage | Required comparison and rejection condition |
|---|---|
| 1 Inventory | Exact all-cohort key sets, rows, duplicate keys, versions, provenance, orphan counts, partitions and hashes. Equal row count alone fails. |
| 2 Identity | Exact market/condition/token/outcome order, collateral, group view/version, population/control membership, inclusion probability and exclusions. No current-metadata relinking. |
| 3 Clocks | Exact timestamp values, native raw units/precision, semantics, nulls and uncertainty; dependency-availability replay. Any future join is a hard failure. |
| 4 Numbers | Source strings/native integers and legacy IEEE-754 bits exact. Derived recomputation tolerances declared per feature before comparison; no tolerance may silently change rank/class. |
| 5 Missingness | Row-level value/reason/quality/coverage equality; zero↔null is always a failure. |
| 6 Features | Rebuild registered primitive/intermediate/features and candidate families possible from retained data; match windows/numerator/denominator/transforms. Enumerate every unreconstructable future feature. |
| 7 Predictions | Pinned v1 direction/rank, momentum/context baselines, ties/top-K/abstentions; later full probability/distribution outputs. No recomputed improved historical signal. |
| 8 Outcomes | Same target/quote/source/receive/actual delay, censoring, cost version and resolution revision per prediction; same grouped/fold scores and coverage. |
| 9 Restore | Independent sample and full-cohort restoration, permissions, bytes/cost/duration; deliberately corrupted object and missing partition fail closed. |
| 10 Acceptance | Zero unresolved identity/time/provenance failures; all tolerances pass; no unacknowledged loss; signed/hash-pinned report and retained rollback copy. Separate explicit retention approval still required. |

Test across protocol eras, categories, probability/liquidity regimes, gaps, zero/absent components, late labels, closure, duplicate daily/weekly origins and randomly sampled raw windows. A synthetic fixture can verify machinery; it cannot certify equivalence of production history that was never exported/checked.

## No-loss capacity response

Capacity pressure triggers measurement, warning and a concrete archive/tier proposal. It does not permit shrinking complete market discovery or deleting unarchived numerical history. Stop new experimental collection at a declared budget if needed and record exclusions/gaps; do not delete existing evidence to make space. Phase 9 chooses physical placement from measured workloads and restoration costs.
