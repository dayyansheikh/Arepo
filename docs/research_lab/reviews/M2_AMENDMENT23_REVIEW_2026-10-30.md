# M2 amendment 23 and sibling-count fix review (science-reviewer, read-only, 4ddf53d8, 2026-10-30)

**Verdict: ACCEPT_WITH_FIXES.** The amendment and the S8 / status-count fix are correct, but the two open items are real forbidden reads. Once the MUSTs are done, q0754b can be promoted after a diff-only check.

**Checks run**
- Tests: `pytest -q tests/test_m2*.py` gives 101 passed. `ruff check astrolabe/research_lab/m2_*.py` reports all checks passed.
- Hashes: `m2_spec.code_sha()` is `aa6182ba…b2270b` and the design file is `a7f30de2…3e07`. Both match the claims.
- Old-code failure: I ran the new tests against the 4680e7e5 `m2_j1.py` in a /tmp copy. 3 of the 4 `test_amendment22_*` variants fail (closed, gone, moved_reoverdue). moved_far passes on the old code too, which is expected because nothing moves.

**(1) The amendment is append-only.** In git, 689de040 is the predecessor and its design file hashes to `bb7c27e05d94…7cbb0`. `git diff 689de040 4ddf53d8` shows 12 added lines, 0 removed, all in section 23 (l.795-806). The commits are timed before registration. The changes are limited to the member-count definition and the scope of the two status counts. The "reading versus amendment" reasoning is sound and follows the M1 section 18 precedent.

**(2) The code does exactly what the amendment says.** Since 4680e7e5 the M2 code changed only in:
- `m2_j1.py`: l.516, 560-561, 615 (state field), 698 (skip earlier units' rows), 712-713 (add earlier units by their event_id at their own k), 796-797 and 851.
- `m2_spec.py`: the design pin.
- `test_m2_code.py`: the pin assertion.

Units created at the same k are added to `unit_ids` only after classification (l.795), so they are still counted from their rows. Empty event_ids are keyed `market:<id>` at l.921/952, so the state key matches the row key.

**(3) Both open items read forbidden state. MUST fix both.**

`left_before_overdue_slot`:
- At a later capture j, an earlier unit whose end_date moved to within +3h of start_j enters `watch_cand` (l.709-710).
- At j+1, if it is closed or gone, it is counted (l.859-862).
- That count goes into `local` and then into the status file's `counts` (l.810), which is not sealed.
- So it leaks exactly the competing-event-C signal from 7.3 (closed flag or missing row), against l.439, 9.2 and 11.2.

`end_date_missing`:
- An earlier unit whose end_date becomes unparseable at j > k is counted (l.842-849, `end_missing_by_day` and `end_missing_markets`).
- That is the unit's follow-up `end_date` (the same field `_write_followup` seals), so it is forbidden by 9.2 and 11.2.
- The same unit at its own k cannot be counted here, because a unit needs a parseable end_date at k.

**(4) Other fields.**
- `self.forms` (l.774-777) counts the UMA status of every row, earlier units included. In J1 it is never written to state, status or the read-out, so no fix is needed. J0, however, printed it (`status_forms`, design l.763). That is an earlier unit's post-k UMA state, which is the outcome of estimand 2 (7.3). It can no longer change anything (SHOULD 9), but it is undisclosed.
- Clean: `_cap_funnel`, `cand`, `prev["ends"]`, `prev["uma"]` and `forms_other` only cover markets not yet seen, so they never include earlier units.
- Not judged: the follow-up sha and line count in the status file (`fu_info`, l.993-1005) are a commitment hash, as previously accepted. Whether the rule ledger leaks through the state sha was outside my scope.

**MUST**
1. In `_scan`, change the `watch_cand` branch (l.709) to require `mid not in follow_mids`. In `_classify`, also skip `f"m2:{mid}" in self.unit_ids` in the `left_before` loop (l.859) and in the `end_missing` loop (l.842), including `end_missing_by_day` and `end_missing_markets`.
2. These change the class definitions at design l.148 and l.166, so the text must cover them. Append a new subsection or section after l.806; do not edit the lines already in section 23. It should:
   - put both classes into scope with the same wording as 23.2 (M2 units are left out, nothing is moved to the read-out);
   - replace the "Residual, not changed here" sentence;
   - re-pin the design sha and re-record `code_sha` in a code note.
3. Add test variants:
   - an earlier unit whose end_date moves to start_j+1h and which is then closed or gone at j+1;
   - an earlier unit whose end_date becomes unparseable after its k.

   Assert that the unit and status files are byte-identical and that `extra` is equal. Show that they fail on aa6182ba.

**SHOULD**
1. Extend the J0 disclosure (23.3) to cover `left_before_overdue_slot` 1,123, `end_date_missing` 1,587 / 20 markets, and `status_forms` (l.759, l.763): not recomputed, changes nothing.
2. Fix the numbering: the code comments (l.516, 851) and the test names say "amendment 22", while the text, code note and ledger say 23. Do it in the same code change.
3. `docs/research_lab/queue/jobs/q0754_m2_dryrun.json` is still in `jobs/` with a "PROMOTED" note. The ledger (l.5708) says it was cancelled on the host. Mark it cancelled or move it in the repo so it cannot be re-sent. I could not check the host.
4. Loading a state that has `unit_ids` but no `unit_events` fails with a bare KeyError at l.713. Make it an explicit refusal (only reachable on a non-fresh store).

**(5) q0754b.** The argv is right: a fresh store at `m2_dryruns/q0754b/research_lab/m2_ch264_dryrun`, `--dry-run-last-days 3` and `--data-dumps ../data-dumps`, with `mem_mb` 600 and `network` none. Once the MUSTs are in:
- update the code_sha / design sha in its notes;
- move it to `jobs/`.

A diff-only check is enough, as long as the diff touches only the l.709/842/859 filters, the comment renumbering, the appended text, the pin and the tests.

**Not verified:** host queue state; whether J0's seal still exists; behaviour on real data.

Files: `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M2_CH264.md`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m2_j1.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_m2_j1.py`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0754b_m2_dryrun.json`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/q0754_m2_dryrun.json`
