# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-24 04:54 UTC+1 (2026-10-24 03:54Z), signal-engine autopilot session 28

## In plain English
- **New: live test LT12's protections are in the engine.** The experiments track froze LT12's design overnight and asked
  the engine to keep two future signal families hidden until 2027-01-03: `mirror` (how one book of a two-option event
  reacts to the other book's spread) and `mixedlad` (unpaid versus paid options reacting to a sibling's shock), plus a
  rule that no model explanation may touch those terms before then. Applied and tested; neither family exists yet, so
  nothing had been computed on them. No model, feature or score changed.
- **Engine health:** fine. The new input monitor ran at every pass overnight; the 02:31Z capture shows all 17 families
  filled, universe 57,884 markets, no alerts. `tilt` back-fill is at 106 of 136 and finishes before today's 12:14Z
  refit, when se24 / se25 fit for the first time.
- **The "newest data" test (q0516) has not run yet:** it waits behind the other track's large exclusive job (q0116i).
  It will run on its own when the slot frees; nothing to do.
- **Scores (early, 3 days, not a promotion read):** the LightGBM base model (se1) leads the logistic champion by about
  0.05-0.07 nats on the direction targets. No promotion is possible before ~11-04 (14-day minimum).
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** session 28's LT12 embargo entries merged and deployed; live fits and predictions unchanged.
- **Refit `q0512`** (daily, 12:14Z): last ran 10-23 (peak RSS 3,204 MB). Still `insufficient_coverage` (expected): se8,
  se9, se10, se16, se20 (aux tables from 10-13; ~10-27). The `res_7d` LightGBM fits wait for labels (~10-28).
- **Score `q0513`:** 3 days scored (10-23 12:16Z). Next at ~10-24 12:16Z.
- **Aux tables (03:50Z):** `book0`, `dispgap`, `dormant`, `hwm`, `movetype`, `surprise` 136; `crypto`, `event`,
  `participation`, `rewards` 124; `tilt` 106 (filling 12 per pass). Input monitor: 0 alerts at the 02:31Z capture.
- **Queue:** q0512 / q0513 on their daily gates (retry_wait while the exclusive slot is busy). The other track's q0116i
  (`run_ml_dev`, exclusive, ~6 GB RSS) runs in <= 5.5 h slices; q0516 (priority 30) waits behind it. Nothing touched.

## Embargo list (model visibility unchanged; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
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
1. **LT12 freeze requests applied** (DESIGN_V1 §33): `config.EMBARGO` gains `mirror` (LT12-CH245), `mixedlad` (LT12-CH244)
   and `attrlimit_lt12` (models champion, se1, any broad model; `no_broad_families: ["mirror", "mixedlad"]`), all until
   2027-01-03T00:00Z (the later of that and LT12's analysis commit). Checked against `LIVE_TESTS_12.md` §9 (sha256
   `a543db63…`). No `feeclass` token. New `test_lt12_freeze_requests`; the attribution-limit loop lists `attrlimit_lt12`.
   Signal-engine (78) and lab (57) tests pass; ruff clean. CANDIDATES reply, ledger entry and checkpoint line written.
2. Session 27's next action 1 checked: `state/input_health.json` exists on the host and is clean.

## Next actions
1. **Input monitor:** read `state/input_health.json` on the host each session; act on any alert.
2. **10-24 refit (12:14Z):** `tilt` complete; se24 / se25 fit on the direction targets; peak RSS under ~3,300 MB.
3. **q0516 result:** read `SE_DEV_REFIT_FULL` in `~/arepo/run/queue/logs/q0516_se_dev_refit_full.1.log`. Apply the
   fixed rule (DESIGN_V1 §32): a challenger only if all 3 direction targets gain, each CI excludes zero and >= 4/5 days
   are positive. Write the result into §32 and the ledger either way.
4. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap` later, and
   `flow` before 11-16. Same for `rewards` against E022 before 11-18.
5. **If CH214 drops at LT9's census:** `book` / `book0` need a new date by ledger line. If a census drops CH232 / CH233 /
   CH234, withdraw that LT11 token with a ledger line.
   Same for LT12: a census drop of CH245 / CH244 withdraws `mirror` / `mixedlad` and any `attrlimit_lt12` item made only for it.
6. Around 10-27/28: se8, se10, se16 and se20 start fitting and the `res_7d` LightGBM fits should work. Watch refit RSS.
7. Remaining engine-first ideas (build only with a real prior): CH250 `paymaker` and CH248 `mt_twin_printed` only after
   11-18 / 11-22; CH239 `ruleclass` (likely a category proxy); `volage` after 11-22. LT12 families (`mirror`, `mixedlad`,
   `feeclass`) are not to be isolated before its freeze.
8. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se`, `astrolabe-lab-se-promo` and
   `astrolabe-lab-se-mid`, `astrolabe-lab-se-inputs` (PR #30, merged), the `/tmp/se_*` scratch (Mac and host `/tmp/se_ih`) and old backfill logs.

## Notes for the other track
- The monitor's backtest confirms the 10-21 00:31Z / 02:31Z passes are missing from the engine's captures, and that the
  2 h / 6 h / 24 h look-back columns of the following captures are empty because of it (missing stays missing).
- No queue job of yours was paused, cancelled or re-prioritised.
