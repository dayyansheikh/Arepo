# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-28 11:38 UTC+1 (2026-10-28 10:38Z), signal-engine autopilot session 29

## In plain English
- **New challenger: `se26_lgbm_mm_full`.** The LightGBM models never learned from the newest fifth of their training
  window, which they only used to decide when to stop. A development test (q0516, run 10-24) refitted the base LightGBM
  on the whole window. It forecast slightly better on all three direction horizons, every day of the five tested. That
  met the rule written before the test ran, so the variant is now a registered challenger. The gain is small (about 0.002
  nats) and is development evidence only. Live prospective scoring decides from now on. Nothing else changed.
- **Engine health:** good. Refits run daily (last one 10-27 19:12Z, 77 min, peak 3.4 GB, 91 fits ok). The input
  monitor shows 0 alerts at the 08:31Z capture (universe 48,352 markets, 17 families filled).
- **Scores (7 days, not a promotion read):** the LightGBM models se1, se17 and se18 lead the logistic champion by about
  0.046 nats on `dir_2h` and 0.06-0.07 nats on `dir_6h` / `dir_24h`. On `res_7d`, se1 is level with the champion. The
  14-day minimum keeps any promotion until about 11-04 (se26: about 11-11).
- **Small fix:** one CLI test had a hidden date dependency and started failing today. Its synthetic data fell out of the
  14-day training window. Its clock is now pinned; no engine code changed.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** session 29's se26 registration merged and deployed; se26 fits at the next refit (q0512, ~10-28 15:00-17:00Z,
  20 h after 10-27 19:12Z) and predicts from the next capture after that.
- **Refit `q0512`:** daily, drifting earlier (min interval 20 h). 13 fits still `insufficient_coverage` (aux tables that
  started later, mainly `res_7d` for the aux-family models). Peak RSS 3,423 MB; se26 adds one se1-sized fit per target
  plus a full-window refit (expect +2-4 min, about +100 MB).
- **Score `q0513`:** 7 days scored (leaderboard 10-27 19:14Z). Promotion block K = 10 → 11 with se26.
- **Aux tables:** all 17 families filled at the latest capture (`dispgap` coverage 0.60 is its normal share).
- **Queue:** q0512 / q0513 on their daily gates. The other track's CH261 map (q0701) is running. Nothing of theirs touched.

## Embargo list (unchanged this session; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, **`se26_lgbm_mm_full`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **q0516 read, DESIGN_V1 §32 rule applied:** `dir_2h` +0.0016 [+0.0014, +0.0017], `dir_6h` +0.0027 [+0.0025, +0.0029],
   `dir_24h` +0.0017 [+0.0013, +0.0022] nats over se1 (event-clustered), 5/5 days positive each. Rule met →
   `se26_lgbm_mm_full` registered (spec sha256 `9fdf9d17…`; se1 + `refit_full: true`, `refit_full_scale: 1.0`). Result
   table in §32; ledger entry written.
2. Tests: `test_refit_full_is_opt_in_and_learns_from_every_frame_row` now asserts se26 is the only `refit_full` spec and
   differs from se1 only there; `test_cli_exit_codes_walkforward_and_dashboard` pins its clock to 2026-10-24T12:00Z.
3. Round-18 `CANDIDATES.md` reply: the LT13 hold request is in force (no such column exists or will be built before
   LT13's freeze); no round-18 family built; `pause` is the first candidate once CH261's counts are in.

## Next actions
1. **Input monitor:** read `state/input_health.json` on the host each session; act on any alert.
2. **se26's first fit (10-28 refit):** check `SE_REFIT` in `~/arepo/run/queue/logs/q0512_se_refit.1.log`: se26 `ok` on
   all 4 targets, a `refit_full_rounds` in its artefacts, peak RSS under ~3,600 MB; then predictions appear for it.
3. **~11-04:** first promotion reads (se1 / se17 / se18 reach 14 days). Apply `se-promotion-v2` as written; record the
   decision either way.
4. **CH261 map (q0701):** when done, read its counts. If halts are frequent enough, build `pause` as an input-monitor
   hygiene rule (no K). Build other round-18 families only with a real prior and after their map lines.
5. **Before 11-14:** check that LT2's analysis (q0461, still queued) has run. If not, move `tte`, `chg1d_x_liq` and
   `dispgap` later, and `flow` before 11-16. Same for `rewards` against E022 before 11-18.
6. **Census drops:** if CH214 drops at LT9's census, `book` / `book0` need a new date by ledger line. A census drop of
   CH232 / CH233 / CH234 withdraws that LT11 token; of CH245 / CH244 the LT12 `mirror` / `mixedlad` and related limit items.
7. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze (CANDIDATES round 18), before any
   isolating challenger.
8. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se`, `astrolabe-lab-se-promo`,
   `astrolabe-lab-se-mid`, `astrolabe-lab-se-inputs`, the `/tmp/se_*` scratch (Mac and host `/tmp/se_ih`) and old backfill logs.

## Notes for the other track
- `test_cli_exit_codes_walkforward_and_dashboard` was failing from 10-28 for a date reason (synthetic world 10-11..10-13
  outside the 14-day window). Now fixed on this branch; any other wall-clock test with fixed October worlds may fail the same way.
- No queue job of yours was paused, cancelled or re-prioritised.
