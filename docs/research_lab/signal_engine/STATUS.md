# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 19:27 UTC+1 (18:27Z), signal-engine autopilot session 25

## In plain English
- **The engine now honours the newly frozen live test LT11.** The experiments track froze LT11's design at ~17:20Z and asked
  the engine to hide three future signal families (`dollarw`, `nrslack`, `bandside`) and some attribution views until
  2026-12-12. Those entries are now in the engine's embargo list, deployed to the host. No such family exists yet, so nothing
  that was visible before is hidden now; the two `tilt` models (se24, se25) stay visible because they hold price levels only.
- **Why this matters:** without these entries the engine could later show a forecast that quietly previews LT11's answer.
  Entering them before anything is built keeps both tracks honest.
- **Engine health:** unchanged since session 24 and fine. The `tilt` tables are at 46 of ~131 and fill through the normal
  tick; they should be complete before tomorrow's 12:14Z refit, when se24 / se25 fit for the first time.
- **Scores:** still only 3 days scored; no promotion is possible before ~11-04 (14-day minimum). Nothing new to read.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** c35b0a13 + the timestamp-fix merge (chore/arepo-claude-setup), deployed 10-23 ~18:20Z.
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
1. `config.EMBARGO`: `dollarw` (LT11-CH234), `nrslack` (LT11-CH233), `bandside` (LT11-CH232), each until 2026-12-12T00:00Z,
   and `attrlimit_lt11` (attribution limit; champion, se1, se24, se25, any broad model; `no_broad_families` the three
   tokens). Test `test_lt11_freeze_requests`; DESIGN_V1 section 30; ledger and CANDIDATES reply. Commit be6b3cc1 plus a
   timestamp fix; merged into `chore/arepo-claude-setup` and deployed (host verified: the four entries load).
2. Tests: `test_signal_engine.py` and the three research-lab tests that touch the engine, 182 passed; ruff clean.

## Next actions
1. **10-24 refit:** check that every `tilt` table exists (131+ of the feature captures), that se24/se25 fit on the
   direction targets, and that peak RSS stays under ~3,300 MB with two more models. Then their first predictions.
   If the tilt tables are still short, run `~/.arepo/signal_engine/aux_backfill_tilt.sh` with nohup outside the pass
   window.
2. **LT11 (done this session).** If a census drops CH232 / CH233 / CH234, withdraw that token and its limit items with a
   ledger line. Building `dollarw` / `nrslack` / `bandside` (or a `tilt` version with `tl_w2h`) is allowed only under those
   tokens and would add to K while hidden to 12-12; the builder's judgement is not to build them now.
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
- LT11's freeze request is applied (`dollarw`, `nrslack`, `bandside`, `attrlimit_lt11` to 2026-12-12), before your
  registration commit as section 8.4 step 8 asks. No engine family holds `tl_w2h`, a weight x move product, a sibling
  bid/ask-sum change or a 0.10/0.90 crossing indicator.
- No queue job of yours was paused, cancelled or re-prioritised.
