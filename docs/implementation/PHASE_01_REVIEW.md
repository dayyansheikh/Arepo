# Phase 1 review record

Phase remains **in progress**. This record covers the first tested schema milestone,
not the complete phase or any validated research finding.

## Schema milestone, 2026-09-20

Added isolated `astrolabe.feature_store` models (21 entities), a pinned column contract,
lossless decimal/unsigned-integer/UTC types, and a separate local migration CLI/ledger.
The application, v1 metadata, deployment files, public API and scheduler do not import it.
Migration URLs must explicitly identify disposable SQLite files or a nondefault-port
loopback PostgreSQL test database. A loopback proxy to production is not authorised.

Checks performed:

- 26 exact-type tests passed, covering mantissas, trailing zeros, negative zero,
  very small decimals, uint256, UTC normalization and invalid inputs.
- 14 SQLite schema/migration tests passed, including catalogue parity, read-only
  schema check, idempotent upgrade, injected-failure DDL rollback, preservation,
  mutation guards, drift refusal and v1 metadata isolation.
- Real PostgreSQL 17.11 integration passed: temporary authenticated loopback cluster,
  migration rollback/idempotency, RLS/grant restrictions, exact values, v1 float-bit
  and JSON preservation, and UPDATE/DELETE/TRUNCATE rejection. Cluster stopped.
- Existing 105 targeted backend regression tests passed (same set as Phase 0).
- New-file Ruff checks and the canonical research/contract checker passed.

Reproduce the new tests from the repository root with explicit settings:

```sh
AREPO_FS2_POSTGRES_BIN=/usr/local/opt/postgresql@17/bin \
DATABASE_URL='sqlite+aiosqlite:///:memory:' AUTO_MIGRATE=false \
ALERT_EMAIL_ENABLED=false DIGEST_EMAIL_ENABLED=false \
backend/.venv/bin/python -m pytest \
backend/tests/unit/test_feature_store_types.py \
backend/tests/unit/test_feature_store_migrations.py \
backend/tests/integration/test_feature_store_postgres.py -q
```

The PostgreSQL test skips unless a local binary directory is explicitly supplied;
a skipped test does not satisfy phase acceptance. Initial fixture failures (macOS
Unix socket path length and a JSON colon parsed as an SQL bind) were corrected by
disabling unused Unix sockets and binding JSON properly. A parity-test filter was
corrected to recognise the catalogue's `derived_as_of_view` field.

Self-review: scope is additive and disconnected; no production entry point changed.
Do not mistake this milestone for a usable collector store: transactional writer,
semantic enums/ranges/causality, full drift checks, manifest closure, concurrency and
natural-key enforcement still need implementation and testing. Database owners can
always defeat guards; production privilege policy is a separate rollout decision.

## Writer and preservation milestone, 2026-09-20

The previously pending writer, structural admission, typed vectors, closed vocabularies,
manifest closure, revision checks, natural-key constraints, installed-schema fingerprint
and local preservation codec now exist. Latest targeted suite: **98 passed**, including
the actual PostgreSQL writer/concurrency/access-drift path. Review remains in progress.
No production entry point changed. Generic prospective writes fail closed until the
Phase 2 durable receipt boundary supplies real chronology; synthetic fixtures test the
structural rules without manufacturing prospective research.

An earlier full suite run passed **581 tests**, using an explicit disposable SQLite file
and the temporary PostgreSQL cluster. The initial full run found three API tests using
separate in-memory legacy engine singletons and one old backlog test using today's wall
clock against an August fixture. The API regression now uses one disposable file; the
backlog test now fixes its monitoring clock to the same declared synthetic observation
time. No application code or assertion was weakened. Later feature-store additions
require the final full regression run before acceptance.

Additional tested properties: same-key retries/concurrent writers, conflicting-batch
rollback, complete source/manifest lineage, late feature/metadata/prediction rejection,
separate label revision availability, exact raw book zeroes and level inventories,
all missingness reasons, corruption detection and fresh-store codec restore. A genuine
populated v1 scan/cohort fixture retains every table value and its schema across two v2
upgrade calls. Numerical float values are compared by their hexadecimal representation.
