# M3 code-check fix diff check (science-reviewer, read-only, 4e7253d4, 2026-10-30)

**Verdict: ACCEPT.** q0780 (J0) can be promoted now, and so can q0781 (dry run). q0782 (serial pass) can be promoted once q0781 has finished (see SHOULD a).

I checked the working tree at 72bd85f8. For all the scoped files it is identical to 4e7253d4: `git diff --stat 4e7253d4 HEAD` is empty. `pytest -q tests/test_m3_code.py` gives 61 passed, and `ruff` reports all checks passed.

**1. MUST 1 is implemented correctly.**
- In `m3_j1.py:874`, `evc` counts only rows where `mid not in unit_mids`.
- `:1043` builds `_ev_units` from the state (`unit_meta[...][3]`, the event_id at the unit's own k, stored at `:1006`).
- `:1144` adds the two together. An empty event becomes `market:<mid>` on both sides, so earlier units cannot be counted wrongly.
- **The test fails on the old code.** I ran the new test file against the 33cd591c `m3_j1.py` in a scratch copy at `/tmp/m3ov.XM7T`, outside the repo. `test_must1_event_count_of_a_later_unit_ignores_the_earlier_units_row_after_its_k` fails on variant "closed" (`:1112`), and `test_must1_open_siblings…` also fails. Both pass on the new code.
- That test uses `alter_after_k(..., same_event=True)` for the "closed" and "gone" variants (`:1099`), and also checks J0's dry output.
- The text in 3.4 and S8 matches the reviewer's wording exactly, apart from the S8 cell being written in table form.

**2. MUST 2 text is verbatim and the output matches it.**
- 10.1 contains the sentence exactly as required, with the three result labels added.
- In `report_j0`, `evaluable = full_days >= min_full_days (3)`. With fewer than 3 full days it gives `not_evaluable_extend_42` with `rule_a=True` and `rule_b=None`. Otherwise it gives `extend_42` or `keep_21`.
- The runner's last stdout line prints `full_days=` and `rule_a_result=` (`run_m3.py:588-590`).
- The ledger entry at `EXPERIMENT_LEDGER.md:5665-5671` was committed in e0a6bf33 at 17:57Z. No q078* job is in `queue/jobs`, and there is no local m3_ch274* output.

**3. Nothing scientific changed.** The only SPEC change is the new `min_full_days: 3`; no threshold, date, class or cut moved.
- MUSTs 3-5, R3, R4 and R13 are text only.
- SHOULD 4 adds sidecar rows to J1 follow-up files only.
- The timing fields go to `logs/j1_runs.jsonl` only.
- The streamed rules merge is equivalent to the whole-index merge. The test compares the two, and the sha-to-class order cannot matter because `sha` is a content hash of `data` (`streams/common.py:373`).
- After the window closes, the merge returns before opening any file.

**4. q0782 cannot write to a real store.**
- The wrapper requires `--base` to be `research_lab/serial_dryrun`.
- Every child gets `--dry-run-last-days`. The M1 and M2 runners then require store names ending `_dryrun` (`run_m1.py:37,67`, `run_m2.py:38`), and the M1 dry run loads no pins (`run_m1.py:85-90`).
- The wrapper writes `--out` once only. A grep of `m1_extract.py` shows writes only under the store.

**5. q0780 and q0781 are correct to promote.** Arguments, roots and separate stores are as before.
- `--last-days 8` against 12-day snapshot retention has negligible risk.
- The "about 8 days" wording in the q0780 notes, note R16 and 10.2 is out of date. Correct it at the freeze; it is not blocking.

**6. Hashes match the note.** `code_sha()` gives `345b96c8…07d6d`. The four file hashes match the note, as does the design text's `34f17a62…a752`.

**SHOULD (not blocking J0):**
- a. q0782 has `depends_on: []`, although its notes say "only after q0750c, q0754, q0781". Add q0781 to `depends_on` or hold promotion until it is done. Also, the wrapper keeps `m3_j1` imported (about 170 MB) while each child runs, so the real total is about 600 + 170 MB against `mem_mb: 600`. Raise `mem_mb` or import lazily.
- b. The q0782 "m3_steady_state" step reruns the same window. It may process zero new captures, while next_action says "one capture each". Report its `capture_s` count instead of assuming one.
- c. `_blind_matches` falls back to a byte-length comparison when the status is missing. The note discloses this, and the data is deterministic, so it is acceptable.

**NIT:** `parse_day_file` decodes each line strictly, so a partial multibyte character at the end of a file still being written raises an error and exits with code 4. The old code had the same exposure, and it is not a different answer, so J0's "no re-run" rule is unaffected.

**Not verified:**
- Host data, real capture ids (`_blind_matches` assumes they contain no dots), and peak memory and run time.
- M1 and M2 `run_pass` beyond a grep for writes.
- Whether any M3 J0 output already exists on the Oracle host.

I left the scratch copy at `/tmp/m3ov.XM7T` (outside the repo).

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m3_j1.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/serial_dryrun_m123.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0782_m3_serial_pass.json`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M3_CH274.md`
