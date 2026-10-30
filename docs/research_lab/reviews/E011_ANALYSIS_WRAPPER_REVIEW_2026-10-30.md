# E011 analysis wrapper review (science-reviewer, read-only, 2917cefa, 2026-10-30)

**Verdict: ACCEPT_WITH_FIXES.** The wrapper runs the registered statistic unchanged, on byte-identical frozen inputs, with all 7 pins enforced and one-shot semantics. Two record-level defects need fixing first: registered secondaries that would be wrongly marked "not produced", and readings that have never been declared in the ledger.

**Evidence**
- **Tests:** `pytest -q tests/test_e011_analysis_wrapper.py`: 10 passed. `ruff`: all checks passed. `test_pins_are_the_seven…` runs `check_tree` on this checkout, so all 7 files equal their pins at 2917cefa.
- **(1) Same run as the registered command:**
  - The registered `main` (`run_surprise_snapshot.py:53-55`) calls `ss.analyze(start_utc=args.start, end_utc=args.end)`, with defaults `ss.REGISTERED_UTC`/`END_UTC` (:48-49).
  - The child (`run_e011_analysis.py:99-110`) puts the `partial(root=…)` binding into the same `sys.modules` object that the script imports, so only `root` changes. `n_boot` 4000 and seed 20261013 stay at their defaults (`surprise_snapshot.py:630-631`).
  - The rest of `main` is unchanged: `basicConfig`, and a `Limiter` that sends no request.
  - `git diff 3e628ec3 HEAD` on `surprise_snapshot.py` shows only `_cluster_id` and `load_capture`. The episode, accounting and verdict code is as registered. The registered file's sha256 is 7c17571c…, which matches the ruling.
- **(2) Pins before anything runs:** order is `_not_before`, then `check_tree`, then copy or child (:286-287, :320-322). A mismatch or missing file gives exit 2, and the tests cover it.
- **(3) Date refusal and one-shot:**
  - Exit 75 before 13:00Z in both steps.
  - Freeze refuses if `inputs/` exists. Analyze refuses if the output or `.run.json` exists.
  - q0791 has `max_retries 0`. A child exit of 75 is mapped to 1. Failure records use `open("x")` with a timestamp, so none is overwritten.
- **(4) Freeze:** copies `st_size` bytes, cuts at the last newline, builds in a temp folder and renames it. Alerts are copied before outcomes. Out-of-window lines are ignored by the filter at :642-648.
- **(5) Counting:** `analyze` writes no trial line (no "trial" in either registered file). `trials.jsonl` has 0 E011 or E009/E010 lines. The registration has one primary and no multiplicity correction, so E011 counts as exactly 1 test.
- **(7) Queue drafts:** q0790 has not_before 13:00Z, no dependencies, 2 retries, no network. q0791 has 13:30Z, depends on q0790, 0 retries, as_cap 3000. q0792 has 13:30Z, depends on q0790, network lane, no `--delete`, and does not gate q0791. All three are correct.

**MUST**
1. **Secondaries (c), (e), (f), (g) are not "not produced".**
   - A pre-declared descriptive supplement exists: `surprise_supplement.py` and `run_surprise_supplement.py --root`, commit 711a9107 (2026-10-20), disclosures in e53dceaa.
   - The readiness doc requires it: A4 (`LIVE_TESTS_READINESS_2026-10-19.md:341-351`) says "Run it once, straight after `run_surprise_snapshot.py analyze`", and A7 :395 says "E011, then the supplement".
   - The ruling's defect 4 cited S1 (:146-150) and missed A4.
   - As written, `SECONDARIES_NOT_PRODUCED` (wrapper:88-96), runbook §4 and §6.4 would put a false statement into the record. They would also drop (g), the registered shortfall record.
   - Fix: add a draft q0793. It should depend on q0791, have 0 retries, pin the two supplement files at their e53dceaa sha256, save stdout write-once, and run with `--root D/inputs`. Remove or relabel the not-produced file. Add an optional SHOULD step: `live_verdicts.py e011` on the saved output (readiness :328).
