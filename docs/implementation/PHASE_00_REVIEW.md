# Phase 0 verification and self-review

2026-09-20. Base e50f063d1a51a07eb32fcffeedd841b565ebca33. Scope: repository planning/specification plus read-only structural checker; no application behaviour changed.

## Validation evidence

- `backend/.venv/bin/python backend/scripts/check_v2_contract.py`: PASS, 13 file hashes, 452 canonical fields across 21 entities, 140/140 research dictionary mappings, 60 features and experiment cards, 11 phase contracts. Reads local documents only.
- `backend/.venv/bin/ruff check backend/scripts/check_v2_contract.py`: PASS.
- Authored-file staged whitespace check: PASS using `git diff --cached --check -- . ":(exclude)docs/research/2026-09-20/**"`. Full staged check flagged source CSV CRLF and original Markdown trailing spaces. Those supplied artefacts remain byte-identical rather than being reformatted; generated CSV files use LF.
- Backend targeted suite: **105 passed**, 4.85s. Files: test_storage, test_migration, test_production_migration, test_research_timing, test_research_atomicity, test_cohort_from_scan, test_forward_batch, test_preclose, test_flow, test_scoring, test_production_scheduler.
- Command: `DATABASE_URL='sqlite+aiosqlite:///:memory:' AUTO_MIGRATE=true ALERT_EMAIL_ENABLED=false DIGEST_EMAIL_ENABLED=false backend/.venv/bin/python -m pytest backend/tests/unit/test_storage.py backend/tests/unit/test_migration.py backend/tests/unit/test_production_migration.py backend/tests/unit/test_research_timing.py backend/tests/unit/test_research_atomicity.py backend/tests/unit/test_cohort_from_scan.py backend/tests/unit/test_forward_batch.py backend/tests/unit/test_preclose.py backend/tests/unit/test_flow.py backend/tests/unit/test_scoring.py backend/tests/unit/test_production_scheduler.py -q`.
- First attempt used AUTO_MIGRATE=false: 104 passed, one expected-environment conflict in the existing test that explicitly requires startup migration. Repeated on isolated local fixtures with the intended true setting; no application/test assertions changed.
- Disposable in-memory v1 upgrade/check: PASS, schema version 12, no missing tables/columns. Existing migrator check was not run against an inherited or production database.
- Full frontend validation not run: no frontend or API implementation changed. PostgreSQL execution belongs to Phase 1; no Phase 0 schema implementation is claimed.

## Self-review findings and resolutions

1. Original dictionary omitted registry/definitions/outcome/experiment/archive entities: added concrete fields, keys and two supporting manifest/target entities; all original fields trace to one destination.
2. Original required first receipt conflicts with honest legacy import: prospective validation still requires it; explicit legacy imports allow unknown_legacy rather than invented time.
3. Observed-to interval updates would mutate evidence: define as-of view using immutable supersession records instead.
4. SQLite Numeric cannot guarantee lossless source decimals: exact decimal text chosen for authoritative storage; typed analytical projections deferred.
5. Existing auto-migrations risk activating v2 implicitly: separate ORM base/ledger and guarded explicit local migrations specified.
6. Existing scan origin defaults to scan start before enrichment completion; forward now precedes batch receipt: record limitations and require v2 per-dependency admission. Do not repair v1 rows.
7. Existing archival checksum/count is insufficient and does not cover microstructure pruning: full ten-stage independent equivalence plus separate retention approval required.
8. Phase 3 panel preceding Phase 4 baseline lock could be misrepresented as confirmation: pilot explicitly development/measurement; fresh confirmation starts after lock.
9. Duplicate compatibility IDs/source/target versions could drift: require equality with canonical referenced versions.
10. Later phase completion cannot be code-only: runtime source access, clean independent events and prospective confirmation remain explicit blockers when missing.

## User-required output inventory

| Requirement | Evidence |
|---|---|
| 1–2 Repository/base/branch verified | ../architecture/V2_LEGACY_SCHEMA_MAP.md; git ancestry and new Phase 0 branch |
| 3 Research reconciled | ../research/2026-09-20/ plus integrity manifest and canonical reconciliation CSV |
| 4–7 Master and phase plans | AREPO_V2_MASTER_PLAN.md and phases/PHASE_00 through PHASE_10; 0–3 detailed, later provisional |
| 8 Canonical implementation specification | ../architecture/FEATURE_STORE_V2_CONTRACT.md and field catalogue |
| 9 Legacy mapping | ../architecture/V2_LEGACY_SCHEMA_MAP.md |
| 10–12 Clocks/identity/missingness/version/provenance | ../architecture/V2_CLOCK_IDENTITY_PROVENANCE.md plus catalogue |
| 13–14 Migration sequence/archive equivalence | ../architecture/V2_MIGRATION_AND_ARCHIVE.md; designed only |
| 15 Agent instructions | ../../AGENTS.md |
| 16 Live recovery checkpoint | ../AREPO_V2_CHECKPOINT.md |
| 17 Checks | Validation above |
| 18–20 Commit/self-review/draft PR | This self-review; exact commit/PR recorded in checkpoint after creation; no merge |

## Explicit limitations

The supplied curated package excludes raw evidence dumps, endpoint/ABI CSV subcatalogues and literature snapshots. Those are not invented or required for the Phase 0 design reconciliation. The Desktop path stalled; matching named artefacts were recovered from the original local research-output directory. Hashes certify those originals, not an unread Desktop duplicate. Runtime source rights/availability, current database sizes and live RLS exposure were not re-audited. No predictive edge or model winner is claimed.
