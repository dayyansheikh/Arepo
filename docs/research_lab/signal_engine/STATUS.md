# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-23 04:05 UTC+1 (03:05Z), signal-engine autopilot session 18

## In plain English
- **The engine now publishes its signals, market by market (owner's /lab only).** After every capture, the engine
  takes the current champion's stored forecast and lists the markets it calls most strongly up and most strongly
  down. Each entry has the market title, a Polymarket link, price, spread and a "signal strength" for 2 h, 6 h and
  24 h. Strength runs from -1 to +1 and means P(up) minus P(down).
  - Next to the lists is the champion's own scored record (forecast quality, not profit).
  - It never shows a model hidden for a live test, and it recomputes nothing: it reads back the write-once
    prediction and its receipt time.
- **A display fix I made before anyone saw it.** The first build put 2-3c longshots with 3-5c spreads at the top.
  On such markets a strong "signal" mostly reflects how the quotes move inside the spread, not anything a user could
  act on. So only markets with a spread of 2c or less and a price between 5c and 95c are ranked (17,013 of ~54,000
  at 00:31Z). This choice was declared before any outcome was read; the model itself is unchanged.
- **Working end to end on the host.** The 02:31Z capture's tick rebuilt the feed by itself at 03:01:51Z: 17,403
  markets in the pool, all 40 listed markets titled. The /lab push carries it (snapshot 127 KB to 142 KB).
- **Web page:** the "Signal feed (champion)" panel is now live on /lab. PR #28
  (https://github.com/dayyansheikh/Arepo/pull/28) was merged by me at ~03:23Z, and the Vercel deploy succeeded.
- Not done, and needing the owner: a public website version of the feed. The North Star asks for an owner-approved
  web deploy, and its wording needs a review.

## Live state (host)
- **Code:** deployed with merge 7d7d0e0b (chore/arepo-claude-setup).
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
- **Queue:** q0512 and q0513 are waiting on their daily due-gates. Nothing on the other track was touched; its MC1
  job q0116h was running (exclusive) throughout.

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
1. `signal_engine/signal_feed.py` (new), schema `se-feed-v1`, DESIGN_V1 §27. `run_signal_engine.py tick` builds
   it; the tick's exit code is unchanged, and `--no-feed-titles` skips the lookup. `lab_host.build_signal_feed`
   embeds it as `signal_engine.feed` after re-checking the champion and its embargo. It is stale after 6 h, and it is
   the first thing dropped when the snapshot is too big.
2. Display pool (spread <= 2c, mid 0.05-0.95), declared 10-23 ~02:45Z after the first host build. Commit 9058f2dd.
3. Tests: 3 new feed tests. 62 engine tests and 56 lab tests pass, and ruff is clean.
4. PR #28 (`feat/lab-se-feed`, /lab UI):
   - It adds the parser and panel. The parser keeps the champion only, re-checks the embargo and fails closed, keeps
     only polymarket.com links, and never throws.
   - Validation: 234 unit tests, tsc, lint and build pass. The full e2e ran against a local API on a /tmp copy of the
     preserved `backend/astrolabe.db`: 120 of 121 pass. The one failure, `replay.spec.ts:58`, depends on the date: the
     preserved cohort's 7-day horizon is now overdue, and replay is untouched by this PR.
   - **MERGED** 2026-10-23 ~03:23Z (merge 2842fd1f) under the owner exception. Vercel succeeded,
     www.arepolabs.com/lab returned 200 and the API health was OK.

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
