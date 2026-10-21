# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 21:11 UTC+1 (20:11Z), signal-engine autopilot session 7

## In plain English
- **The promotion rule is now stricter: `se-promotion-v2`.** It is deployed and is the rule in force.
  - Before a challenger can replace the champion, its gain must now be convincing in two ways at once:
    - across separate events (as before);
    - across separate days (new).
  - Why: one news-heavy day can move every market together. The old check would have counted that one day as
    thousands of independent pieces of evidence.
  - It was declared with one scored day. The new check cannot even be computed until there are two scored days.
    No challenger can qualify before 11-04, so no result shaped it.
  - The science review accepted it with small fixes, all applied. Everything else in the rule is unchanged.
- Earlier today (session 6): new challenger `se17_lgbm_mm_900k` (first fit at the ~07:34Z refit on 10-22); the
  `regime` family was tested and dropped; the week-long development walk-forward showed LightGBM ahead of the
  champion every day (development only).
- Nothing has been promoted; that is possible from about 11-04, at the earliest. No edge claims. The UI wording stays
  "signal strength".

## Live state (host)
- **Code:** deployed 2e6e66f (~20:09Z). Host check: `RULE_VERSION` and registry both `se-promotion-v2`, and 18 models load.

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
1. `promotion.py`: `se-promotion-v2`. Condition 2 needs both the v1 event-bootstrap bound and the new two-way bound
   (`cluster_var`, `twoway_bound`). Ties go to the larger two-way bound. `evaluate` refuses when the registry's
   `promotion_rule` differs from the code's rule.
2. `registry.json` `promotion_rule` -> `se-promotion-v2`. No spec changed, and the leaderboard metrics and
   `scoring_version` are unchanged.
3. DESIGN_V1 §7 (v1 superseded) and §20 (v2 declaration), plus a ledger entry. The science review was
   ACCEPT_WITH_FIXES, all applied.
4. Tests: 41 engine tests pass (4 new); ruff is clean.

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
4. Done (v2 is in force). From day 2 on, `leaderboard/latest.json` `promotion.checks.<model>.gain_twoway` shows
   `se_event` vs `se_day`. Note on the dashboard how large the day component is; that is informational only.
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
