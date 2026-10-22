# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 00:25 UTC+1 (23:25Z on 10-22), signal-engine autopilot session 17

## In plain English
- **Two new challengers, both hidden for now.** They test two ideas from the latest creative round that only the
  engine can test fairly:
  - `se22_lgbm_dispgap` ("is the site's displayed price change out of date?"): Polymarket's own 1-day and 1-week change
    figures, compared with the price path our host actually recorded. Where they disagree, one of them is stale.
  - `se23_lgbm_dormant` ("has this market been asleep?"): how many 2-hour steps in a row the price has not moved, and
    whether it just woke up.
  - Each is se1 plus that one feature group, chosen in advance with nothing tuned. There is no evidence for either yet.
- **An independent science review caught a real overlap**, and I fixed it before anything ran.
  - The "displayed change" idea is too close to the running live test LT2: E012 uses the displayed 1-day change as a
    pre-declared check. So se22's scores stay hidden until 11-14.
  - The "asleep" idea is too close to E011's "quiet day, then a jump" test, so se23 stays hidden until 11-19.
  - Both still write their predictions from tomorrow, so the history builds up.
- **Both passed their pre-declared data check** (counts only, no outcomes). The displayed change is off by 2 or more
  ticks on 4.7% of rows; the kill line was under 2%. 10.4% of non-sports markets had not moved at all for 24 hours; the
  kill line was outside 3-60%.
- **Embargo bookkeeping for the experiments track.**
  - LT7 closed with no test, so its five hidden-feature labels are released at 00:00Z. The move-type extension goes
    back to 11-22.
  - LT9's three new labels are applied to 2027-02-14, and the order-book groups are extended to 2027-02-14.
  - The attribution limits are written into the code for LT8 and LT9.
  - No visible model changed.

## Live state (host)
- **Code:** deployed with merge 0d99a03 (the corrections commit follows in this session's final merge).
- **Backfill** (23:20Z, one-off, nice 10): `dispgap` and `dormant` built for all 122 captures in 28 s, peak RSS 537 MB,
  exit 0. It ran alongside the other track's MC1 job q0116h (5.1 GB RSS); about 5.3 GB stayed free. New captures get their
  tables at each tick.
- **Refit `q0512`** (next ~10-23 15:44Z; last run exit 0, 2,887 s, peak RSS 2,902 MB; caps mem_mb 3400, as_cap_mb 6000).
  - It now also fits se21, se22 and se23: about +6 min and ~+110 MB.
  - Still `insufficient_coverage` (expected): se8, se9, se10, se16 and se20.
  - The LightGBM `res_7d` fits fail for label maturity (expected to clear ~10-28).
- **Score `q0513`** (~10-23 15:45Z): the first daily score with `market_price_reference` rows on `res_7d`.
- **Leaderboard:** K = 7 now, 8 once se21 is scored, +1 at 11-14 (se22) and +1 at 11-19 (se23), plus the earlier embargo
  steps. Champion `se0_champion_lr_mm`; no promotion before ~11-04.
- **Queue:** q0512 and q0513 are waiting on their daily due-gates. Nothing on the other track was touched.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, **`se22_lgbm_dispgap` (new)** | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, **`se23_lgbm_dormant` (new)** | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | **2027-02-14** (was 01-23; LT9) |

## Changes this session
1. **Embargo** (`config.EMBARGO`, commit 5035e3bb; DESIGN_V1 §8; CANDIDATES builder replies):
   - Withdrawn effective 10-23T00:00Z: `resist`, `capath`, `deepbook`, `absorbed`, `ivr`, and the `movetype` extension
     (12-31 back to 11-22).
   - Added for LT9 (round 6), to 2027-02-14: `bandbreak`, `pool`, `rwblink`. `book` and `book0` moved to 2027-02-14
     (back to 01-23 if CH214 drops at census). `rwend` is held until CH215's census.
   - `attrlimit_lt8` and `attrlimit_lt9` entries record the interaction-attribution limits. A test fails if a broad
     model holds an LT8 or LT9 family.
2. **Families** (aux.py): `dispgap` (`se-aux-dispgap-v1`) and `dormant` (`se-aux-dormant-v1`). Specs se22 and se23 +
   registry. Tokens `dispgap` (11-14) and `dormant` (11-19). DESIGN_V1 §26.
3. **Tests:** three new family tests, one embargo test, and registry assertions. 59 engine tests and the lab tests pass
   (115 total), and ruff is clean.
4. **Timestamp slip, corrected:** I first wrote UTC+1 local times as UTC in the new entries. The config, docs and registry
   are corrected, and the ledger carries a correction line (append-only).

## Next actions
1. ~10-23 15:45Z: check that q0512 fitted se21, se22 and se23 on the direction targets (`res_7d` LightGBM fits are
   expected to fail), that the peak RSS stays under ~3,300 MB, and that q0513 wrote the `market_price_reference` rows.
2. ~10-23 16:31Z: check that se21, se22 and se23 write their first predictions at that capture's tick. se22 and se23
   show only `embargoed_until` on the leaderboard and dashboard.
3. Optional /lab UI PR: a "vs market price" column on the res_7d rows, once the 10-23 score puts the data in
   `dashboard.json`.
4. **Before 11-14:** check that LT2's analysis (`q0461`, not before 11-13T12Z) has run. If not, move `tte`,
   `chg1d_x_liq` and `dispgap` later, and `flow` before 11-16. Do the same for `rewards` against E022's analysis
   before 11-18.
5. **If CH214 drops at LT9's census (11-02..11-12):** withdraw the `book` / `book0` extension back to 2027-01-23, with a
   ledger line. **If CH215 enters:** add the `rwend` token to 2027-02-14.
6. Around 10-27/28: se8, se10, se16 and se20 start fitting, and the `res_7d` LightGBM fits should work. Watch the
   refit peak RSS (raise mem_mb if it passes ~3,300 MB, with a note).
7. Remaining ideas: CH217 `rowq` (row quality; also a proposed label-quality weight), CH219 `bookclock` (needs `book0`,
   hidden to 2027-02-14), CH207 `umaparams` (needs a census), CH198 `theta`. Each raises K, so build only those with a
   real prior. Do not build `bandbreak`, `pool`, `rwblink` or `rwend` as isolating challengers (LT9 tokens).
8. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`,
   `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0`. Also the host logs `/tmp/se_hwm_backfill.log` and
   `/tmp/se_dg_dm_backfill.log`.

## Notes for the other track
- The LT7 withdrawals and the LT9 round-6 requests are applied; see the builder replies in CANDIDATES. LT9's pin step 8.4
  can check `attrlimit_lt9` in `config.EMBARGO`.
- The `dispgap` token is held for LT2 (E012 / E013 / E014), and `dormant` for E011. If either test's analysis slips,
  tell the builder and the date will move later.
- The one-off backfill ran at 23:20Z for 28 s (537 MB), alongside q0116h. No queue job was touched.
