# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 18:50 UTC+1 (17:50Z), signal-engine autopilot session 24

## In plain English
- **The /lab page now compares each model with the market price itself.** The score tables have a new column, "Gain vs
  market price", on the 7-day resolution target (`res_7d`). It shows whether a model forecast "will this resolve yes
  within 7 days" better than simply reading the market's own mid price as the probability. The market-price row is
  labelled as a reference, not a model. Embargoed models still show no numbers. This went in as PR #29 (merged and
  deployed on Vercel at ~17:45Z; finishing work an earlier session left half-done).
- **What it shows today (3 days scored, far too early to conclude anything):** the champion is level with the market
  price on resolution, -0.0005 nats with a 95% interval of -0.0016 to +0.0005. On the 2 h direction target the
  LightGBM challengers still lead the logistic champion by about 0.047 nats. That is a learner effect, not an edge.
  No promotion is possible before ~11-04 (14-day minimum).
- **The engine is healthy on the host.** Today's refit (12:14Z cutoff, peak RSS 3,204 MB under the 3,400 cap) fitted the
  three new challengers se21 (`hwm`), se22 (`dispgap`) and se23 (`dormant`), and they have predicted every capture since
  12:31Z. The new `tilt` tables are filling in through the normal tick (12 per 2 h; 46 of 131 at 17:00Z), so se24 and
  se25 should fit for the first time at the 10-24 refit. The separate backfill script was not needed.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** b55a5281 (chore/arepo-claude-setup), unchanged this session (the only change was the web UI).
- **Refit `q0512`** (daily; 10-23 12:14Z cutoff): every direction target fitted where expected.
  - Still `insufficient_coverage` (expected): se8, se9, se10, se16 and se20 (their aux tables start 10-13; ~10-27).
  - The `res_7d` LightGBM fits fail with "inner split too small (train 0)": 11 days of resolution labels minus the
    7-day gap leaves no training rows. Expected to clear ~10-28.
- **Score `q0513`** ran at 10-23 12:16Z: 3 days scored, with `market_price_reference` rows on `res_7d`.
- **Feed:** `signal_engine/feed/latest.json` (champion only), rebuilt by the tick.
- **Queue:** q0512 and q0513 on their daily due-gates (normal). The other track's q0116i was running; not touched.

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
1. PR #29 (`feat/lab-se-vs-mid`, merge 89094c85 into `arepo-free-production-v1`): `frontend/lib/lab/types.ts`,
   `signal-engine.ts`, `signal-engine.test.ts`, `components/lab/SignalEngine.tsx`. Display only; the backend already
   wrote `gain_vs_mid` (DESIGN_V1 scoring section).
2. Validation: `npm test` 238 passed, `tsc` clean, lint clean, build ok, Vercel preview and production deploys
   succeeded, API `/health` 200. `npm run e2e` (with `PW_WEB_SERVER=1`): the lab signal-engine spec passes; 41 specs
   fail **identically** on the branch and on the production tip, because they need a real backend on :8000 with a
   preserved database, which the Mac no longer has. This baseline is worth knowing for every future UI PR.
3. Session 23's STATUS rewrite (tilt family) committed; checkpoint line rewritten.

## Next actions
1. **10-24 refit:** check that every `tilt` table exists (131+ of the feature captures), that se24/se25 fit on the
   direction targets, and that peak RSS stays under ~3,300 MB with two more models. Then their first predictions.
   If the tilt tables are still short, run `~/.arepo/signal_engine/aux_backfill_tilt.sh` with nohup outside the pass
   window.
2. **At LT11's freeze:** apply `dollarw`, `nrslack`, `bandside` and `attrlimit_lt11`. Make sure `attrlimit_lt11` lists
   se24/se25 (requested in CANDIDATES). A `tl_w2h` / `tl_w_traded` version of `tilt` comes only after the freeze,
   under `dollarw` if CH234 registers.
3. **Before 11-14:** check that LT2's analysis (q0461) has run. If it has not, move `tte`, `chg1d_x_liq` and `dispgap`
   later, and `flow` before 11-16. Do the same for `rewards` against E022 before 11-18.
4. **If CH214 drops at LT9's census:** `book` / `book0` need a new date by ledger line.
5. Around 10-27/28, se8, se10, se16 and se20 start fitting and the `res_7d` LightGBM fits should work. Watch the
   refit peak RSS. The vs-market-price column then fills for the LightGBM models too.
6. Remaining ideas, only with a real prior (this session judged both of the first two weak and built neither):
   - `nrslack` levels inside `event` (CH238): mostly re-expresses the overround the family already holds; the bid/ask
     split adds only the summed spread.
   - `ruleclass` (CH239, res_7d first): N2 EV2, the class is likely a category proxy.
   - `volage` after 11-22; CH217 `rowq`; CH207 `umaparams`.
7. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se`, `astrolabe-lab-se-promo` and
   `astrolabe-lab-se-mid` (PR #29, merged), plus the `/tmp/se_*` scratch on the Mac and the host and the old backfill
   logs. Removing them needs a permission this headless session does not have.

## Notes for the other track
- LT11 section 9's pre-freeze hold is still followed: no engine family holds `tl_w2h`, a weight x move product, a
  sibling bid/ask-sum change or a 0.10/0.90 crossing indicator.
- No queue job of yours was paused, cancelled or re-prioritised.
