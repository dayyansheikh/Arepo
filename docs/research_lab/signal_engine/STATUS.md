# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 22:50 UTC+1 (21:50Z), signal-engine autopilot session 16

## In plain English
- **New challenger: "where is the price relative to its own recent highs and lows?"**
  - Until now the models saw only fixed-horizon price changes (1 h, 2 h, 6 h, 24 h, 1 week). They could not see whether
    a market sits right at its highest price of the week, or far below it.
  - The new feature family `hwm` (high-water marks) adds that. For 3-day and 7-day windows of earlier captures it
    records how far the price is below its high and above its low. For 7 days it also records hours since the high
    and since the low, the position within the range, and how much history exists.
  - The idea comes from equities, where prices near their 52-week high behave differently (anchoring). In AREPO it is
    an idea only: there is no evidence yet, development or prospective.
  - The new model `se21_lgbm_hwm` is the same LightGBM as `se1_lgbm_mm` plus this family, so comparing it with se1
    measures the family's effect. One configuration, chosen in advance; nothing was tuned on past results.
- **An independent science review accepted it** (ACCEPT_WITH_FIXES; the fixes were documentation and are applied). It
  found no look-ahead and no shadowing of any registered or drafted live test, so it is not embargoed.
- **It is live on the host.** Its tables are built for every capture. It fits at tomorrow's refit and starts predicting
  from the next capture after that. Like every challenger, it needs 14 days of prospective scores before promotion
  can even be considered.

## Live state (host)
- **Code:** deployed with merge 4f643a62 (this session's commits 95a608ed and the review-fix commit).
- **hwm backfill** (21:46Z, one-off `features --max-items 16`, nice 10): 121 tables in 40 s, peak RSS 578 MB, exit 0,
  no errors. Coverage on the newest capture (20:31Z): 3 d values 87% of eligible markets, 7 d values 79%. Captures
  before ~10-15 have empty 7 d values (no earlier history), as expected. New captures get their table at the pass's tick.
- **Refit `q0512`** (last run 10-22 15:44Z: exit 0 in 2,887 s, peak RSS 2,902 MB; caps mem_mb 3400, as_cap_mb 6000).
  The next run (~10-23 15:44Z) fits se21 too: about +2 min and ~+55 MB. Caps unchanged.
  - Still `insufficient_coverage` (expected): se8, se9, se10, se16 and se20.
  - LightGBM `res_7d` fits fail ("inner split too small (train 0 ...)"). Checked this session: this is data maturity,
    not a bug. Resolution labels count from their fetch time, fetching started recently, so no early-origin row has a
    label before the validation cut yet. It should clear by itself (~10-28).
- **Score `q0513`** (~10-23 15:45Z): the first daily score with the `market_price_reference` rows on `res_7d`
  (DESIGN_V1 §24).
- **Leaderboard (day 2):** K = 7, champion `se0_champion_lr_mm`, promotion null (under 14 days). se1_lgbm_mm and
  se7_lgbm_all (ineligible) beat the champion by 0.05-0.07 nats on every direction target. K rises by one once se21
  is scored.
- **Queue:** q0512 and q0513 are waiting on their daily due-gates (the 20:00Z attempts returned "not due", as intended).
  Nothing on the other track was touched.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se8_lr_event`, `se10_lgbm_event`, **`se21_lgbm_hwm` (new)** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-01-23 |

## Changes this session
1. `aux.py`: family `hwm` (`se-aux-hwm-v1`, `hwm_features`, `_hwm_builder`), from the engine's own quotes files of
   slots k-84..k, same inputs as `surprise`. The shared `SlotMids` cache keeps the larger of the two look-backs.
2. `specs/se21_lgbm_hwm.json` + registry entry (sha af050330...).
3. DESIGN_V1 §25 (with the review, the `surprise` rationale and the departures from CH181 as listed: raw distances,
   not SD units; no explicit new-extreme flag), plus a ledger entry.
4. Tests: `test_hwm_features_hand_example`, `test_hwm_family_reads_only_earlier_quotes`. 55 engine tests and 42 lab
   tests pass, and ruff is clean.

## Next actions
1. ~10-23 15:45Z: check that q0512 fitted se21 (all four targets; `res_7d` will fail like the other LightGBM fits),
   that its peak RSS stays under ~3,300 MB, and that q0513 wrote the `market_price_reference` rows to
   `leaderboard/latest.json` and `gain_vs_mid` to `dashboard.json`'s champion `res_7d` row.
2. ~10-23 16:31Z: check that se21 writes its first predictions at that capture's tick.
3. Optional /lab UI PR: a "vs market price" column on the res_7d rows, and a one-line explanation of the reference
   row. The data reaches `dashboard.json` from the 10-23 score.
4. **Before 11-16:** check that LT2's analysis (`q0461`, not before 11-13T12Z) has run. If not, move `flow` later. Do
   the same for `rewards` against E022's analysis before 11-18.
5. Around 10-27/28: se8, se10, se16 and se20 start fitting, and the LightGBM `res_7d` fits should work. That adds
   memory. If the refit's peak RSS passes ~3,300 MB, raise mem_mb, or cap the resolution frame below the direction
   cap. That is a spec change and needs a note.
6. Remaining ideas: the engine-first ones from creative round 14 (CH217 `rowq`, CH218 `dispgap`, CH219 `bookclock`,
   CH220 dormancy), CH207 `umaparams` (needs its own census first), CH198 `theta`. Each raises K, so build only those
   with a real prior. Do not build `bandbreak`, `pool`, `rwblink` or `rwend` before LT9 fixes its embargo dates.
7. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`, plus
   `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0` (and this session's `/tmp/se_hwm_backfill.log`).

## Notes for the other track
- The one-off hwm backfill ran on the host at 21:46Z for 40 s (578 MB), alongside q0603. No queue job was touched.
