# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 22:10 UTC+1 (21:10Z), signal-engine autopilot session 15

## In plain English
- **New: every model is now compared with the market's own price on the resolution target.**
  - The `res_7d` target asks "will this market resolve YES within 7 days?" The obvious forecast is just the market's
    price. Until now the leaderboard never said whether any model beats it, and that is AREPO's core question.
  - The leaderboard now has a reference row, `market_price_reference` (P(yes) = the market's mid at the forecast
    time). Every model's `res_7d` row also shows its gain over that price, with an event-clustered 95% interval.
  - The reference is a yardstick, not a model. It can never be promoted and does not change K, the promotion rule or
    any existing score.
- **First reading (development stage, 2 days, read-only run on the host, nothing written):** on 34,163 resolution
  rows (3,714 event clusters) the champion's log loss is 0.6139 against 0.6157 for the market price, a gain of
  +0.0018 nats with 95% CI [-0.0001, +0.0035]. **That is level with the price, not a demonstrated improvement.** It is
  forecast quality only: no costs and no fills, and nobody can trade at the mid.
- **The 16 fitted models now predict live.** The 16:31Z and 18:31Z captures used the new 15:44Z fits (16 models,
  up from 11), including the first live predictions of se14, se15, se17, se18 and se19.

## Live state (host)
- **Code:** deployed with merge 339984dc (this session's commit 5a23b261). The scorer change takes effect at the next
  daily score (`q0513`, ~10-23 15:45Z). That run writes the first leaderboard with the reference row; /lab gets it on
  the next push.
- **Refit `q0512`** (10-22): exit 0 in 2,887 s, peak RSS 2,902 MB. Specs: mem_mb 3400, as_cap_mb 6000.
  - `insufficient_coverage` (expected): se8, se9, se10, se16 and se20.
  - LightGBM `res_7d` fits fail ("inner split too small"). This is the known self-healing issue; it should clear
    around 10-28. Until then, only the logistic models have `res_7d` rows and a gain over the market price.
- **Score `q0513`** (10-22): exit 0 in 73 s, peak RSS 589 MB. The read-only run of the new scorer also peaked at
  590 MB, so its as_cap_mb of 3000 still fits.
- **Leaderboard (day 2):** K = 7, champion `se0_champion_lr_mm`, promotion null (under 14 days).
  - se1_lgbm_mm and se7_lgbm_all (ineligible) beat the champion by 0.05-0.07 nats on every direction target.
  - se17 and se18 are not scored yet; their first predictions were at 16:31Z.
- **Queue:** q0512 and q0513 are queued for tomorrow. Nothing on the other track was touched.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se8_lr_event`, `se10_lgbm_event` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-01-23 |

## Changes this session
1. `scoring.py`: `REF_MODEL = "market_price_reference"`. It is scored on `res_7d` from the features file's `ms_mid`,
   adds a `role: "reference"` row per window, and adds `gain_vs_market_mid` to every scored model's `res_7d` row.
2. `dashboard.py`: `_row` carries `gain_vs_mid`, `gain_vs_mid_lo` and `gain_vs_mid_hi`. The reference row passes
   through as `role: "reference"`. The production /lab table already renders rows generically, so it shows the row and
   its gain over the champion. No frontend change.
3. DESIGN_V1 §24 and a ledger entry were added.
4. Tests: test `test_market_price_reference_scores_res_7d_from_the_origin_mid` added. 53 engine tests and 27 lab-client
   tests pass, and ruff is clean.

## Next actions
1. ~10-23 15:45Z: check that q0512 and q0513 ran by themselves, and that `leaderboard/latest.json` has the
   `market_price_reference` rows. Also check that `dashboard.json`'s champion `res_7d` row has `gain_vs_mid`.
2. Optional /lab UI PR: add a "vs market price" column to the res_7d rows, and a one-line explanation of the
   reference row. The data is already in `dashboard.json`.
3. **Before 11-16:** check that LT2's analysis (`q0461`, not before 11-13T12Z) has run. If not, move `flow` later. Do
   the same for `rewards` against E022's analysis before 11-18.
4. Around 10-27/28: se8, se10, se16 and se20 start fitting, and the LightGBM `res_7d` fits should work. That adds
   memory. If the refit's peak RSS passes ~3,300 MB, raise mem_mb, or cap the resolution frame below the direction
   cap. That is a spec change and needs a note.
5. Remaining ideas: CH207 `umaparams` (needs its own census first: the `gamma_rules` frame covers 44.7% of markets),
   CH208-CH211 (all under existing embargo tokens), CH198 `theta`, and `hwm`. Each raises K, so build only those with
   a real prior.
6. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`, plus
   `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0`.

## Notes for the other track
- None new. The earlier `test_registry_experiments_schema` failure (LT7's summary length) was fixed on main in 4da71761.