2. **Declare the rulings below in the ledger before promotion.** The chained episode reading appears nowhere in the ledger. A grep for "chain" finds no E011 hit.

**SHOULD**
1. **No catch-up or quiescence check.**
   - The runbook (line 6) claims that every SHOULD from the E009/E010 review was applied. Its SHOULD 3 was not: the E009/E010 wrapper has a catch-up check at `run_e009_e010_analysis.py:250-264`, and this wrapper has none.
   - The 12:31Z pass takes about 18 minutes (ledger :1106) and is the first pass after the registered "12 h after due" point.
   - Fix: exit 75 if `outcomes.jsonl` or `passes.jsonl` was modified less than 10 minutes ago, or the collector lock is held. Record whether there is a pass with `written_utc` at or after 2026-11-11T12:31Z.
2. **PRE_RUN pass counts are not limited to the window** (:243-253). Restrict them to `[REGISTERED_UTC, END_UTC)` and add an outcome-blind count of missed slots on the 2-hour :31 grid.
3. **`analyze` does not check `pre_run_sha256`** (:325) and does not record numpy, pandas or Python versions. Add both.
4. **Runbook §4 should state the count:** "1 counted test; no `trials.jsonl` line written by analyze".

**Rulings: exact ledger text to add before the run**
```
## E011 analysis readings declared before the run (outcome-blind)
1. Input: the registered `run_surprise_snapshot.py analyze` (defaults, unchanged) reads byte prefixes of
   alerts.jsonl/outcomes.jsonl frozen at FREEZE_MANIFEST `frozen_utc` (>= 2026-11-11T13:00Z). "Analysis time" in
   "any line still pending at analysis time is reported as pending, never imputed" = `frozen_utc`. Outcome lines
   written after it are not used.
2. Catch-up: no gate on pass times beyond the registered 13:00Z. Lines pending at `frozen_utc` are reported as
   pending, not unavailable. Last pass `written_utc` and whether the 12:31Z pass is present are reported.
3. Episode: registration "alert lines of one market closer than 24 h collapse to the first" is implemented by the
   registered `analyze()` (named in secondary (g)), which chains each line from the previous line of that market
   (surprise_snapshot.py:659-665, unchanged since 3e628ec3). This reading binds; no head-anchored variant is computed.
4. Secondaries (c)(e)(f)(g) and the alert+control (d) come from the pre-declared supplement (711a9107/e53dceaa) run
   once on the same frozen inputs after the primary; descriptive, no verdict role, not counted.
5. Pre-run counts (non-ok passes, window alert lines with fee_category=="unknown", missed slots) are operational
   counts from passes/alert lines only; no outcome line is parsed.
6. Code version: as in the 2026-10-30 18:30Z deviation (pins 413107af… etc.); nothing added.
7. Shortfall: the result entry reports every missed collector slot in the window (10-14 00:31-10:31Z, 6 passes,
   ledger :1086, plus any later), from passes.jsonl; the window is not extended.
8. Counting: E011 is 1 counted test (one primary); analyze writes no trials line.
```

**Not verified**
- The host HEAD and pins on Oracle.
- Real memory use (RSS).
- That the collector is still scheduled on 11-11 and that the 12:31Z pass finishes before 13:00Z.
- `--include-active` matching on `inputs/*`.
- Child-vs-live equality on real data; this was shown on synthetic lines only.

**Promotion:** Yes, q0790-q0792 may be promoted after the MUSTs with a diff-only check, provided that:
- the diff touches only the wrapper's secondaries constant, the new q0793 draft and its pins, the runbook, the tests and appended ledger entries;
- `git diff 2917cefa.. --` on the 7 pinned paths and the 2 supplement files is empty;
- the scoped tests pass again.

Relevant files:
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_e011_analysis.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/surprise_supplement.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/LIVE_TESTS_READINESS_2026-10-19.md
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/E011_ANALYSIS_RUNBOOK_2026-10-30.md
