# M2 (CH264) registration conditions (science-reviewer, read-only, HEAD 0c4dffe5, 2026-10-30)

**Verdict: REVISE.** Registration can be made mechanical, but three of your premises fail as written. q0755 cannot be promoted unchanged. Section 16 is stale, so there is no block to apply word for word. The slide rule needs a code change.

Verified at HEAD 0c4dffe5: the design file sha is ff342ff3…bd9b98c (817 lines). Recomputed code_sha over `m2_spec.CODE_FILES` is 64b5dee0…491de2. All eight pinned modules match `m2_spec.SPEC` (l.68-79). `git diff 9299d2e1 HEAD` is empty for every M2 code file, the design and the eight modules. 9299d2e1 is the commit M2_A24_DIFF_CHECK reviewed.

**Defects, most serious first**
1. q0755 depends on `q0754_m2_dryrun` (`drafts/q0755_m2_j1.json:17-18`), which was cancelled. `queue_worker.py:235` needs every dependency `done`, so q0755 would never run and a cron guarded on it would never start. Change it to `q0754b_m2_dryrun` in the registration commit.
2. Section 16 (design l.626-634) says "DRAFT", "second draft … on feat/m2-ch264" and "Next: M2-J0 (q0733b)". FINAL_VERIFY item 7 (l.46) says to refresh it before registration, but the file is frozen. Do not apply it word for word; write the entry in item 3 below.
3. The slide rule cannot just go into the commit. `registered_utc`, `end_utc` and `readout_utc` are hard-coded in `m2_spec.py:33`, which is in CODE_FILES. Sliding changes code_sha and needs a fresh diff check.
4. Untested ulimit. q0754b runs with `as_cap_mb` 6000, while the proposed cron uses `ulimit -v 1572864` (1.5 GiB). The dry run never tests the 1.5 GiB virtual cap, and `j1_runs.jsonl` records RSS only.
5. Dumps guard. Default 50 GiB (`run_m2.py:67`), about 38 GiB used (checkpoint l.32), growing about 1 GB/day. That can reach 50 GiB before 11-24. Every pass then exits 75, q0755 fails and the cron never starts.

**Checklist**
1. **q0754b passes when** `logs/j1_runs.jsonl` (last line) shows:
   - rc 0 and no exit 3
   - `peak_rss_mb` ≤ 600 (design l.456, l.489)
   - `code_sha` 64b5dee0b1788c040071eafdd2b345c759c26a71a274b461315d650cdf491de2 (its spec_sha differs by design)
   - `ledger_records` ≥ 800,000 and `ledger_markets` ≥ 250,000 (`DRYRUN_LEDGER_PAD`, padding happened)
   - `processed_slots` > 0
   - Record the wall time from the queue's attempts log.
2. **`seals/M2_pins.json`.** The code reads only `spec_sha`, `code_sha` (`m2_spec.py:167-174`), `registration_commit_utc` (`m2_analysis.py:656-658`), `manifest_sha256` and `followup_manifest_sha256` (l.661-663). Values:
   - `spec_sha` = `design_sha256` = ff342ff36f815b5cce6851cb1c4526a4daf0829ba5e033012704c80f3bd9b98c (what `spec_sha()` returns, l.118-122)
   - `code_sha` 64b5dee0…491de2
   - for the record, as in M1: design_path, the eight module sha256s and `rule_lexicon_sha256` 2209e0ad…b97e
   - `registration_commit_utc` = the commit's author and committer time, which must be ≤ 2026-11-23T00:00Z (void 11.6)
   - registered_utc 2026-11-24T00:00Z, end_utc 2026-12-15T00:00Z, readout_utc 2027-01-29T00:00Z
   - the dry_run block; both manifest hashes `null`
   - before committing, recompute the design sha and code_sha and check they equal these values
3. **Ledger entry** "M2 (CH264) REGISTERED, <time>". Quote section 16 l.630-634 from "Headline:" to "2027-01-29." verbatim. Then add:
   - design frozen plus amendments 23 and 24, with sha ff342ff3…
   - code_sha, J0 q0733b done
   - the q0754b numbers
   - the pins path
   - no slide
   - a link to this conditions file
4. **Promote to `jobs/`** with only the dependency fix from defect 1:
   - q0755: not_before 2026-11-24T00:50Z
   - q0755b: 2026-12-15T06:30Z
   - q0755c: 2027-01-29T06:30Z
   - q0755d: 2027-01-29T00:00Z
   - q0755e: 2027-01-29T12:00Z
   Every one already has `--pins ../docs/research_lab/seals/M2_pins.json`, and `run_m2.py:80,97,109` refuses to run a real store without it.
5. **Cron** (in a separate ops commit, as M1's 17:30Z addendum):
   ```
   50 */2 * * * grep -q '"id": "q0755_m2_j1".*"outcome": "done"' ~/arepo/run/queue/attempts.jsonl && cd ~/arepo/backend && flock -n ~/arepo/run/m2_j1.lock flock -w 1500 ~/arepo/run/m1_j1.lock nice -n 19 sh -c 'echo 1000 > /proc/self/oom_score_adj; ulimit -v <V>; ../.venv/bin/python scripts/run_m2.py j1 --store ../data-dumps/research_lab/m2_ch264 --snapshot-root ../data-dumps/research_lab/snapshots --rules-root ../data-dumps/research_lab/stream_gamma_rules --pins ../docs/research_lab/seals/M2_pins.json' >> ~/arepo/run/m2_j1.log 2>&1
   ```
   - Holding M1's lock keeps the two J1s from overlapping in both directions. A skipped pass is caught up later, because slots are decided by `finished_utc` (l.471).
   - `<V>` = 6144000 (the same as q0754b) unless the 1.5 GiB cap is shown to work.
   - M3 should take a later offset under the same lock pattern.
   - Neither line checks for queue `exclusive` jobs, so the memory rule rests on the queue.
6. **Empty diff required:** `git diff 9299d2e1 <registration commit>` must be empty for:
   - `m2_spec.py`, `m2_j1.py`, `m2_j2.py`, `m2_readout.py`, `m2_analysis.py`, `scripts/run_m2.py`, `run_m2_j0.py`
   - `MEASUREMENT_M2_CH264.md`
   - the eight pinned modules
   Any change means a fresh diff check.
7. **Deadline:** commit by 2026-11-22T23:59Z, otherwise stop and get a review (defect 3).
8. **Open, not blocking the commit:**
   - (a) Dumps: confirm the trend on the host is below 50 GiB through 2027-01-29. If not, choose with a written reason between adding `--data-dumps-cap-gb` to the argv and rotating data.
   - (b) The `unit_events` refusal has no test (A24 check items 1-2).
   - (c) q0782 serial timing is still a draft.
   - (d) A failed q0755 strands the cron, as for M1.

**Not verified:** q0754b's output, host dumps size, host cron and queue state, the virtual memory J1 needs, and M2 pass wall time against the :20 and :50 gaps.

Files:
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M2_CH264.md
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m2_spec.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_m2.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0755_m2_j1.json
- /Users/DayyanSheikh/Projects/astrolabe/scripts/oracle/crontab.txt
