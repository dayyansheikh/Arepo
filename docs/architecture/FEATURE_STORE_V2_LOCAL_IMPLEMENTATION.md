# Feature Store v2 local implementation

Phase 1 implementation of the [canonical contract](FEATURE_STORE_V2_CONTRACT.md).
This is a nonproduction storage foundation. It supplies no measured predictive evidence.

## Interfaces and isolation

`backend/astrolabe/feature_store/` owns separate `FeatureStoreBase` metadata, 21 `fs2_`
tables and its own migration ledger. v1 models, startup, API, scheduler and deployment
configuration do not import it. `models.py` declares the columns; `schema.py` pins the
validation contract; tests compare both with the canonical CSV, excluding the derived
`observed_to_at` view. Scalar natural keys receive SQL uniqueness. JSON-list/nullable
natural keys additionally rely on canonical SHA keys verified by the writer.

`admission.prepare(entity, payload)` validates a complete record, exact values, closed
vocabularies, field-level null reasons and natural identity; it fills only deterministic
ID/compatibility aliases. Callers retain source spelling separately. JSON integers beyond
2^53−1 use strings; binary floating-point outputs require a `float64` hexadecimal tag.
Probability sums are exact, with a 10,000-digit exponent-span validation budget. Oversized
input is rejected, never rounded into apparent validity; retain the original raw evidence.

`repository.append_batch(url, records, fixture_clock=...)` owns an atomic local transaction.
It accepts synthetic fixtures, reconstructed and legacy-unverified records, checks typed
FK/list dependencies, rejects conflicting retries, and preserves identical concurrent
retries. A supplied fixture clock is accepted only for synthetic rows. All v2 connections
enable SQLite FK/recursive-trigger enforcement. PostgreSQL guards reject UPDATE, DELETE
and TRUNCATE; new tables and ledger have RLS and revoked public/browser/service-role grants.
Database owners retain the power to bypass guards; no production grants are introduced.

## Clock boundary and prospective gate

The public generic writer **rejects prospective writes**. No parameter bypasses that gate.
Phase 2 adds the dedicated `SourceRun`/`index_source_run` path described in
[prospective source admission](V2_PROSPECTIVE_SOURCE_ADMISSION.md), restricted to verified
predeclared source journals; it accepts no caller-provided record payloads. SQL is a later
index with a separate post-commit receipt. A timestamp sampled before commit
cannot certify post-commit availability. Phase 1 writer-assigned record time identifies local
transaction admission, not a proven live research availability boundary. Do not use it as
such. Nonproduction synthetic fixtures test structural chronology; they are not a completed
live ingestion implementation. The dedicated Phase 2 path retains raw/source-specific parse
and admission acknowledgements, immutable build and policy binding, and actual first receipt.

Domain availability is taken from explicit model/manifest/mapping/label/prediction clocks;
record time is the fallback for metadata with no separate availability field. A feature's
association with its frozen origin is not itself an observed feature input. Pre-origin
computation must be independently evidenced; storing a derived record later does not prove
that computation happened earlier. Sources, transforms and actual calculations must satisfy
the frozen cutoff. A later calculation is reconstructed. Source-only admission does not open
generic origin, feature, prediction or label writes; their actual computation paths are later work.

Outcome `quote_rule.clock` currently supports `receipt`, `source_event` and
`source_published`, each matched to the exact source-envelope clock. Missing source time
is not replaced with receipt time. Labels preserve actual delay and later revision
availability. Prediction admission currently handles positive fixed horizons; event-driven
prediction timing remains closed until its target-specific protocol is implemented.
This does not prevent retaining event-driven target definitions as research candidates.

## Manifests, revisions and preservation

Manifest payload schema is `fs2-manifest-v1`: `roots` and `closure` are ordered lists of
`{entity, id}` references. `closure` must contain exactly the transitive inventory. Empty
roots require `empty_reason`; empty does not silently mean complete coverage. A nonempty
training manifest declares an aware ISO `as_of_cutoff_at`; all dependencies must have been
available by it and label dependencies must be mature.

Books include their complete numerical level inventory. Level-parent links represent
composition; other cycles are rejected. Iterative traversal visits each shared dependency
once per graph and does not hit Python recursion limits on long chains. It still loads the
declared dependency graph: this is an offline admission path, not a public API query.
Phase 3 must size bounded batches, graph inventories and collector budgets from measurements.

Corrections append subject-consistent versions with advancing knowledge time. Unknown native
source identity cannot establish a source revision by assumption. Exact catalogue fields are
structural containers; source-specific parsing and scientific formula/model definitions are
implemented in their planned later phases, not inferred from version hashes alone.

`preservation.encode_records`/`decode_records` perform exact typed JSONL roundtrips and reject
checksum, schema, key, row-count or numerical-representation changes. Verification state is
`local_codec_only`. This is not the ten-stage archive-equivalence certification and supplies
no deletion or retention authority. It has no filesystem, database or external-store effects.

## Local migration and verification

The CLI reads no application database settings. `preview` compiles schema DDL without a
connection; guard/ledger behavior is defined and tested in `migrations.py`. `check` does not
create a missing database or ledger. `upgrade` requires explicit disposable local targeting:
absolute SQLite paths under the OS temporary directory or password-protected loopback
PostgreSQL on a nondefault port, with `fs2_test_` database/filename naming. Neither guard
authorises a local proxy to production. Existing v2 schema mismatch is refused, not repaired.

The initial version is being developed only on disposable fixtures. A previous draft's
checksum mismatch does not authorise deleting it: use a fresh fixture for the next rehearsal.
No production migration has been applied. Installed-state fingerprints cover actual columns,
constraints, indexes, trigger definitions, RLS/policies and privileges. Failed creation rolls
back; successful schema/data is preserved. v1 scan/cohort fixtures are value/schema compared
before and after repeated upgrades, including exact floating-point representations.

Validation commands and results live in [Phase 1 review](../implementation/PHASE_01_REVIEW.md).
