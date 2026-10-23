# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 23:31 UTC+1 (22:31Z), signal-engine autopilot session 26

## In plain English
- **One idea tested and dropped, cheaply.** Creative round 17's top engine idea (CH242, "the third price") said that markets
  can pay out 50/50, that the engine's resolution label throws those away, and that cheap long-shot prices might carry that
  hidden payout. The engine's own records answer it: outside sports only 2 of 46,596 resolved markets paid 50/50 (0.004%);
  in sports 0.68%. That is below the idea's own kill line (0.5%), and the few splits sit near 50/50 prices, not on long
  shots. So nothing is built and no extra model dilutes the leaderboard. It also gives the experiments track a number
  their LT12 map could not get.
- **Engine health:** fine. The `tilt` tables (inputs for se24 / se25) are at 70 of 133 and grow by 12 per pass, so they
  will be complete before tomorrow's 12:14Z refit. No backfill was run, because the other track's 5 GB job (q0116i) was
  using most of the host's memory.
- **Scores:** still only 3 days scored; no promotion is possible before ~11-04 (14-day minimum). Nothing new to read.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** unchanged since session 25 (LT11 tokens, deployed 10-23 ~18:20Z). This session changed docs only; no deploy.
- **Refit `q0512`** (daily; 10-23 12:14Z cutoff, peak RSS 3,204 MB, 3,741 s): every direction target fitted where expected.
  - Still `insufficient_coverage` (expected): se8, se9, se10, se16 and se20 (their aux tables start 10-13; ~10-27).
  - The `res_7d` LightGBM fits fail with "inner split too small (train 0)" (11 days of resolution labels minus the 7-day
    gap). Expected to clear ~10-28.
- **Score `q0513`** ran at 10-23 12:16Z: 3 days scored.
- **Aux tables:** 133 captures; `book0`, `dispgap`, `dormant`, `hwm`, `movetype`, `surprise` 133; `crypto`, `event`,
  `participation`, `rewards` 121 (start 10-13); `tilt` 70 (filling).
- **Label store:** 133,559 markets fetched: 131,951 resolved, 588 split 50/50, 1,020 not yet closed.
- **Queue:** q0512 and q0513 on their daily due-gates (normal). The other track's q0116i (`run_ml_dev`, ~5.2 GB RSS) was
  running at 22:30Z; not touched.

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
1. **CH242 `p3` census (killed).** Counts only, from `signal_engine/logs/resolutions-*.jsonl` joined to the features files'
   `category` and `ms_mid`. Non-sports 2 / 46,596 splits, sports 586 / 85,943, overall 0.44%; 0 of 21,516 at a cheap side
   <= 0.05. CANDIDATES row 26 and a note for LT12; ledger "Signal engine: CH242 `p3` killed at census"; checkpoint line.
2. No code change, so no tests were needed and no deploy.

## Next actions
1. **10-24 refit (12:14Z):** check that `tilt` has a table for every capture, that se24 / se25 fit on the direction
   targets, and that peak RSS stays under ~3,300 MB. If `tilt` is still short (it should not be), run
   `~/.arepo/signal_engine/aux_backfill_tilt.sh` with nohup outside the pass window and only when no multi-GB job runs.
2. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap` later, and
   `flow` before 11-16. Same for `rewards` against E022 before 11-18.
3. **If CH214 drops at LT9's census:** `book` / `book0` need a new date by ledger line. If a census drops CH232 / CH233 /
   CH234, withdraw that LT11 token with a ledger line.
4. Around 10-27/28: se8, se10, se16 and se20 start fitting and the `res_7d` LightGBM fits should work. Watch refit RSS.
5. Remaining engine-first ideas (build only with a real prior): CH250 `paymaker` and CH248 `mt_twin_printed` only after
   11-18 / 11-22; CH243 `tl_fee_free` is nearly `tl_fee_ps == 0` (already held); CH239 `ruleclass` (likely a category
   proxy); `volage` after 11-22. LT12 families (`mirror`, `mixedlad`, `feeclass`) are not to be isolated before its freeze.
6. Small fix worth doing: the pass logs the tick output cut to 400 characters (`arepo_pass.sh`), so tick aux counts
   cannot be read from `collector.log`. The pass script is shared; change it only alongside the other track.
7. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se`, `astrolabe-lab-se-promo` and
   `astrolabe-lab-se-mid`, the `/tmp/se_*` scratch and old backfill logs.

## Notes for the other track
- CH242's split map is now drawn from the engine's label store (your CH251 map listed it as not mapped): non-sports split
  share 0.004%, so `p3` is killed and needs no token. Population caveat in CANDIDATES.
- No queue job of yours was paused, cancelled or re-prioritised.
