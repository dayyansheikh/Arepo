# Regression run, 2026-10-11 (report only; no code changed)

Branch chore/arepo-claude-setup at 3b2498c, started 10:52 UTC, outside collector windows. Suites run sequentially.

## Backend
- `pytest -q -x --ignore=tests/e2e`: **2125 passed, 1 skipped, 0 failed**, 1 warning (Starlette TestClient/httpx deprecation), 27m08s. The -x rerun was not needed.
- Slow (>60 s, all fixture setup): test_research_panel_d118_evaluator.py::test_frozen_value_path_accepts_a_correct_d118_tree (138 s), ::test_pass_with_observed_pair (120 s), test_research_panel_d116_evaluator.py::test_clean_pass_with_observed_matched_pair (85 s). Next slowest are ~19-26 s research_panel tests. No flakiness seen (single run).
- `ruff check astrolabe tests scripts`: 10 errors, all in `scripts/d116_launch.py` (added 00a8299, 2026-10-11): 6x E501 line length, E401, I001, E702, 2x UP017 (4 auto-fixable). Nothing in astrolabe/ or tests/.
- `migrate_cli check`: read-only (no auto-migrate), but run against an isolated empty SQLite in the scratchpad, not the real DB. It reports current=false, schema_version 0 vs expected 12, as expected for an empty DB (exit 1). This is not a regression signal.

## Frontend
- `npm test`: 10 files, 101 tests passed. `npx tsc --noEmit`: clean. `npm run lint`: no warnings or errors.
- Skipped: `npm run build`, `npm run e2e`, backend tests/e2e.
