# E011 wrapper fix diff check (science-reviewer, read-only, 82925026, 2026-10-30)

**Verdict: ACCEPT.** q0790 to q0793 may be promoted now. The usual preconditions in the drafts still apply: merge into the branch the host runs, then `scripts/oracle/deploy.sh`.

1. **Scope holds.** `git diff 2917cefa 82925026` on the 7 pinned paths plus the 2 supplement files has 0 lines. The code and draft changes are all in 82925026: the wrapper, the tests, the runbook, the q0790 and q0791 notes/outputs, and the new q0793. 316c658a adds only the review file and 23 ledger lines, with 0 deleted lines in the ledger. One small deviation from the literal condition: 5e3e2723 also rewrites `docs/AREPO_V2_CHECKPOINT.md` and `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md`. These are status documents only, with no threshold, gate or verdict text, so it doesn't matter.

2. **Supplement step is correct.**
   - `supplement()` in `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_e011_analysis.py` runs the tree/7-pin check and the two `SUPPLEMENT_PINS` checks. It refuses with exit 2 if `results/e011_analysis.json` is missing. The primary file is only written after a successful run, so its existence implies success.
   - It re-checks the frozen inputs against `FREEZE_MANIFEST` and refuses if `e011_supplement.json` or `.run.json` already exists. It runs `run_surprise_supplement.py --root D/inputs`, the only argument that script's `main()` accepts. It writes the output once via tmp+rename. A failure leaves a unique `.failed-` record, and a child's own exit 75 is mapped to 1.
   - Pins checked with sha256: `f7cf470e…1a84` and `8917f623…329b8` are identical at e53dceaa, at 82925026 and in the working tree.
   - q0793 is `depends_on` q0791, `max_retries` 0, `not_before` 13:30Z, network none.

3. **Quiescence cannot lose the one-shot.**
   - A tempfail does not count as an attempt (`queue_worker.py:262`). q0790 has `max_retries` 2, which only applies to real errors. The retry wait is 30 min (`:68`). The cap is more than 48 consecutive tempfails before "failed" (`:69`, `:264`), and the count resets on any other outcome (`:276`).
   - Passes run at `31 */2` (`scripts/oracle/crontab.txt:4`) and take about 18 min. Adding the 10-minute quiet window gives roughly 28 to 40 busy minutes in every 120. So at most 1 or 2 consecutive 75s are expected, far below 48.
   - The queue worker only probes the collector lock and holds its own `worker.lock` (`:159-169`, `:356-358`), so the job cannot block itself. The wrapper's shared-lock probe does conflict with `arepo_pass.sh`'s exclusive `flock -n 9`, so a running pass is detected.
   - Quiescence runs before any write (`run_dir.mkdir` comes after it).
   - Even if the cap were somehow reached, nothing has been written and `queue_worker.py retry` restores the job (`:452`).

4. **The ledger entry matches the wrapper.**
   - Item 2: the code records `last_written_utc` and `pass_with_written_utc_ge_2026-11-11T12:31:00Z`, with no pass-time gate.
   - Item 4: the supplement step described above.
   - Item 5: `prerun_counts` reads only passes and alert lines.
   - Item 7: the slot grid with `missed_slot_utc`.
   - Item 8: no trials line is written.
   - The `pre_run_sha256` check and the library-version record are in `analyze()`.

5. **Checks pass.** `pytest -q tests/test_e011_analysis_wrapper.py`: 17 passed. Ruff: all checks passed. The tests cover quiescence, window-limited counts and missed slots, the PRE_RUN tamper check, supplement pins, refusal, write-once, and the q0793 draft shape.

**Minor issues, none blocking:**
- a. The missed-slot grid starts at the first pass inside the window (`min(pass_ts)`). Missed slots between 2026-10-13T14:00Z and that first pass would not be counted, and a schedule drift of more than 30 min would falsely mark slots as missed. This is a descriptive count only. When the result entry is written, compare it against the ledger's 6-pass gap (10-14 00:31 to 10:31Z).
- b. `supplement()` does not re-check `PRE_RUN.json` against `pre_run_sha256`. That doesn't matter for its output; it only affects auditability.
- c. The pinned supplement reads `float(p["t"])` with no fallback (`surprise_supplement.py:100`). The wrapper falls back to `written_utc`. A pass line without `t` would make q0793 fail. That failure would be recorded and descriptive only, and can't be fixed without editing the pin.

**Not verified:**
- Host HEAD and deployment state (no network access).
- Whether every line in `passes.jsonl` has `t`. I did not read any data.
- Whether `archive_rotate.py --include-active surprise_live/*` (Sundays 06:10 UTC) could alter the source files. 2026-11-11 is a Wednesday, so a run on the day is unlikely to matter, and this is outside the diff.
- No alert or outcome data was read.
