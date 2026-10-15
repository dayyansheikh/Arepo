# Phase 1 review record

Phase 1 is **complete as a nonproduction foundation**. The chronological milestones below
retain their original results; final acceptance supersedes their pending-work statements.
This implementation supplies no validated research finding.

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

## Final acceptance, 2026-09-20

Full backend regression: **610 passed, zero skipped**, 38.31 seconds; one existing
Starlette/httpx deprecation warning. Actual PostgreSQL 17.11 tests ran and their disposable
cluster stopped. Reproduction from repository root:

```sh
AREPO_TEST_DIR=$(mktemp -d "${TMPDIR%/}/arepo_v2_final.XXXXXX")
DATABASE_URL="sqlite+aiosqlite:///$AREPO_TEST_DIR/regression.sqlite" \
AUTO_MIGRATE=true ALERT_EMAIL_ENABLED=false DIGEST_EMAIL_ENABLED=false \
AREPO_FS2_POSTGRES_BIN=/usr/local/opt/postgresql@17/bin \
backend/.venv/bin/python -m pytest backend/tests -q --tb=short
backend/.venv/bin/ruff check backend/astrolabe backend/tests backend/scripts
backend/.venv/bin/python backend/scripts/check_v2_contract.py
git diff --check
```

Ruff, the canonical checker (13 artefacts, 452 fields/21 entities, 140 mappings, 60 cards,
11 phase plans), and authored-file whitespace checks passed. Frontend code is unchanged.
GitHub's combined status reported a Vercel success, not backend CI evidence; local backend
execution above is the acceptance evidence. No deployment was requested by this programme.

Self-review covered correctness, causal leakage, security/access, preservation, scalability
and unrelated changes. Final fixes replace recursive manifest expansion with iterative
deduplicated traversal (deep-chain/shared-diamond regressions), bind outcome clock claims to
raw envelope fields, require exact label-delay semantics and preserve cluster cleanup on
startup failure. Tests cover nonempty training cutoffs and missing legacy receipt reasons.
No unresolved Phase 1 acceptance blocker remains. Production configuration, workflows,
v1 storage, API and scheduler are unchanged; user orchestration residue is not committed.

Phase 2 must implement the durable receipt/acknowledgement boundary before prospective
admission can open. Event-driven prediction timing remains closed pending its own protocol;
fixed horizons are implemented. The codec is only local preservation evidence: full archive
equivalence, source rights, collection and scientific validation remain later scoped work.
Draft PR #14 targets Phase 0 branch; neither #13 nor #14 is merged.
