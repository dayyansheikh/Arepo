# LT2 / LT3 / LT4 analysis readiness (science-reviewer, outcome-blind, read-only, 2026-10-30)

**Verdict summary (outcome-blind, from the repo only, HEAD 5439baca):**
- **E012-E014 (LT2, q0461): READY_WITH_OPS_FIXES.** It has the most exposure, because it depends on q0460 finishing.
- **E015 (LT3, q0475): READY_WITH_OPS_FIXES.**
- **E022 (LT4, q0486): READY_WITH_OPS_FIXES.**

**1. Pins (recomputed now)**
- **Spec hashes match the pinned values:** LT2 `010a7ba1…584c`, LT3 `72a174eb…2a26`, LT4 `f7fbcff1…55a9`.
- **Normalised code hashes match every spec `code_sha256` entry:** 2 files for LT2, 2 for LT3, 5 for LT4 (including `bounce_decomp.py` `2caf0edc…`). `code_check()` returns "match" for all three when imported locally.
- **No commit touches any pinned file or spec after registration.** The last commits are a4127bb9 (10-20 18:51), 2580c58a (10-21 12:36) and bf730c6f (10-22 06:59).
- **Unpinned modules imported by LT2 and LT3:** `bounce_decomp`, `battery`, `economics`, `forecast`, `panel`, `trade_sample`, `cb13_label`, `cb17_census`, `provenance`. None changed since 10-20 17:00. `battery2.py` (imported by `bounce_decomp`) did change (1d301e29, 6c5cb133, b9d7fa3a, 08d6a431), but only to add new kinds. It imports cleanly.
- **Unit tests:** 116/116 LT2-4 tests pass at HEAD.
- **Fixes from the earlier reviews all landed before registration:**
  - LT2 re-check A-C and F: a14f3efb, b756fcbc. The NaN refusal is at `live_tests2_analysis.py:73-75`.
  - LT3 pre-pin fixes 1-2: b48e1909, f9c9566c (`live_tests3_analysis.py:54-60,883-889`).
  - LT4 R2 findings 1-3: bounce_decomp pinned, midnight anchor (`live_tests4.py:817`), q0484 run after the LT3 pin.
- **Disclosure (cannot be fixed without voiding the pin):** the pinned LT2 spec still says `"status": "DRAFT (not registered…)"` and has no `k_tests`. This has no effect on behaviour, because the refusal logic keys on `_pinned`.

**2-4. Argv, timing, refusals, counting**
- **Argv:** each job runs `analyze --out ../data-dumps/research_lab/live_testsN/analysis_v1.json`. The worker's working directory is `~/arepo/backend` (`queue_worker.py:302`), so this resolves to `OUT_ROOT` (`forecast.ROOT`). The window defaults to the registered REGISTERED/END constants. The protocols only say `analyze` (`LIVE_TESTS_3.md:62`, `LIVE_TESTS_4.md:87`), so nothing conflicts.
- **Timing:** each job's `not_before` equals its `ANALYSIS_NOT_BEFORE`.
- **Refusals:** the code refuses before that date, on a spec hash mismatch (`load_spec`), and on a code mismatch (`code_check`).
- **One-shot:** the runners refuse an existing `--out` before computing (`run_live_tests2.py:90-92`, `run_live_tests4.py:113`).
- **Counting:** the `battery2` count rules for the kinds `live_tests2`, `live_tests3` and `live_tests4` all exist and use the per-test count (`battery2.py:46,51,457`).
  - LT2 counts 8 tests (4 Holm primaries plus 4 economics tests), with Holm m = 4.
  - LT3 and LT4 count the tests in `k_tests` (one each), with Holm m = 1 (`live_tests3_analysis.py:950`, `live_tests4_analysis.py:595`).
- **Consequence of `max_retries` 1:** a crash before the output is written leads to an identical-seed rerun, which is harmless. A crash after the output is written but before the trials line is appended leads to a rerun that refuses, so the job ends 'failed' and the count is missing.

**5. Dependency**
- q0461 runs only once q0460 is 'done' (`queue_worker.py:235`).
- q0460 reaches 'done' only by printing `LIVE_TESTS2_WINDOW_CLOSED`. That needs time ≥ END+30h (11-13T06:00Z) and a pass that writes nothing, after the data-dumps guard check (`run_live_tests2.py:55-59`).
- After 48 consecutive "not now" exits (code 75), q0460 is marked 'failed'. q0461 then never runs. Blocking is the right behaviour, because it guarantees the outcome lines are complete before the analysis.
- If q0460 is 'failed', the operator should run `queue_worker.py retry q0460_lt2_live_collect` (after clearing the cause). Do not remove `depends_on`.

**6-7. Risks, ranked**
1. **HIGH (collection, all three):** every collector has `--data-dumps-cap-gb 50` (q0460 argv; `crontab.txt:27,30`). The ledger projects the guard binding around 11-11 (`EXPERIMENT_LEDGER.md:5616-5617`). That is before LT2's END (11-12), LT3's (11-14) and LT4's (11-16).
   - If it binds, the collectors stop writing, so window data is lost for good.
   - q0460 can then never print `LIVE_TESTS2_WINDOW_CLOSED`, which blocks q0461.
2. **MED (LT2):** the timeout of 21,600 s is half of LT3/LT4's, yet LT2 is the heaviest job (about 7M series rows, 20 placebo draws). Memory has not been measured for any of the three. The memory caps are 5,000 MB for LT2 and 6,000 MB for LT3/LT4 (twice `mem_mb`). An out-of-memory error or timeout fails twice, with no result seen.
3. **LOW:** a manual rerun with a different `--out` would bypass the one-shot guard and add a second trials line.
4. **LOW:** stale text, which does not affect behaviour. q0461's `next_action` says the count rule is missing, but it exists. Job titles still say "DRAFT".

**MUST (ops only, no change to registered code)**
- **M1:** keep host `data-dumps` below 50 GiB through 11-17, by archive rotation or by raising the guard in the q0460 argv and crontab. The 10-28 change is the precedent (`EXPERIMENT_LEDGER.md:4598`). Record the reason in the ledger.
- **M2:** at about 11-13T06:30Z, check that q0460 is 'done'. If it is 'failed', retry it as in section 5.
- **M3:** before each `not_before`, run a code-only preflight on the host that reads no data: `load_spec()` plus `code_check()`. This confirms the deployed checkout matches the pins.
- **M4:** raise q0461's `timeout_s` to 43,200 and give all three jobs a larger `resources.as_cap_mb` (for example 8,000) where host memory allows. This changes only the queue spec.
- **M5:** add one runbook line: if the output exists but the trials line is missing, append `trial_record(json.load(out))` once. Never rerun.
- **M6:** confirm the LT3 and LT4 cron readers ran through END plus about 9h (from the log tail and the ops-stats counts only).

**Could not verify (no host access):** the current state of q0460 and the current size of `data-dumps`; whether the host checkout matches HEAD; peak memory and run time; whether the LT3/LT4 cron collectors are healthy.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/q0461_lt2_analyze.json`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/q0460_lt2_live_collect.json`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/q0475_lt3_analyze.json`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/q0486_lt4_analyze.json`
- `/Users/DayyanSheikh/Projects/astrolabe/scripts/oracle/queue_worker.py`
- `/Users/DayyanSheikh/Projects/astrolabe/scripts/oracle/crontab.txt`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_live_tests2.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/battery2.py`
