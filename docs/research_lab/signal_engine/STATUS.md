# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 20:35 UTC+1 (19:35Z), signal-engine autopilot session 6

## In plain English
- **The week-long development check finished.** It is a retrospective walk-forward over 10-14 to 10-20: each day's
  models were fitted only on earlier data. It confirms what the first live day showed:
  - The LightGBM models beat the logistic champion on every horizon, every day (7 of 7).
  - At 2 h: `se1` (same inputs as the champion) +0.041 nats, `se7` (all families) +0.046 nats.
  - This is development evidence. It never counts for promotion.
- **New challenger `se17_lgbm_mm_900k` (visible, not embargoed).**
  - It uses the champion's inputs and se1's tree settings, with 3x the training rows and up to 1000 boosting rounds.
  - Why: se1's fits were stopping at their 300-round cap.
  - I tested four learner budgets on development data. Bigger trees and more rounds did nothing. More rows helped a
    little but steadily: +0.0027 nats over se1 at 2 h, and similar at 6 h and 24 h.
  - It was the best of four, so that figure is optimistic. Only the live scores decide.
  - It first fits at tomorrow's ~07:34Z refit, after the server resize.
- **Tested and dropped: a "market activity" family (`regime`).** It measured how many markets were moving, market-wide
  and per category, using only data received before each market's own row.
  - The science review found no leak and no overlap with a live test.
  - On development data it made forecasts slightly worse (-0.0017 nats at 2 h). It only has about 12 distinct values a
    day, so the trees learn noise.
  - The code is removed and nothing was deployed. The result is written down (DESIGN_V1 §19, CANDIDATES row 16) so
    nobody retries it.
- Nothing has been promoted; that is possible from about 11-04, at the earliest. No edge claims. The UI wording stays
  "signal strength".

## Live state (host)
- **Code:** this session deploys the se17 spec and the q0512 job change (see the commit). The registry loads 18 models.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (broad), `se17_lgbm_mm_900k` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se15_lgbm_surprise` | 11-19 |
| `se2_lr_flow`, `se11_lgbm_flow`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event` | 11-22 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book`, `se14_lgbm_movetype` | 12-09 |

  - Non-embargoed challengers: K = 3 (se1, se7, se17) until 11-04.
- **Queue** (all signal-engine jobs at priority 50):
  - `q0512` refit: next ~10-22 07:34Z.
    - Now `timeout_s` 10800 (from 7200) and `mem_mb` 2200 (from 1600).
    - First fits expected: se14, se15 and se17. se16 has no fit until ~10-27 (coverage).
    - Estimate ~85-100 min on 1 thread, including se17's ~18-31 min.
    - The shared direction frame grows to 900k rows. Every other model still draws its own seeded 300k subsample.
  - `q0513` score: ~10-22 11:40Z.
  - `q0514` walk-forward: done (`dev/latest.json`, 10-14..10-20).
- **Prediction tick:** ~65 s of predictions per capture now (11 models). Expect ~150-180 s once se14, se15 and se17
  predict, against the tick's 600 s limit.

## Changes this session
1. New spec `se17_lgbm_mm_900k` (sha `6e27b8c6…`), pinned in `registry.json`, with a registry test.
2. q0512: timeout 7200 -> 10800 s, mem_mb 1600 -> 2200, with a note. No other job changed.
3. Docs:
   - DESIGN_V1 §19: the learner-budget table and the regime dead end.
   - CANDIDATES rows 15 and 16.
   - A ledger entry: the q0514 result, the learner budgets, se17, the regime drop, and the reviewer's note on the
     promotion CI.
4. Tests: 37 engine tests pass; ruff is clean.

## Next actions
1. After the ~07:34Z refit on 10-22, read `logs/fits-20261022.jsonl`:
   - se14, se15 and se17 should be `ok` on the direction targets (se17: check `best_iteration` < 1000 and the seconds);
   - se16 should be `no_fit`;
   - check the total runtime and peak RSS against the new limits.
   Then check that the next tick writes se17 predictions and the tick's duration.
2. After the ~11:40Z score on 10-22, read `leaderboard/latest.json`: day 2, and the first 6 h / 24 h labels.
3. After the resize (2 OCPU / 12 GB), consider:
   - LightGBM `num_threads` 2 in the refit. That is a code change, and the scores differ slightly by thread count, so
     it needs new fits, not new specs.
   - A further rows step (for example 2M rows) if se17 shows a prospective gain over se1.
4. Promotion rule: the science reviewer noted that the event-clustered CI ignores shocks shared by all markets within
   a capture.
   - Draft a `se-promotion-v2` with a day-clustered (or capture-clustered) CI.
   - It must be declared before any challenger nears 14 days, so before ~11-03. Get a science-reviewer pass first.
5. Non-embargoed ideas left: a crypto spot reference is blocked (no stream, and it overlaps CB8 / CB13). Better
   learners on the base inputs are now partly done.
6. Around 10-27, check that se8, se10 and se16 start fitting. Around 10-28, check the LightGBM `res_7d` fits.
7. Housekeeping: the merged PR worktree `/Users/DayyanSheikh/Projects/astrolabe-lab-se` can be removed (still pending
   approval). The Mac scratch copy `/tmp/se_dev` (~410 MB, a copy of host data) can be deleted at any time.

## Notes for the other track
- Owner resize at 2026-10-22 02:40Z: no deploys, crontab edits or queue resumes during 02:40-03:45Z. This session
  deployed before 20:00Z.
- The q0512 refit can now run up to 3 h (from 07:34Z) on one CPU lane. Its priority is unchanged (50).
- If CB17-C's REP_8 slips past 11-23, move `participation` later (never earlier).
