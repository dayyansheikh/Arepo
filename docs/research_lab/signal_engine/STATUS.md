# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 11:10 UTC+1 (10:10Z), signal-engine autopilot session 3

## In plain English
- **Three new hidden challengers.** They are LightGBM versions of the flow, time-to-close and cross-venue families:
  `se11_lgbm_flow`, `se12_lgbm_tte` and `se13_lgbm_xvenue`.
  - They use the same learner and settings as `se1`, so each one measures what its family adds on the strong learner.
  - From their first fit they write predictions once, with receipt times. No score is computed or shown until their
    embargo dates: xvenue 11-04, tte 11-14, flow 11-22. They then start with real prospective history.
- **The first daily refit on the server is still queued.** It waits behind the other track's long CPU job (q0475).
  Nothing is broken: the score job runs and is fetching the resolution backlog (about 40,000 markets resolved per day).
- **One known gap that will close by itself.** The LightGBM models cannot fit the resolution target (`res_7d`) yet.
  - A resolution counts as known only from the moment it was fetched, and the whole backlog was first fetched today.
  - The leak-proof validation split therefore has no training rows yet.
  - It should start around 10-28. The rule is correct and stays. The logistic models are not affected.
- Promotion: `se1` can meet the rule after 14 days of prospective scores, around 11-05 at the earliest. Nothing has
  been promoted. No edge claims.

## Live state (host)
- **Code:** deployed `51895a4b` (main checkout `chore/arepo-claude-setup`). The registry loads 14 models on the host.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion) | not embargoed |
| `se1_lgbm_mm` | not embargoed |
| `se7_lgbm_all` (broad) | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-22 |
| `se3_lr_book`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event` | 11-22 |
| `se6_lr_wallet` | 12-07 |

  - Non-embargoed challengers: K = 2 (se1, se7) until 11-04, when se4 and se13 join.
- **Queue:**
  - `q0512` refit: queued, priority 42, behind `q0475` (running since 08:06Z).
  - `q0513` score: daily. Its first leaderboard (07:22Z) was empty: 0 captures scored. Resolutions so far: 39,647
    resolved out of 113,828 due, at 800 requests per day.
  - `q0514` walkforward: priority 35, queued. It skips embargoed models.
- **Refit budget** (Mac copy, development data, 10 days):
  - each extra LightGBM model adds about 110 s;
  - a 5-model refit peaked at 1.28 GB RSS;
  - host estimate: about 3 min per LightGBM model, so 6 LightGBM plus 7 logistic models take about 20–30 min. The
    timeout is 3600 s and mem_mb is 1500.
- **Feature store:** as in session 2. Base: 100 captures. Event aux: 90. Rewards aux: about 88. se8 and se10 first
  fit about 10-27, se9 about 11-04.
- **Development baseline:** unchanged. It is the ledger entry of 2026-10-21 ~08:40Z, where se1 and se7 beat the
  champion by 0.04–0.06 nats on the direction targets. It is development only; the host's `q0514` is the record.

## Changes this session
1. Added `se11_lgbm_flow`, `se12_lgbm_tte` and `se13_lgbm_xvenue`. Each copies its logistic sibling's families,
   derived sets, isolates and sources, with se1's LightGBM params. They are pinned in `specs/registry.json`.
   - Test `test_repo_registry_loads_and_embargo_assignment` was extended. 28 engine tests and 51 lab/signal tests pass;
     ruff is clean.
2. Docs:
   - DESIGN_V1 §18 addendum (the new models, refit timing, the `res_7d` inner-split note);
   - CANDIDATES rows 9–11;
   - a ledger entry ("hidden learner-matched challengers se11-se13").
3. Owner inbox (resize relay) read and archived. The server resizes to 2 OCPU / 12 GB at 2026-10-22 02:40Z. No deploy
   or crontab edits during 02:40–03:45Z.

## Next actions
1. When `q0512` has run, read `logs/fits-*.jsonl` on the host: per-model seconds, total runtime against 3600 s, and
   peak RSS. Then check the next pass tick writes predictions for every fitted model.
   - If the total is over about 40 min, raise the q0512 timeout (job file in `docs/research_lab/queue/jobs/`) before
     adding more models.
2. If the budget allows, add hidden LightGBM versions for `book` and `rewards` (11-22) and `wallet` (12-07). After the
   resize to 2 OCPU this is cheaper.
3. Around 10-28, check that the LightGBM `res_7d` fits start (status `ok` in the fits log).
4. Watch the leaderboard. The first non-empty one should come once the resolution backlog and the first predictions
   overlap.
5. The per-market signal feed for the website comes only after real prospective scores exist.
6. Housekeeping: the merged PR worktree `/Users/DayyanSheikh/Projects/astrolabe-lab-se` can be removed. Its removal
   is still pending approval.

## Conflicts with the other track
- **Queue:** the refit has waited since about 04:30Z behind long CPU-lane jobs (q0474, then q0475). It was not
  re-prioritised. If it is still waiting tomorrow, the owner may want its priority raised. It needs about 20–30 min a day.
- **Merge:** the main checkout had the other track's uncommitted queue-file edits. I waited until they were committed
  and did not touch them. The ledger conflict was resolved by keeping both sides.
- **E005 summary row:** the ledger summary row still says "REGISTERED, pending". Left for the experiments track.
