# CB3 follow-up step: wiring prepared, not deployed (implementer, 2026-10-29 ~23:25Z)

Follows `CB3_DEADLINE_RULING_2026-10-29.md` actions 2-4. Branch `fix/cb3-followup-wire` (from `chore/arepo-claude-setup`
e8dad450). Nothing is merged or deployed and the host crontab is untouched. No window, floor, threshold, formula or sampling
rule changed. The CB3 declaration hash is unchanged at `5233cdb6df15885fe69f2a2b03d5d7689f2dd25421ee1f2595d64a8f4663105b`
(computed on the branch and on the base, so the q0061b census binding holds).

## 1. Host facts (read-only `ssh oracle`, 2026-10-29 ~23:10Z; host code e9682917)
- **Queue.** `q0061_cb3_census`: failed (2 attempts, rc=1, the 10-17 OOM; it stays failed). `q0061b_cb3_census`: done
  2026-10-17T07:16Z. `q0035_j4r_snapshots`: done 2026-10-21T07:25Z. `q0064_cb3_prospective_census`: queued, 0 attempts. It
  depends on `q0064a_cb3_prospective_gate`, which does not exist, so it cannot start (ruling defect c).
- **`cb3_extract/manifest.json`.** 226 captures: 225 extracted (2026-10-10T19:22Z to 2026-10-29T22:31Z) and **1 missing**
  (`20261013T231958Z_80e78ef1`, reason `no_host_manifest`, the same capture as the backfill completeness record). The live
  step currently writes 1 capture per pass (`missing 0`, about 20 s).
- **`cb3_followup/`.** Does not exist. No follow-up pass has ever run, so `T3_fu_start` is undefined.
- **Pass structure.** cron `31 */2 * * *` runs `scripts/oracle/arepo_pass.sh`. The host copy is identical to the repo at the
  host head. CB3's only live step is the `run_cb3_quote_state.py --all-new --data-dumps-cap-gb 50` line, inside the
  `state=complete` branch. The last 6 passes took 31-34 min (start :31, end :02-:05), so a step of at most 10 min fits.
- **Inputs the step needs.** `~/.arepo/wallet_hash_key` exists, so the `missing_no_wallet_key` path will not fire. The latest
  trade samples have `plan.json`, `trades.csv.gz`, `wallets.csv.gz` and `features.csv.gz` (the fix-8 input).
  `archive_retention.json` has no `cb3_followup` rule, so the step's output is never rotated off the host.
- **Disk.** `du -sb data-dumps` = 48,633,600,714 B = **48.63 GB decimal** (46 GiB). `_dir_gb` divides by 1e9, so the shared
  50 guard leaves only **1.37 GB of headroom**. Every `--data-dumps-*-gb 50` step, including this one, will refuse at the same
  time. Each refused pass is missing and is never backfilled (§2.8). Root disk: 23 GB free.

## 2. What changed (commit on this branch)
1. `scripts/oracle/arepo_pass.sh`: one new line after the quote_state line and before the signal-engine line, inside the
   complete-capture branch. It is the §4.3.2 design line verbatim, plus the operational guard used by every other CB step
   (40 -> 50 GiB, ledger 2026-10-28):
   `timeout 600 nice -n 10 $PY scripts/sample_trades_followup.py --snapshot latest --frac 0.5 --vacuum-max 300 --rps 4 --budget-s 540 --data-dumps-max-gb 50 2>&1 | tail -1 || true`
   It has its own 600 s timeout and a self-budget of 540 s. `|| true` means it can never fail the pass, and the one-line
   JSON summary goes to `collector.log`.
2. `docs/research_lab/seals/j4r_window.json`: `"final": true` with `t_j4r_end` unchanged at 2026-10-21T00:00Z, plus a
   `finalised` note. The declared action is the seal's own `rule`: *"When J4-R has run, the coordinator commits the actual
   final --until here with final true; the end can only move forward."* CB3 §1.2 defines `T_J4R_end` as J4-R's actual final
   `--until`. The ledger records "SB2-J4-R (q0035, run `bounce-j4r`, finished 2026-10-21 07:25Z)" on declared window
   `[2026-10-16T00:00Z, 2026-10-21T00:00Z)`, and the committed q0035 argv has `--until 2026-10-21T00:00:00Z`. Ruling action 2.
3. `docs/research_lab/queue/jobs/q0064_cb3_prospective_census.json`: the title now names `T3_dev_end` (10-25 moved forward by
   whole days) instead of hardcoding 10-25, and a dated note was added. argv is unchanged: `--before 2026-10-25T00:00Z` is
   only an upper-bound check in `run_cb3.py`, and the window end comes from `dev_window_end`. **q0064a was not created.**
4. `backend/scripts/sample_trades_followup.py`: docstring only (this script is not hashed). `cb3_followup.py` is untouched,
   because every function in it is in the declaration hash.
