# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-29 23:58 UTC+1 (2026-10-29 22:58Z), signal-engine autopilot session 30

## In plain English
- **Engine health: good.** The 10-29 refit (13:40Z) fitted every model in 96 min at a 3.5 GB peak. The newest challenger,
  `se26_lgbm_mm_full`, fitted on all four targets and now predicts at every capture. The input monitor shows 0 alerts at
  the 20:31Z capture (17 families filled).
- **Scores (9 days, not a promotion read):** the LightGBM models lead the logistic champion by about 0.045-0.048 nats on
  `dir_2h`. The 14-day minimum keeps any promotion until about 11-04 (se26: about 11-11).
- **One idea killed, one probe queued.** `pause` (markets that stop accepting orders) was checked over a full day: no
  eligible market was ever halted, so it needs neither a feature nor a monitor rule. A development probe (q0518) now
  tests whether the two learner changes that each helped (900k rows and refitting on the whole window) add up. The rule
  for registering it was written before the run (DESIGN_V1 §34).
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** unchanged this session (docs and one queue job only); main deployed with q0518.
- **Refit `q0512`:** daily, last fit 2026-10-29T13:40Z, 5,775 s, peak RSS 3,494 MB; frame 894,630 dir / 870,760 res rows.
  Same 13 fits `insufficient_coverage` (`res_7d` of the aux-family models whose tables started later).
- **Score `q0513`:** leaderboard 10-29 13:10Z, 9 days scored, K = 11.
- **Probe `q0518`:** queued at priority 30 (gaps only); expect about 4-5 h, about 3-3.5 GB peak.
- **Queue:** nothing of the other track's touched. Their CB8 / CB3 / CB4 / CB5 / LT2-LT4 / copy jobs are queued or waiting.

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
1. **`pause` (CH257) map, counts only:** 13 captures 10-28 22:31Z..10-29 22:31Z, engine eligibility: 0 eligible rows halted
   (`accepting_orders` false); 7 of ~257,600 rows false overall, none open and two-sided. Killed at its map
   (CANDIDATES builder row 27; ledger).
2. **q0518 queued:** `run_se_dev_refit_full.py --base se17_lgbm_mm_900k --days 5`. Fixed rule (DESIGN_V1 §34): register a
   se17 + `refit_full` challenger only if it beats se17 on all three direction targets, each CI excluding zero, at least
   4 of 5 days positive; otherwise a dead end.

## Next actions
1. **Input monitor:** read `state/input_health.json` on the host each session; act on any alert.
2. **q0518:** read `SE_DEV_REFIT_FULL` in `~/arepo/run/queue/logs/q0518_se_dev_refit_full_900k.1.log`; apply §34 as
   written (register the challenger or record the dead end). Watch its peak RSS against the 3,400 MB request.
3. **~11-04:** first promotion reads (se1 / se17 / se18 reach 14 days). Apply `se-promotion-v2` as written; record the
   decision either way.
4. **Round-18 families:** `stress` (CH258) is the next candidate with no embargo; it needs its census first (stress slots
   in 21 days, |corr| with the slot common factor) and the slot-factor control column. `attn` needs CB17's use of the
   comment count checked first. `disp` would be a display column only.
5. **Before 11-14:** check that LT2's analysis (q0461, still queued) has run. If not, move `tte`, `chg1d_x_liq` and
   `dispgap` later, and `flow` before 11-16. Same for `rewards` against E022 before 11-18.
6. **Census drops:** if CH214 drops at LT9's census, `book` / `book0` need a new date by ledger line. A census drop of
   CH232 / CH233 / CH234 withdraws that LT11 token; of CH245 / CH244 the LT12 `mirror` / `mixedlad` and related limit items.
7. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze (CANDIDATES round 18), before any
   isolating challenger.
8. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se`, `astrolabe-lab-se-promo`,
   `astrolabe-lab-se-mid`, `astrolabe-lab-se-inputs`, the `/tmp/se_*` scratch (Mac and host `/tmp/se_ih`,
   `/tmp/se_pause_map.py`) and old backfill logs.

## Notes for the other track
- q0518 is a one-off priority-30 job (mem 3,400 MB, up to 8 h); it runs only in gaps and was not given priority over any
  of your jobs.
- No queue job of yours was paused, cancelled or re-prioritised.
