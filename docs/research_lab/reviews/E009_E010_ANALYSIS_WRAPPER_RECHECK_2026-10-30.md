# E009/E010 wrapper re-check of c9d1658c (science-reviewer, 2026-10-30; read-only)

**Verdict: ACCEPT_WITH_FIXES.** MUST 1 is fixed and I found no new MUST. Three SHOULDs remain, all small.

## Evidence
- **Tests:** `13 passed in 6.14s` (`tests/test_e009_e010_analysis_runner.py`, run in the worktree).
- **Pins (MUST 1):** I ran `git show <commit>:<path> | shasum -a 256` for all 7 files: 9beda37e ×3, 4751a46d ×2, e5f6ca7f, b3b54f93. All 7 match `REGISTERED_PINS` in full (wrapper:79-97), and each file at c9d1658c is still byte-identical to its pin. The rule doc at c9d1658c hashes to `d9d17d8d…421f`, which is `RULE_DOC_SHA256`. The economics pin `c745980b…` matches 9beda37e. The file differs at HEAD (`3418b74d…`), and the wrapper records that through `economics_differs_from_9beda37e` without enforcing it, as runbook:84 discloses.
- **Pin refusals are never 75:** `check_tree` raises `Refusal(...)` with the default `REFUSED=2` (wrapper:114-116, 166). Freeze (240), merge (305, 317), analyze (365) and verdicts (401) all call it.
- **SHOULD 1-6:**
  - S1 fixed: move-aside and no marker, wrapper:325-333.
  - S2 fixed: `_write_unique` uses `open("x")`, 184-194 and 385.
  - S3 fixed: the mtime check comes before anything is written, 250-264.
  - S4 fixed: runbook:80.
  - S5 fixed: 351-353.
  - S6 fixed: `_child_code`, 175-177.
- **Second look:** analyses q0772-q0775 have `max_retries 0` and refuse if `out` or `.run.json` exists (363-364). q0770 has `max_retries 3` and q0771 has 2. Both only copy bytes or merge, and the analyses wait on q0771 through `depends_on`. Freeze refuses if the run folder exists (242), and merge refuses once `MERGE_RUN.json` exists (307). So no retry can produce a statistic twice.

## (a) Always passing `--allow-dirty`: consistent with R9 and honest
R9 (rule:94-96) allows `--allow-dirty` if `tree_dirty` is recorded and disclosed. The CLI still computes the real `dirty` and passes it to `gf.merge(tree_dirty=dirty)` (gapfill CLI:46, 54). The wrapper keeps the narrowing: the allowed-dirty check plus pins run right before the call (317) and again after it (320), and `MERGE_RUN.json` records `dirty_tracked` and `dirty_tracked_after`. The only gap is a file that becomes dirty and is reverted inside the call window, which is negligible.

**SHOULD-C:** runbook:19 ("passes `--allow-dirty` **only** when…") and runbook:49 (`[--allow-dirty]`) now contradict wrapper:316 and runbook:123-128. Update them.

## (b) Mapping CLI exit 2 to 75: should be removed
Because `--allow-dirty` is now always passed, the CLI's dirty refusal (CLI:50-53) can never fire. Exit 2 can now only come from:
- an unreadable git HEAD (CLI:47-49), or
- an argparse usage error (always exit 2).

Both are real refusals and are usually deterministic. Mapping them to 75 makes them look like "not now". The queue then retries every 30 min for up to 48 consecutive tempfails (queue_worker:68-69, 261-268), about 24 h, and writes a failure record each time. No statistic is exposed, because q0772-q0775 depend on q0771. But the time-anchored analysis would slip by about a day, and a real refusal would be hidden. The comment at wrapper:331 ("its dirty-tree/HEAD refusal") is also out of date.

**SHOULD-A:** use `_child_code(p.returncode)` at wrapper:333, so exit 2 stays 2. Update runbook:127-128 to match.

## SHOULD-B: failure of the post-merge check
If the CLI succeeds and then the after-check at wrapper:320 raises:
- `merged/` stays in place;
- no `MERGE_RUN.json` and no failure record are written, because `rec` is built after line 320;
- every q0771 retry then refuses at 307.

Also, `analyze` primary needs only `merged/MERGE_MANIFEST.json` (345-347), so an analysis started by hand would run on that unconfirmed merge.

Fix: wrap the after-check in the failure path (move aside and record), and make primary analyze require `MERGE_RUN.json` with `rc == 0`.

## q0777
The ruling is applied. q0777 depends only on q0770, so it does not gate the analyses. The tag-or-failure disclosure is at runbook:83 and the retention condition at runbook:141.

## Promotion
The drafts may be promoted now: no remaining defect can produce a second look or a wrong-code run. Since not_before is 2026-11-03T08:30Z, there is time to apply SHOULD-A and SHOULD-B first (each a few lines) and re-run the test file. I recommend doing that. One precondition: the host must run a commit whose pinned files match, otherwise every step refuses with exit 2. That refusal is the intended behaviour.

## Not verified
- Which commit the host runs, and the real per-line memory use.
- Whether a poller restart backfill can write after 05:05Z while the mtime check has already passed. It is outcome-blind and best effort.
- `archive_rotate --include-active` matching on nested paths.

Files:
- /Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-ac5269ed9851c5679/backend/scripts/run_e009_e010_analysis.py
- /Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-ac5269ed9851c5679/backend/scripts/run_cross_venue_gapfill.py
- /Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-ac5269ed9851c5679/docs/research_lab/E009_E010_ANALYSIS_RUNBOOK_2026-10-30.md
- /Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-ac5269ed9851c5679/scripts/oracle/queue_worker.py
