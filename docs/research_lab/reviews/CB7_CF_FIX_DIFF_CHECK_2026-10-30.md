# CB7 code-freeze fix diff check, 2026-10-30 (science-reviewer, read-only; 117b57ad)

**Verdict: ACCEPT_WITH_FIXES.** There is one fix, and it is to a doc only: the code hashes do not change. Once it is made, the freeze commit can go ahead.

**What I checked**
- **Tests and lint:** `pytest -q tests/test_cb7*.py` gave 43 passed, and `ruff check` is clean.
- **Scope:** `git diff --stat 301b6679 16aec9d9` touches no CB7 file. Commit 117b57ad touches only the 11 CB7 files and drafts. The M3 files are a separate workstream, outside this review. `cb7_census.py`, `cb7_xv.py` and `cb7_common.py` hash the same as they did at the code-freeze check.

**MUST 1 (drafts): met**
- All three `argv[1:]` parse with `build_parser()` and reach `cmd_screen` with family S, G and X. The `--n-boot` flag is gone.
- `depends_on` is correct: q0148 has none, q0150 depends on q0148, and q0149 depends on both. The run order matches the spec's `queue.promote`.
- Outputs are `creative_batch7/results_{S1,G1,X1}.json` and `seals/cb7_*1_stage1.json`. q0148 no longer depends on q0156 or describes the slope. `not_before` is null in all three.
- Resources (300, 1,500 and 800 MB, 3,600 s timeouts) are sensible.
- One consequence to note: `queue_worker.py:235` starts a job only when every dependency's status is `done`. If q0150 refuses or fails, q0149 never starts, so G1 stays uncounted and pending rather than failing silently. That is acceptable.
- **`--union-recorded-utc`: the drafts should not carry it.** The argv is committed before the deploy that runs `union_jsonl.py` (`deploy.sh:20,24`), so a fixed time would be a guess. The "pre-union lower bound" label is acceptable. It is honest, because the count can only be too low. It feeds only the BY triage label. Holm k1 = 3 is fixed and does not use it. If an operator later runs the union by hand just before a screen, they can add the flag at that point.

**MUST 2 (A1 reverted): met**
- `MIN_CLUSTERS` is 30 for every way: `{"event_week": 30, "theme": 30}` in G and `{"event": 30, "date": 30}` in X.
- The new test `test_a1_reverted_every_way_needs_30_clusters` covers this, and the A1 entry is rewritten as "RULED AN AMENDMENT AND REVERTED".

**MUST 3 (hashes): one defect**
- `declaration_sha256()` recomputes to `cf84f910…7f481fd8e`, matching the note.
- The eight module hashes match both `D.file_hashes()` and `shasum`.
- **Defect (fix before freeze):** the code note's `scripts/run_cb7.py` row still shows `9584ac51…90a4a9`. That is the value at 301b6679. The current file hashes to `bc3c43cbf7bda7a72170fc21c90a446ef362f5a1c86558d639725466f333f76d`; update that row. The spec itself is unaffected because `write-spec` computes the hashes from the live files.

**SHOULDs 3-7: no statistic, threshold or decision changes**
- **Freeze-clock check:** it runs before `--dry-run`, and the test refuses a freeze time 2.5 h off the clock (exit 2).
- **Seal-pin check:** `check_seal_pins` runs right after `verify_seal_copies` and before any sealed file is opened. It compares both state and sha256. If the pins are missing it refuses, so it fails closed. The census `seals` block has the same `{state, sha256}` shape, all three "sealed".
- **Union label:** this is a new field only.
- **Promote order:** this is metadata only.
- **Crash-recovery note:** this is docs only.
- Low-risk observations (procedure, not code):
  - `--now-utc` is marked "tests only", but nothing stops it being passed at the freeze. Do not pass it.
  - The rule "`screen_not_before_utc` ≤ T7_X_list − 48 h" is not checked in code. The operator has to check it.

**How to make the freeze commit**
0. Fix the `run_cb7.py` hash row in `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/CB7_ANALYSIS_CODE_NOTE_2026-10-30.md` and commit that separately. This note is not inside the declaration hash.
1. The census exists only at `/tmp/cb7_census/census.json` (sha256 `85824be10a1b4d7c4bbb51e1d7f52581d9889069c0cf47aaec547a88be7e6920`), which is volatile. Before writing the spec, confirm the host's `data-dumps/research_lab/creative_batch7/census.json` has the same sha256. `load_census` refuses otherwise.
2. From `backend` with the venv active, run a dry run first, then the same command without `--dry-run`:
   `python scripts/run_cb7.py write-spec --census-json /tmp/cb7_census/census.json --freeze-utc <now as YYYY-MM-DDTHH:MM:SSZ> --screen-not-before-utc 2026-10-31T06:00:00Z --dry-run`
   - There is no `T7_X_list` argument. The code sets it to max(2026-11-03T06:00:00Z, freeze + 24 h), which gives `2026-11-03T06:00:00Z`.
   - Check that the dry run shows `T7_S_rep_start` "not applicable" and the census and seal pins listed in the code-freeze check.
3. The command writes one file: `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/model_specs/cb7_v1.json`. Commit it on its own, straight away, so the commit time stays within 1 h of `freeze_utc`.
4. In a follow-up commit, copy q0148, q0150 and q0149 into `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/`, each with `"not_before": "2026-10-31T06:00:00Z"` and nothing else changed. Do not promote q0151, q0152 or q0156. q0153-q0155 stay conditional on X1 advancing.
5. Deploy both commits by **2026-10-31T04:00Z**.
   - If the deploy slips past then, use `2026-11-01T06:00:00Z` instead. That is exactly T7_X_list − 48 h, so it is the last valid date.
   - Commit the Stage-1 copies from `seals/` after each screen.

**Not verified**
- The real host column layouts.
- Runtime against the 3,600 s timeout.
- That the host's census.json hash matches.
- Per-theme unit counts and G end-date shares. The code note says the operator still has to report these.
