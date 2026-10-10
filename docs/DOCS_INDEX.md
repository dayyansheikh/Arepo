# AREPO documentation index

Load only what the task needs. Never load whole directories, `*EVIDENCE*.json`, `PHASE_03_REVIEW.md` (1.7k lines)
or `docs/research/2026-09-20/EDGE_HYPOTHESIS_LIBRARY.md` (3k lines) wholesale; grep or read ranges.

## Source-of-truth order
1. Current code, tests and verified evidence.
2. Current explicit user decisions.
3. Canonical contracts and active phase protocols.
4. Live checkpoint and decisions log.
5. Historical handovers, superseded plans, old prompts (`docs/history/`, `docs/archive/`).

## 1. Live state (read first)
- [AREPO_V2_CHECKPOINT.md](AREPO_V2_CHECKPOINT.md): live state and exact next action (about 30 lines).
- [implementation/AREPO_V2_DECISIONS.md](implementation/AREPO_V2_DECISIONS.md): decision log D001-D114 plus the Oct 10 correction at the end.
- [implementation/AREPO_V2_MASTER_PLAN.md](implementation/AREPO_V2_MASTER_PLAN.md): phases 00-10, dependency path.
- `../AGENTS.md` (rules), `../CLAUDE.md` (session routine).

## 2. Architecture and Feature Store v2 contracts
- [architecture/FEATURE_STORE_V2_CONTRACT.md](architecture/FEATURE_STORE_V2_CONTRACT.md) (+ `_FIELDS.csv`, `_RECONCILIATION.csv`, `_LOCAL_IMPLEMENTATION.md`)
- [architecture/V2_CLOCK_IDENTITY_PROVENANCE.md](architecture/V2_CLOCK_IDENTITY_PROVENANCE.md), [V2_PROSPECTIVE_SOURCE_ADMISSION.md](architecture/V2_PROSPECTIVE_SOURCE_ADMISSION.md), [V2_MIGRATION_AND_ARCHIVE.md](architecture/V2_MIGRATION_AND_ARCHIVE.md), [V2_LEGACY_SCHEMA_MAP.md](architecture/V2_LEGACY_SCHEMA_MAP.md)
- Contract check: `cd backend && source .venv/bin/activate && python scripts/check_v2_contract.py`

## 3. Research plans and protocol (canonical science)
- Research package `research/2026-09-20/`: start at `READ_ME_FIRST.md`; baselines B0-B4 in `MODEL_COMPARISON_AND_VALIDATION.md` section 4; feature/experiment registers are CSVs (grep them).
- Architecture/infra/product strategy package `research/2026-10-10-architecture/` (independent session, 2026-10-10): start at `AREPO_FUTURE_ARCHITECTURE_2026-10-10.md`; specialist reports alongside. Strategic input, not implemented decisions; staged adoption is recorded in the decisions log.
- Research-lab experiment ledger (Track A): [research_lab/EXPERIMENT_LEDGER.md](research_lab/EXPERIMENT_LEDGER.md).
- Phase plans: [implementation/phases/](implementation/phases/) (`PHASE_03_PROSPECTIVE_PANEL.md` current; `PHASE_04_EDGE_EXPERIMENTS.md` NOT started, needs refresh).

## 4. Phase 3 protocols and data contract
- Exit/data boundary: [PHASE_03_EXIT_SCOPE.md](implementation/PHASE_03_EXIT_SCOPE.md), [PHASE_03_DATA_BOUNDARY.md](implementation/PHASE_03_DATA_BOUNDARY.md), [PHASE_03_ACCEPTANCE_STATUS.md](implementation/PHASE_03_ACCEPTANCE_STATUS.md) (PROVISIONAL banner).
- Contracts: `PHASE_03_FRAME_CONTRACT.md`, `PHASE_03_PANEL_JOURNAL_CONTRACT.md`, `PHASE_03_PANEL_ORIGIN_CONTRACT.md` in `implementation/`.
- Latest live pilot protocol (D114, also holds the inline pilot script): `PHASE_03_GZIP_PILOT_PROTOCOL.md`.
- Retention: [PHASE_03_BOUNDED_RETENTION.md](implementation/PHASE_03_BOUNDED_RETENTION.md).

## 5. Immutable evidence (never edit; grep, do not bulk-read)
- `implementation/PHASE_03_*EVIDENCE*.json`; canonical pilots: `OWNED_PILOT` (D082), `OBSERVATION_PILOT` (D094), `TEMPORAL_PILOT` (D097), `GZIP_PILOT` (D114).
- `PHASE_03_EXIT_EVIDENCE_AUDIT.json`, `PHASE_03_SCREENING_BUDGET_VALIDATION.json`, `PHASE_03_STORAGE_RETIREMENT_SUMMARY.json`.
- Raw data: `data-dumps/` (git-ignored, local only; protected runs listed in the checkpoint).

## 6. Code and tests
- v2 panel runtime: `backend/astrolabe/research_panel/` (screening.py, window_computation.py, sampling.py, selection.py, origin_*). Feature store: `backend/astrolabe/feature_store/`.
- Tests: `backend/tests/unit/test_research_panel_*.py`, `test_feature_store_*.py`. v1 product code: rest of `backend/astrolabe/`, `frontend/`.

## 7. History and archive (do not load by default)
- [history/AREPO_V2_CHECKPOINT_HISTORY.md](history/AREPO_V2_CHECKPOINT_HISTORY.md): full pre-rewrite checkpoint (1,038 lines).
- Original user handover (2026-10-10): kept PRIVATE, not in Git (local archive only). [AREPO_V2_PHASE_3_HANDOVER.md](AREPO_V2_PHASE_3_HANDOVER.md): Codex closeout (PROVISIONAL).
- v1 product docs: the other `docs/*.md` files; `archive/` for v1 root status files and old prompts.
