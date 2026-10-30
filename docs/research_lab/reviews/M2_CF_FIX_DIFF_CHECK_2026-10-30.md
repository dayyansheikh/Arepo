# M2 code-freeze fix diff check, 2026-10-30

**Verdict: ACCEPT.** MUSTs 1-4 are fixed. The three code-fix tests fail on the old code, and the MUST 3 test fails on a mutant. The SHOULDs move no estimand, class, threshold, date or valid-run number. The design text is unchanged. One operational SHOULD is listed below; it does not block q0754.

## Integrity
- The old code at `3b87d3e2` gives `code_sha` `f09e23a8…c705`, recomputed with the `m2_spec.code_sha()` method from `git archive`. The `m2_j1.py` hash `0765fe20…` matches code note b.
- The new `code_sha()` is `03984d2c278ba5872378e3f70aa78829dd05f4d3ebb503b1e18d142c4f95d6e2`. All six per-file sha256s match code note c. `m2_j2.py` and `m2_spec.py` are unchanged.
- `MEASUREMENT_M2_CH264.md` sha256 is `bb7c27e0…7cbb0`, equal to `SPEC["design_sha256"]`.
- None of the eight `PINNED_MODULES` changed between `3b87d3e2` and HEAD.
- In `3b87d3e2..4680e7e5`, only `4680e7e5` touches the M2 code, tests, design or q0754/q0755 drafts. The other files in the range diff are CH276 and signal_engine work from merges, which are outside `CODE_FILES` and the pins. The M2 code at HEAD (`3227e8d8`) is identical to `4680e7e5`.
- `pytest -q tests/test_m2*.py`: 97 passed. `ruff`: all checks passed.

## MUSTs
1. **Post-window rule index: fixed.** `run_j1` now passes `rules=None` and loads `RulesIndex` only if `not mp.ledger_closed()` (`m2_j1.py:1186-1189`). The early return in `merge_rule_ledger` also frees an index it was handed (`:641-643`). After the window, `self.rules` is read only through `_unit` (`:931`, which runs only inside the window) and `report_j0` (`:1107`, dry run only). `j1_runs.jsonl` has no `rules.info`, so the outputs are unchanged. On the old code the test fails with `AttributeError: ledger_closed`.
2. **J3 retry gap: fixed.** The gap is now measured per request from the start of its own last attempt (`m2_readout.py:67-78`). On the old code the test fails: `c` was attempted at `[1400, 3600, 7200]`. The new code adds at most one round's duration per retry, which is well inside q0755d's `timeout_s` of 28800.
3. **Item 5 test: done.** The test passes on the old code, which is expected because item 5 was already implemented. I mutated `run_m2.py:102` so the pad was `None` and the test failed, so it guards against wrong code.
4. **Implementation reading: done.** It is recorded in code note c only, with no change to the frozen text. It matches `lookup_records` and `test_v_rule_records_after_t_d_never_change_s2` (`test_m2_j1.py:205`).

## SHOULDs (no change to a valid run)
- `j2` and `j3` now refuse without `--pins` on a real store. The q0755b/c/d drafts all pass `--pins`.
- `load_units(man)` reads only files listed in the manifest. For a valid run this is the same set: `_hash_dir` lists every `units/` file at J2, and any missing or differing file already voids the run under 11.7 (`m2_analysis.py:631`).
- A pin mismatch now writes a void record and then re-raises, so the exit code is still 3. `PinMismatch.record` exists (`m2_spec.py:98-103`). As a side effect, `--out` now exists afterwards, so a rerun is refused. This fits the one-shot analysis and 11.1.
- The banned-word check skips only the top-level `uma_status_by_class` and `cross_check_engine_log` (`:703`, `:717`). The only generated string skipped is `cross_check`'s note "the pinned source governs", which contains no banned word. The new test confirms generated text still raises.
- The old code fails 6 of the 8 new or extended tests, as expected.

## Defects / follow-ups (non-blocking)
1. **(SHOULD, ops) The new dumps guard applies to every job and can stall real runs.** The default cap is 50 GiB (`2**30`, `run_m2.py:83`). The ledger (`EXPERIMENT_LEDGER.md:4693-4694`) records data-dumps at 48.6 GB, then 37.76e9 bytes after deletions on 10-30. The checkpoint (`AREPO_V2_CHECKPOINT.md:298`) says it grows about 1 GB/day. Under queue README:31-33, 48 tempfails in a row (about a day) make a job `failed`, and this affects J1 and the one-shot analysis too. Before registration, record the cap and the ops plan for data-dumps size.
2. **(SHOULD) The dry run does not exercise the real guard.** With q0754's store path, the default `--data-dumps` resolves to `data-dumps/research_lab/m2_dryruns/q0754`, not `data-dumps` (the help text says "i.e. data-dumps"). So the dry run never measures the `rglob` cost over the real tree on each pass. Adding `--data-dumps ../data-dumps` to q0754 would fix this. It is optional.
3. **(Nit)** The `--data-dumps-cap-gb` flag says GB but the code uses GiB.

## q0754 draft
The argv is correct for this code: `j1`, dry-run store `…/m2_dryruns/q0754/research_lab/m2_ch264_dryrun`, which is separate from the real `research_lab/m2_ch264` and passes `store_ok`. It also sets `--dry-run-last-days 3` and pads by default. Other settings: `mem_mb` 600, `as_cap_mb` 6000, network `none`, no `not_before` (deadline 11-21) and no hard-coded `code_sha`.

## Could not verify
- The host's current data-dumps size and file count, and so the guard's run time.
- Real peak RSS, which is what q0754 will measure.
- Whether `finished_utc` is present in the host's manifests.

May q0754 be promoted now? **yes**. Record `code_sha` = `03984d2c278ba5872378e3f70aa78829dd05f4d3ebb503b1e18d142c4f95d6e2`.
