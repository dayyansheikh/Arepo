# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-24 00:20 UTC+1 (2026-10-23 23:20Z), signal-engine autopilot session 27

## In plain English
- **New: the engine now checks its own inputs.** At every capture it compares each feature family's coverage with the
  previous day and raises an alert if a column goes empty, halves, turns all-zero, if an extra table fails to appear,
  if the market universe shrinks, or if a capture was missed. Without this, a broken data source would leave models
  quietly predicting on missing inputs for days. Tried on the real data (read-only): today is clean. Over the last
  6 days, 9 of 72 captures would have alerted, all because of the two missed passes on 10-21 at 00:31Z and 02:31Z. No
  model, feature or score changed.
- **New: a test of whether the stronger models waste their newest data.** The LightGBM models never learn from the
  newest ~2.8 days of their 14-day window, which they use only to tune themselves. A development job (q0516, low
  priority, about 2 h) compares se1 with an otherwise identical copy refitted on the whole window, over the last 5 days.
  The bar for turning it into a real challenger was written down before the run. Nothing live changes.
- **Engine health:** fine. `tilt` tables are at 82 of 134 and will be complete before today's 12:14Z refit, when se24 /
  se25 fit for the first time.
- **Scores (early, 3 days, not a promotion read):** the LightGBM base model (se1) is ahead of the logistic champion by
  about 0.05 nats at 2 h, 0.06 at 6 h and 0.07 at 24 h, with tight intervals. No promotion is possible before ~11-04
  (14-day minimum). For resolution (`res_7d`) the champion is no better than the market price itself.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** session 27's input monitor and the `refit_full` probe merged and deployed (see below); live fits and predictions unchanged.
- **Refit `q0512`** (daily, 12:14Z): last ran 10-23 (peak RSS 3,204 MB). Still `insufficient_coverage` (expected): se8,
  se9, se10, se16, se20 (aux tables from 10-13; ~10-27). The `res_7d` LightGBM fits wait for labels (~10-28).
- **Score `q0513`:** 3 days scored (10-23 12:16Z). Next at ~10-24 12:16Z.
- **Aux tables:** 134 captures; `book0`, `dispgap`, `dormant`, `hwm`, `movetype`, `surprise` 134; `crypto`, `event`,
  `participation`, `rewards` 122; `tilt` 82 (filling 12 per pass).
- **Queue:** q0512 / q0513 on their daily gates. The other track's q0116i (`run_ml_dev`, exclusive, ~6 GB RSS) has been
  running since 19:22Z in <= 5.5 h slices. The refit (priority 50) gets the next free slot when due. Not touched.

## Embargo list (unchanged)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **Input-coverage monitor** (DESIGN_V1 §31): new `backend/astrolabe/signal_engine/input_health.py`, called at the end
   of `tick` (never changes its exit code). It writes `state/input_health.json` plus a per-capture cache, and
   `dashboard.live_status` / `status` expose `inputs`. It reads features / aux / meta only (no labels, predictions or
   scores). Tests: `tests/unit/test_signal_engine_input_health.py` (6) and the signal-engine and lab suites (190 total)
   pass; ruff clean.
2. **`refit_full` development probe** (DESIGN_V1 §32): opt-in `params.refit_full` in `learners.fit_lgbm` (no pinned spec
   sets it); `backend/scripts/run_se_dev_refit_full.py`; queue job `q0516_se_dev_refit_full` (priority 30, 1,800 MB, not
   exclusive). Two new tests in `test_signal_engine.py`; 192 backend tests pass; ruff clean.
3. /lab display of `inputs`: branch `feat/lab-se-inputs` (worktree `../astrolabe-lab-se-inputs`, from the production tip
   89094c85); frontend tests, tsc, lint and build pass. See "Next actions" for the PR.
4. Ledger entries "input-coverage monitor" and "`refit_full` development probe queued"; checkpoint line.

## Next actions
1. **After the next pass (10-24 00:31Z):** check that `state/input_health.json` exists on the host and that the tick
   log line has `inputs` (the pass log cuts the tick output at 400 characters, so read the file, or run `status`).
2. **10-24 refit (12:14Z):** `tilt` complete; se24 / se25 fit on the direction targets; peak RSS under ~3,300 MB.
3. **q0516 result:** read `SE_DEV_REFIT_FULL` in `~/arepo/run/queue/logs/q0516_se_dev_refit_full.1.log`. Apply the
   fixed rule (DESIGN_V1 §32): a challenger only if all 3 direction targets gain, each CI excludes zero and >= 4/5 days
   are positive. Write the result into §32 and the ledger either way.
4. **/lab `inputs` PR** (`feat/lab-se-inputs`): open, merge after validation, then check the Render / Vercel deploys.
5. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap` later, and
   `flow` before 11-16. Same for `rewards` against E022 before 11-18.
6. **If CH214 drops at LT9's census:** `book` / `book0` need a new date by ledger line. If a census drops CH232 / CH233 /
   CH234, withdraw that LT11 token with a ledger line.
7. Around 10-27/28: se8, se10, se16 and se20 start fitting and the `res_7d` LightGBM fits should work. Watch refit RSS.
8. Remaining engine-first ideas (build only with a real prior): CH250 `paymaker` and CH248 `mt_twin_printed` only after
   11-18 / 11-22; CH239 `ruleclass` (likely a category proxy); `volage` after 11-22. LT12 families (`mirror`, `mixedlad`,
   `feeclass`) are not to be isolated before its freeze.
9. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se`, `astrolabe-lab-se-promo` and
   `astrolabe-lab-se-mid`, the `/tmp/se_*` scratch and old backfill logs.

## Notes for the other track
- The monitor's backtest confirms the 10-21 00:31Z / 02:31Z passes are missing from the engine's captures, and that the
  2 h / 6 h / 24 h look-back columns of the following captures are empty because of it (missing stays missing).
- No queue job of yours was paused, cancelled or re-prioritised.
