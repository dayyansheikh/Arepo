# Final pre-deployment baseline

Recorded at the start of the pre-deployment repair and launch-readiness pass, on branch
`arepo-final-predeployment-launch-readiness` (safety tag
`arepo-before-final-predeployment-launch-readiness`), before the repair.

| Item | State |
| --- | --- |
| Branch / start commit | `arepo-final-predeployment-launch-readiness` from `dd55938` (edge-research at `5e2ce9f` + spec) |
| Git status at start | clean |
| Backend tests | 339 pass (baseline), ruff clean |
| Frontend tests | 21 vitest; tsc/lint clean; build 16/16 |
| Migration mechanism | `create_all` bootstrap only (no ALTER) — the root cause |
| Local database | `backend/astrolabe.db` (SQLite); schema version 0 (untracked) |
| research_entries columns | 34 present; **missing** `momentum_direction`, `orderbook_direction`, `tradeflow_direction` |
| research_cohorts / forward / revisions | present and current |
| Cohort counts | 0 research cohorts (the failed 6h freeze left NO partial row — single-commit rolled back) |
| Failed/incomplete cohort records | none persisted |
| Reproduced blocking error | `sqlite3.OperationalError: no such column: research_entries.momentum_direction` |
| `live token data unavailable` | logged per-token in `LiveSource.get_token_data`; token returns empty data, not excluded/tracked |
| Tooltip overflow | `MetricHelp` popover uses CSS absolute positioning; can overflow the viewport + cause horizontal scroll |
| Horizontal overflow | present on Signal Lab at narrow widths (popover-driven) |
| Signal Lab action row | badge + "Why this fired" + "Show/Hide detail" visually merged |
| Hosting configuration | `render.yaml` (Render web + crons); not yet a decided/decision-doc'd architecture |
| Scheduled jobs | 7 existing + 4 research crons (from `5e2ce9f`) |
| Deployment blockers | schema migration (now fixed); external accounts (Supabase/Render/Vercel) |

## Repair status after this baseline (verified this pass)

- Additive migration implemented (`astrolabe/storage/migrate.py` + `migrate_cli.py`); the real
  `astrolabe.db` migrated 0 → v2, added the 3 missing columns, preserved rows, idempotent on rerun.
- The previously-blocked `research-freeze --cadence 6h` now succeeds (universe_size 60, frozen).
- Backup taken: `backend/astrolabe.db.backup-<timestamp>` before migrating.
