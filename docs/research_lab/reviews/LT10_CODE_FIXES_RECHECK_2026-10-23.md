# LT10 code-fixes re-check (science-reviewer, read-only), 2026-10-23; filed by the orchestrator

Verdict FIXES_REQUIRED (2 required, 5 notes). Tip f36ff4dd; design sha 1da6c075 unchanged; no E026 file touched; 116 LT10 tests + 132 pin tests pass; ruff clean.
R1: Replace the registered-seed call in test_registered_seed_is_refused_outside_the_registered_run (test_..._worlds.py:260) with a monkeypatched an.REGISTERED_SEED (e.g. 777), so no test executes size_check at seed 20261397.
R2: q0665: set max_retries to 0. A deterministic crash recurs and a timeout must not be retried (queue_worker.py:269-273 would send a timeout with attempts 1 <= max_retries 1 to retry_wait, rerunning at the registered seed), so every failure goes to the orchestrator.
N1: Record in the ledger the seed and plan that produced the ~3 s / ~13 s timing runs (unknown; if any ran at 20261397, disclose it).
N2: Add to the handover steps in run_xv_quotes_poller.py / 8.2: record the host's history_backfill.py sha256 and confirm it equals 25bef961... and the file E009's process loaded.
N3: Add battery2.py to CODE_FILES, or state why the counting entry is not hashed.
N4: In the _write_origin "exists" path, record which kinds have a frozen file, and flag the status file as a reprocess.
N5: Update the stale comments at analysis.py:769 and :915 to W1, W2, W3 and W10; add a test for S1 (no write on a refusing census).
Low issue 4 (no change required): while a pair file is unreadable, its pairs are marked retired instead of not_yet_in_force; both are non-units.


## Fixes applied (orchestrator's implementer)
- R1: `backend/tests/unit/test_research_lab_live_tests10_worlds.py:255-263` (`test_registered_seed_is_refused_outside_the_registered_run`): `an.REGISTERED_SEED` is monkeypatched to 777 and both the refusal and the `registered=True` call run at 777; no test executes `size_check` at 20261397.
- R2: `docs/research_lab/queue/drafts/q0665_lt10_size_check.json` (`max_retries`): 1 -> 0. Every failure or timeout goes to the orchestrator.
- N1: ledger line appended at the end of `docs/research_lab/EXPERIMENT_LEDGER.md` (timing-run seed/plan not recorded; honest disclosure).
- N2: `backend/scripts/run_xv_quotes_poller.py:9-11` handover step 3 (record the host's `history_backfill.py` sha256, confirm it equals 25bef961... and is the file E009's process loaded).
- N3: `battery2.py` added to `CODE_FILES` (`backend/astrolabe/research_lab/live_tests10.py:75`); the design-text pin (`DESIGN_TEXT_SHA256`) hashes only LIVE_TESTS_10.md, so it is unaffected.
- N4: `live_tests10.py` `_write_origin` "exists" path: the status file now carries `reprocess=1` and `frozen_kinds`; asserted in `test_zero_overwrite_of_a_refusing_census_and_frozen_not_duplicated`.
- N5: stale comments updated at `live_tests10_analysis.py:769` and `:915` (W1, W2, W3 and W10); new test `test_refusing_census_writes_no_out_file` (S1, no `--out` write on a refusing census) in `test_research_lab_live_tests10.py`.
