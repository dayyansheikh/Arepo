# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 02:52 UTC+1 (01:52Z), signal-engine autopilot session 10

## In plain English
- **The order-book signal is back, without the timing flaw.**
  - Last session found that the `book` features were read about 7 minutes after the price that the forecasts are
    scored from. It locked the models that use them out of promotion.
  - This session added `book0`: the same book measurements, taken from the last book sweep that finished *before*
    the capture. That is normally the previous pass, about 110 minutes earlier, so it cannot see the move being scored.
  - Coverage is 93% of eligible markets.
- **New challenger `se18_lgbm_all_b0`**: the broad "everything" model, rebuilt on `book0`. It replaces se7 as the
  broad model that is allowed to become champion.
  - Adding it makes the promotion bar slightly stricter for everyone (K goes from 3 to 4).
  - `se19_lr_book0` (book0 on its own) is hidden until 12-31, like the other book models, because live tests use book data.
- The science review accepted it with fixes. No leakage was found, and all fixes are applied. The change is deployed and
  all past book0 tables are built.
- Nothing has been promoted yet. The earliest possible date is about 11-04 for se1/se17; se18 needs 14 days from its
  first prediction (about 11-05). No edge claims; the UI wording stays "signal strength".

## Live state (host)
- **Code:** deployed 487d2cbe (~01:47Z). The host loads 20 models; the rule is `se-promotion-v2`.
- **book0 backfill (01:49-01:50Z):** 111/111 captures have a table, with median coverage 92.7%. Peak RSS was 330 MB.
  - Three captures have no pass sweep within 3 h, so they stay NaN: the first capture (10-12 04:31Z) and two
    collection gaps (10-14 12:31Z, 10-21 04:31Z).
  - These tables are training inputs only. Nothing is predicted for past captures.
  - Script: `~/.arepo/signal_engine/aux_backfill_book0.sh` (log next to it).
- **Promotion-eligible non-embargoed challengers:** se1, se17 and se18 (from its first fit). K = 4: se1, se7, se17,
  se18 (se7 still counts but is ineligible).

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se17_lgbm_mm_900k`, **`se18_lgbm_all_b0`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se15_lgbm_surprise` | 11-19 |
| `se2_lr_flow`, `se11_lgbm_flow`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event` | 11-22 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), **`se19_lr_book0`** | 12-31 |

  - Tokens with no model yet: `chg1d_x_liq` (11-14), `hollow` (11-18), `wallet_skill` (12-07), `vote`, `clips`,
    `deadline`, `siblings` (12-09), and `resist`, `capath`, `mm_fresh`, `deepbook`, `absorbed`, `ivr` (12-31).
  - New token `book0` (12-31): same tests as `book`. It also hides book0 in se18's family attribution.
- **Queue:** `q0512` refit is due ~10-22 07:34Z. It is the first fit for se14, se15, se17, se18 and se19 (se18 adds
  ~10 min on 1 OCPU). `q0513` score is due ~11:40Z. No jobs were touched.

## Changes this session
1. `aux.py`: family `book0` (`se-aux-book0-v1`; `prior_sweep`, `book0_features`), with provenance in the table metadata.
   `features.py`: `book_features` split into `read_sweep_book` + `book_columns` (output unchanged).
2. Specs `se18_lgbm_all_b0` and `se19_lr_book0`, the registry entries, the EMBARGO token `book0`, and DESIGN_V1
   §22 (with the §8 row and a §21 pointer).
   - Disclosures: the se7 − se18 contrast; the columns and specs were written before the development diagnostic was seen.
3. Tests: 46 engine tests pass, including 2 new book0 tests and extended registry asserts. Ruff is clean.
4. Science review: ACCEPT_WITH_FIXES. Applied: only pass sweeps of indexed captures are used and `.tmp_` folders are
   skipped; sweep provenance is recorded; the wording and disclosures are fixed; the backfill is labelled as training
   input only.
5. CANDIDATES builder row 19, and a ledger entry.

## Next actions
1. After the ~07:34Z refit, read `logs/fits-20261022.jsonl`:
   - Expect se14, se15, se17, se18 and se19 `ok`, and se16 `no_fit`.
   - Check that the total runtime is under 10800 s and peak RSS under 2200 MB. se18 and se19 need
     `require_full_coverage`; all 111 tables exist.
   - Then check that the next tick writes se18 predictions.
2. After the ~11:40Z score: check day 2 of `leaderboard/latest.json` and the `dashboard.json` `promotion` block. Expect
   K = 4, because K counts every active non-embargoed challenger, even one with no scores yet. se18 will fail check 1
   (age) until about 11-05. Check that se7 shows `eligible: false`.
3. After the owner's resize (still 1 OCPU at 01:30Z): LightGBM `num_threads` 2, then the learner-matched
   `se20_lgbm_book0` (embargoed 12-31), and perhaps se18 at 900k rows.
4. Around 10-27: se8, se10 and se16 start fitting. Around 10-28: the LightGBM `res_7d` fits.
5. Remaining ideas: CH198 `theta`, CH201 rewards-v2 (check it against §21 and §22 first).
6. Housekeeping (needs approval): remove the merged worktrees `/Users/DayyanSheikh/Projects/astrolabe-lab-se` and
   `astrolabe-lab-se-promo`, plus `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0` (scratch diagnostic copy).

## Notes for the other track
- `book0` is embargoed with `book` (same tests, 12-31). The visible broad models se7 and se18 differ only in their
  book input (sweep 1 against the previous pass's sweep). That contrast is disclosed in DESIGN_V1 §22 (science review:
  acceptable, since se7's post-origin overlap dominates it). If LT6 V or LT7 need it hidden, say so and se18's rows can be
  embargoed.
- No queue jobs were touched. The main checkout's `trials.jsonl` has uncommitted changes from your side; I left them alone.
