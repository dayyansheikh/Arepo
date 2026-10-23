# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 08:22 UTC+1 (07:22Z), signal-engine autopilot session 20

## In plain English
- **A short housekeeping session.** The experiments track's LT8 census dropped one of its planned tests (CH204, "the
  market's own clock"): too few markets qualified. A dropped test no longer needs its hiding rule, so I removed the
  `sched` embargo token and the one LT8 attribution limit that existed only for it. No model used either, so nothing
  new becomes visible. The rest of LT8's hiding rules (`quietbook`, `swclock`, `book`, `book0`) are unchanged.
- **The engine is healthy on the host.** The signal feed was rebuilt from the 06:31Z capture, every model wrote its
  predictions at 07:00Z, and the daily refit (q0512) and score (q0513) are waiting for their usual afternoon times.
- **Memory check before today's refit.** Today's refit fits three new challengers (se21-se23) for the first time.
  Training frames have a fixed row cap (~900k rows; the last refit used 892k at a 2.9 GB peak), so the extra columns
  should add only ~100 MB, under the 3.4 GB cap.
- Session 19 (03:55Z-05:14Z) applied LT10 round 7 (`kxbook`, `attrlimit_lt10`, second cross-venue read root) and hit
  the usage limit before it could rewrite this file; that work is merged and live (ledger "LT10 round 7 applied").
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** deployed with merge 88ec8a05 (chore/arepo-claude-setup).
- **Feed:** `signal_engine/feed/latest.json` (`se-feed-v1`, ~16 KB) is rebuilt by the tick when the champion has a
  newer prediction. Titles are cached in `feed/titles.json` (one Gamma request per new capture, at most 60 ids).
- **Refit `q0512`** (next ~10-23 15:44Z; caps mem_mb 3400, as_cap_mb 6000) fits se21, se22 and se23 for the first time.
  - Still `insufficient_coverage` (expected): se8, se9, se10, se16 and se20.
  - The LightGBM `res_7d` fits fail for label maturity (expected to clear ~10-28).
- **Score `q0513`** (~10-23 15:45Z): the first daily score with `market_price_reference` rows on `res_7d`.
- **Leaderboard** (10-22, 2 days scored): the LightGBM challengers lead the logistic champion by ~0.05 nats on every
  direction target (se1 dir_2h +0.051, event-clustered CI +0.049..+0.052). That is a learner effect. The two-way
  (event + day) bound is still negative with 2 days, and no promotion is possible before ~11-04 (14-day minimum).
  K = 7. Champion `se0_champion_lr_mm`.
- **Queue:** q0512 and q0513 are in `retry_wait` on their daily due-gates (normal). Nothing on the other track was
  touched (q0116h `retry_wait`; q0623 re-prioritised by that track).

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
1. `config.EMBARGO`: `sched` withdrawn (`until` = `withdrawn_utc` = 2026-10-23T07:30:00Z, `until_before` 2027-01-23).
   `attrlimit_lt8` drops the per-market slot-of-day limit and `sched` from `no_broad_families` and keeps both under
   `withdrawn`. Its date is unchanged. DESIGN_V1 section 8 table, CANDIDATES reply, ledger "Signal engine: LT8 `sched`
   withdrawn". Commit 7fe05328.
2. Tests: new `test_lt8_sched_withdrawn_after_ch204_census_drop`. 65 engine tests pass and ruff is clean.
3. Merged into `chore/arepo-claude-setup` (88ec8a05) and deployed. The host's config shows `sched` until 07:30Z.

## Next actions
1. ~10-23 15:45Z: check that q0512 fitted se21, se22 and se23 on the direction targets (`res_7d` LightGBM fits
   expected to fail), that the peak RSS stays under ~3,300 MB, and that q0513 wrote the `market_price_reference` rows.
2. ~10-23 16:31Z: check that se21, se22 and se23 write their first predictions; se22 and se23 show only
   `embargoed_until`.
3. Feed:
   - Watch `feed_error` / `titles_error` in the `SE_TICK` lines.
   - After a promotion, check that the feed switches to the new champion at its next prediction.
   - Possible v2, needing the owner and a design note: a feed column with the champion's calibration per strength
     band, so users see how often strong signals moved.
4. Optional /lab UI: a "vs market price" column on the res_7d rows, once the 10-23 score puts it in `dashboard.json`.
5. **Before 11-14:** check that LT2's analysis (`q0461`, not before 11-13T12Z) has run. If not, move `tte`,
   `chg1d_x_liq` and `dispgap` later, and `flow` before 11-16. Do the same for `rewards` against E022's analysis
   before 11-18.
6. **If CH214 drops at LT9's census (11-02..11-12):** withdraw the `book` / `book0` extension back to 2027-01-23, with a
   ledger line. **If CH215 enters:** add the `rwend` token to 2027-02-14.
7. Around 10-27/28: se8, se10, se16 and se20 start fitting, and the `res_7d` LightGBM fits should work. Watch the
   refit peak RSS.
8. Remaining family ideas, only with a real prior: CH217 `rowq`, CH219 `bookclock` (hidden to 2027-02-14), CH207
   `umaparams` (needs a census), CH198 `theta`. The LT7 tokens are free since 10-23 (resist, capath, deepbook,
   absorbed, ivr). `resist` (CH195) passed every census gate except the F-MDE, so it is the most plausible engine
   family of the five; check for LT8 `quietbook` overlap first.
9. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`,
   `/tmp/se_dev`, `/tmp/se_e2e`, the host's `/tmp/se_b0`, `/tmp/se_hwm_backfill.log` and `/tmp/se_dg_dm_backfill.log`.
   This session's PR worktree and its temporary files are already removed.

## Notes for the other track
- No embargo, token or queue change this session. The feed shows only the champion (`se0`, not embargoed). If a
  broad model is ever promoted, the feed shows it (as the leaderboard does). Raise it in CANDIDATES if a live test
  needs the feed hidden.
