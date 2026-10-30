# LT14 F1-F3 fixes: diff re-check (science-reviewer, 2026-10-30; read-only)

**Verdict: ACCEPT_WITH_FIXES.** F1 now does what it should: a stale or missing catalogue, or a restore that leaves a gap, stops the job with exit 3 and nothing is sealed. Two things need fixing before the seal. First, the guard's data cap (55) does not match the census's own cap (50). Second, the census still refuses on `added_utc`, and the frozen design does not support that refusal. That one was my own error in the previous review's wording of F3.

## Verified
- `LIVE_TESTS_14.md` still hashes to `f047c000…f815`, unchanged from b6bb71a7 to d2cfa5f5. Its last commit is still 485c63dd.
- Commit 22eaddd8 touches only the LT14 files listed in the code note. No E026 frozen file, no `model_specs/` and no `signal_engine/` file changed.
- `pytest tests/test_live_tests14.py tests/test_live_tests14_census.py`: **61 passed**.
- `live_tests14.py` now hashes to `25494780…ee2f`. That hash is not yet in `EXPERIMENT_LEDGER.md` (grep), so it still has to be re-announced.

| Item | Status | Evidence |
|---|---|---|
| F1: q0744 command | OK | `archive_catalogue.py --out <scratch>` writes only `<out>/*.jsonl`, `releases.json` and `README.md`, plus a temp dir that it deletes (`archive_catalogue.py:189-221`). The tracked catalogue is not touched. Draft releases are skipped. `gh` runs through PATH, and the queue cron sets `PATH=/home/opc/.local/bin` (`crontab.txt:10`). The q0744 note "gh not verified on the host" is now out of date. |
| F1: tag computation | OK | It uses the same `dc.matches` as `measure`. A tag given by the caller is left alone. A missing or empty catalogue gives `hit=[]`, then exit 3 before any restore (`lt14_restore_guard.py:124-131`). |
| F1: coverage check after restore | OK | Restore root = `dest/data-dumps/research_lab/snapshots`, the same as the second root in q0741 and q0742. It uses the census's own `_meta_by_slot`. A non-zero restore returns its own code. In the worker, a failed q0743 never reaches `done`, so q0741 cannot seal (`queue_worker.py:235`). This fails closed. |
| F2: cap arithmetic | OK, but see Fix A | `used + bytes + reserve <= cap·2^30`. The error message picks the right cause. `disk_mb` 4400 is labelled as an estimate. |
| F2: how "used" is measured | Minor | `tree_bytes` sums `st_size` (apparent size). `arepo_pass.sh:16` and the census `_cap` use `du -sk` (`live_tests11_base.py:111-114`). |
| F3: compared fields | OK | Status is print-only (`p_registry_status`). `model_id`, `spec_sha256` and the canonical sha refuse. |
| F3: `added_utc` refuses | Not supported | See Fix B. |
| Job graph | OK | q0740 (now) → q0744 (11-17 05:01) → q0743 (05:01; deps q0740, q0744) → q0741 (05:01) → q0742 (06:00). The last tail slot is 04:31Z and its 30-minute tolerance ends at 05:01, so seal-after-tail holds. The span [11-07, 11-17) matches the guard's globs (20261107…20261116) and `--since/--until`. |
| No other behaviour change | OK | `live_tests14.py` changed only the comparison and one extra print field. |

## Required fixes
- **A (MEDIUM): two caps that disagree.** q0742 runs with `--data-dumps-cap-gb 50` and exits 75 "not now" above 50 GiB (`run_live_tests14.py:100`). The guard allows a restore up to 55. So a restore that passes the guard (about 4 GB) can leave the census stuck in "not now". Fix: add `--data-cap-gb 50` to q0743's argv, or use the smaller of the two caps. Optionally switch `tree_bytes` to `b.du_bytes` so it measures the same way.
- **B (LOW-MEDIUM): `added_utc` should be print-only.** The design seals "P's spec sha" (l.531). The refusal list (l.534-535) covers inputs not in the seal and a P that fails the audit. `added_utc` is neither. The audit does not test it (`live_tests14_base.py:206-253`), and the engine only copies it into `spec["_added_utc"]` (`specs.py:74`); I found no reader. The prediction files are already pinned by the seal's sha256s. Refusing on it blocks the one-time census without a durable record, which is the same objection that applied to `status`. Fix: compare only `model_id`, `spec_sha256` and the canonical sha, and add `added_utc` to `p_registry_status`. Change the `test_must4_…` case so that a changed `added_utc` passes. This changes the hash again, so re-announce it in the ledger before q0741.
- **C (LOW): q0744's release check is too loose.** Its `next_action` check "a `data-2026111*` release exists" passes on any release from 11-10 to 11-19. The rotation job runs at 03:30 (`crontab.txt:16`), so the 11-17 release may not exist by 05:01. Change the check to `data-20261117*`, or rely on the post-restore coverage check (it already covers this) and fix the title's "including the 11-17 release". Also remove the stale note that `gh` was not verified on the host.
- **D (LOW, optional): needless stop and download.** If the host already holds every span sidecar (retention is 12 days, so it should on 11-17), the guard still downloads about 4 GB of duplicate files. And if no catalogue tag matches, it stops even though nothing is missing. Running the coverage check on the host roots first, and skipping the restore when there are no gaps, would avoid both. Both cases fail safe as written.

## Promotion
- **q0744: may be promoted now.** It reads only release metadata, waits until 11-17 05:01, and none of the fixes touch its inputs. Fix C is wording only.
- **q0743: promote after Fix A** (one argv change).
- **q0741 and q0742: promote after Fix B** is merged and deployed to the host, the new `live_tests14.py` sha is re-announced in the ledger, and the code is final. The seal records whatever code hashes are on the host at 11-17 05:01.

## Not verified
- Whether the 11-17 release is published before 05:01.
- November `rows_ext` sizes and data-dumps usage on 11-17.
- Whether a sidecar can appear in two releases. If it can, the second restore would collide in `dest` without `--overwrite`; that fails closed.
- How group-granularity releases (more than 20,000 files) are restored. Their rows ignore the path glob, so the measured bytes overstate the real size, which can only cause a cautious stop.
- No host or network access, and no real data read.

Files:
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/lt14_restore_guard.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/live_tests14.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_live_tests14.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0743_lt14_sidecar_restore.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0744_lt14_catalogue_refresh.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0742_lt14_census.json
- /Users/DayyanSheikh/Projects/astrolabe/scripts/oracle/crontab.txt