5. Tests: new `backend/tests/unit/test_cb3_followup_wiring.py` (bash -n; line position and isolation; arguments equal the
   hashed `FOLLOWUP_CONSTANTS`; the guard equals the other CB steps; script exit codes). `test_cb3_maker.py` now asserts the
   pin is final (`[10-16, 10-21)`); its single-commit example moved to `seals/cb1_t_rep_start.json`, because the pin now has
   2 commits; the non-final behaviour is still tested on a tmp pin.

## 3. What the reviewer must check before deploy
**Fixes 7-9** (freeze check 2026-10-16, "7-9 before deploying the follow-up"). They were coded in badb274a and listed as
verified at 13c6ac8 by the re-check (RELEASE_Q0061, ~23:25Z). The ruling still asks for a check. Confirm:
- (7) `cb3_maker.build_prospective`: `not_reached` markets are excluded and counted; failed, `http_*`, `retries_exhausted`
  and partial windows are unavailable, never unfilled; q0064 reports counts by status (`cb3_maker.py:~1266-1315`).
- (8) `pre/features.csv.gz` is copied unchanged (`cb3_followup.py:268-290`) and read for pre-origin visibility and the
  500-print cap (`cb3_maker.py:~1367`).
- (9) A pass is used only if `plan.previous_capture_id` names the onset capture (`cb3_maker.py:1243`,
  `cb3_quote_vacuum.py:732`); no wallet key writes the `missing_no_wallet_key` manifest; exhausted retries are recorded as
  `retries_exhausted`, not 429.
- Since 13c6ac8 only 6e41476f touched these modules (memory-bounded `load_quote_panel`; default `drop_mat=()`, so
  `plan_vacuum` still gets `s2_recv`).

**Open points the reviewer should rule on.** The first two cannot be fixed without changing the declaration hash.
- a. **`plan_vacuum` has no unit test.** Confirm that `u["cap_i"] == P.n_caps - 2` selects onsets whose vacuum is at the
  current capture, and that `s2_epoch` (current capture's second-sweep receipt) is the declared window start.
- b. **Exception isolation inside `run()`.** `plan_vacuum` runs after the post fetch and before `meta.json`/`manifest.json`.
  If it raises, the script catches it (exit 0), but the pass directory has `plan.json`/`pre/`/`post/` and no manifest. Readers
  glob `*/manifest.json`, so that pass is invisible rather than recorded as missing. Is that acceptable, or must the
  analysis count manifest-less directories as missing?
- c. **Over-cap refusal writes nothing** (no directory, no manifest). Confirm that "absent = missing, never backfilled" is
  how q0064 counts missing passes.
- d. **`T3_fu_start`.** §1.2 says "deployment commit time ... recorded in `cb3_followup/manifest.json`". The step writes
  only per-capture manifests, and `run_cb3.py census P` uses the min `capture_start_utc` over follow-up manifests. Record
  both the deploy commit time and the first follow-up capture in the ledger. Note that a `missing_no_wallet_key` manifest
  would also count as the first pass.
- e. **Disk.** Only 1.37 GB of headroom remains under the shared 50 (decimal GB) guard. Decide whether rotation keeps it flat
  before relying on 3 full days of follow-up passes. No guard was raised here.
- f. Peak RSS of at most 500 MB is declared but not enforced (no `ulimit`), as for the other CB steps.
- g. Ruling defect (d), `pin_rep_start` with the fixed 10-25 + 2d, is unchanged here.

## 4. Deploy steps (orchestrator, after an accepting review)
1. Merge `fix/cb3-followup-wire` into `chore/arepo-claude-setup` (the branch the host runs; never production).
2. On the Mac: `scripts/oracle/deploy.sh chore/arepo-claude-setup`. It waits for the collector lock, rsyncs the committed
   tip and unions `trials.jsonl`. No crontab change is needed, because cron already calls `arepo_pass.sh` by path.
3. Verify on the host (read-only): `git -C ~/arepo log --oneline -1` shows the merge;
   `grep -c sample_trades_followup ~/arepo/scripts/oracle/arepo_pass.sh` returns 1;
   `cd ~/arepo/backend && ../.venv/bin/python -c "from astrolabe.research_lab import cb3_declaration as D; print(D.j4r_window(), D.declaration_sha256())"`
   prints a finite end of 1792540800.0 and `5233cdb6…105b`.
4. After the next pass (:31 on an even UTC hour, about 35-45 min): `grep cb3_followup ~/arepo_collector/logs/collector.log | tail -1`
   shows `stopped` null or `budget`, and `requests`, `post_rows` and `not_reached`.
   `ls ~/arepo/data-dumps/research_lab/cb3_followup/*/manifest.json` exists. The first pass has no vacuum tasks (there is no
   previous `vacuum_plan.json`).
5. Ledger: record `T3_fu_start` (deploy commit time and the first follow-up capture id and start), the pin flip, and that
   q0064 stays held. Per §1.2, `T3_dev_end` = first whole-day end giving >= 3 full days after `max(T3_fu_start, 10-21T00Z)`.
6. Only after 3 full days of follow-up passes: create gate `q0064a_cb3_prospective_gate` (ruling action 4).
7. Rollback: revert the merge commit and rerun `deploy.sh`. Data already written under `cb3_followup/` stays (it is never
   deleted, and no reader uses it before q0064).
