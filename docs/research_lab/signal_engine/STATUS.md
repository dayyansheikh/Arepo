# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 ~13:15Z, signal-engine autopilot session 23

## In plain English
- **A new signal family went in: `tilt` (CH235, "collateral tilt").** On Polymarket the price of a share is the money
  you put up for it, so cheap-side quotes, fees and rebates have shapes the champion's straight-line model cannot see.
  The family adds five such columns: cheap-side price, which side is cheap, the market's own taker fee and maker rebate
  per share, and spread over the cheap-side price. Two new challengers use them: `se24_lgbm_tilt` (read against se1)
  and `se25_lr_tilt` (read against the champion). Both are visible and start at today's refit if the backfill finishes.
- **One column was held back on purpose.** CH234's "who paid how much for the move" weight is the lead test of the
  other track's LT11 draft, which asks the engine not to score it before LT11 is frozen. A first version, never
  deployed, hid it behind a temporary embargo. The final version simply leaves it out.
- **One idea was killed by its own counting rule.** CH237 (`parentsib`, the parent event's other markets): only 0.15% of
  eligible non-sports markets have a parent event. Its kill line was 5%, so no family was built.
- **The leaderboard (3 days scored, 10-23 12:16Z):** the LightGBM challengers still beat the logistic champion by about
  0.045 nats on dir_2h. se1's two-way (event + day) lower bound turned positive (+0.020) for the first time. That is a
  learner effect, not an edge. No promotion is possible before ~11-04 (14-day minimum).
- Two independent science reviews, both ACCEPT_WITH_FIXES. All the fixes were applied, and none was a leakage issue.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** deployed b55a5281 (chore/arepo-claude-setup) at ~13:05Z.
- **Backfill:** `~/.arepo/signal_engine/aux_backfill_tilt.sh` (log `aux_backfill_tilt.log`) builds the `tilt` tables
  for every processed capture in small batches outside the pass windows. se24/se25 need every labelled capture of their
  window to have the table (`require_full_coverage`). If the backfill is not complete by the 15:44Z refit, they first
  fit at the 10-24 refit.
- **Refit `q0512`** (~10-23 15:44Z; caps mem_mb 3400, as_cap_mb 6000):
  - Fits se21, se22, se23 (and se24, se25 if the backfill is done) for the first time. Peak RSS is to be watched.
  - Still `insufficient_coverage` (expected): se8, se9, se10, se16 and se20.
  - The `res_7d` LightGBM fits fail for label maturity (expected to clear ~10-28).
- **Score `q0513`** ran at 10-23 12:16Z: 3 days scored, K = 8 (it becomes 10 once se24/se25 have scores).
- **Feed:** `signal_engine/feed/latest.json` (champion only), rebuilt by the tick.
- **Queue:** q0512 and q0513 are on their daily due-gates (normal). Nothing on the other track was touched.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, **`se24_lgbm_tilt`, `se25_lr_tilt` (new)** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. `tilt` aux family (`se-aux-tilt-v1`, DESIGN_V1 §29), specs se24/se25 and registry entries, tests
   (`test_tilt_features_hand_example`, `test_tilt_reads_only_its_own_capture`, registry asserts). 68 engine tests pass;
   ruff clean.
2. Counts-only checks (no outcomes read), both on capture 10-23 10:31Z:
   - CH237: 27 of 18,349 eligible non-sports rows have a parent, so the family is killed.
   - Fee schedules are present on 98.1% of eligible rows.
3. CANDIDATES rows 24/25, a reply to the experiments side, and a ledger entry. The checkpoint line was rewritten.

## Next actions
1. Check the backfill log: `tables` should reach the number of feature captures (~128+).
2. ~10-23 15:45Z: check q0512.
   - se21–se23 (and se24/se25) should fit on the direction targets.
   - Peak RSS should stay under ~3,300 MB.
   - Then ~16:31Z: their first predictions.
3. **At LT11's freeze:** apply `dollarw`, `nrslack`, `bandside` and `attrlimit_lt11`. Make sure `attrlimit_lt11` lists
   se24/se25 (requested in CANDIDATES). A `tl_w2h` / `tl_w_traded` version of `tilt` comes only after the freeze,
   under `dollarw` if CH234 registers.
4. **Before 11-14:** check that LT2's analysis (q0461) has run. If it has not, move `tte`, `chg1d_x_liq` and `dispgap`
   later, and `flow` before 11-16. Do the same for `rewards` against E022 before 11-18.
5. **If CH214 drops at LT9's census:** `book` / `book0` need a new date by ledger line.
6. Around 10-27/28, se8, se10, se16 and se20 start fitting and the `res_7d` LightGBM fits should work.
7. Remaining ideas, only with a real prior:
   - `ruleclass` (CH239, res_7d first);
   - `nrslack` levels inside `event` (CH238);
   - `volage` after 11-22;
   - CH217 `rowq`;
   - CH207 `umaparams`.
8. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`, plus the
   `/tmp/se_*` scratch on the Mac and the host and the old backfill logs.

## Notes for the other track
- LT11 section 9's pre-freeze hold is followed: no engine family holds `tl_w2h`, a weight × move product, a sibling
  bid/ask-sum change or a 0.10/0.90 crossing indicator. The `tilt` level columns are built, as section 9 allows.
- The deploy pulled 5 host trial rows into the main checkout's `trials.jsonl` (the deploy script's normal union). They
  are left uncommitted for that track's next commit.
