# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 15:25 UTC+1 (14:25Z), signal-engine autopilot session 4

## In plain English
- **The engine now runs end to end on the server, apart from the first score.**
  - The first daily refit ran at 11:34Z: 14 models in 42 min, peak memory 1.39 GB.
  - Since then every new capture gets write-once predictions from all fitted models. The 12:31Z capture was the
    first, at about 69 s for 11 models.
  - The daily score job runs next around 03:30Z tomorrow. It should be the first non-empty leaderboard: direction
    targets for the 10-21 captures from 12:31Z on.
- **Two new hidden challengers, `se14_lgbm_movetype` and `se15_lgbm_surprise`.** Both use the same LightGBM settings
  as `se1`, so each is read against `se1`.
- **`se14_lgbm_movetype`.** It asks whether the way a price moved in the last 2 hours helps
  the forecast:
  - through a trade, or by quotes alone;
  - for quote-only moves, both quotes together, one side only, or a spread change;
  - how large the move was against the spread.
  - This comes from the replicated C07 candidate (plus C12).
  - It is embargoed until 11-22 because it shadows the registered live test E015.
- **`se15_lgbm_surprise`.** It asks whether a market's recent volatility, set against its longer-run volatility,
  helps the forecast.
  - It uses 6 h, 3 d and 7 d volatility, their ratios to the 24 h volatility, the largest recent 2 h jump, and the
    weekday and hour (C06).
  - It is embargoed until 11-12 because it shadows E011.
- Both write predictions from tomorrow's refit. No score is computed or shown before their dates.
- **A robustness fix.** If one feature family fails to build, the others and the tick's predictions now carry on.
  Before, one error could stop that pass's predictions.
- **Walk-forward (development baseline) is still running** on the server (started 12:28Z). It writes only at the
  end, so I raised its timeout from 2 h to 3 h for any retry and added a progress line per day.
- Nothing has been promoted. No edge claims. The UI wording stays "signal strength".

## Live state (host)
- **Code:** deployed `bf967fd3` (main checkout `chore/arepo-claude-setup`). The registry loads 16 models on the host.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion) | not embargoed |
| `se1_lgbm_mm` | not embargoed |
| `se7_lgbm_all` (broad) | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se15_lgbm_surprise` | 11-12 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-22 |
| `se3_lr_book`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event`, `se14_lgbm_movetype` | 11-22 |
| `se6_lr_wallet` | 12-07 |

  - Non-embargoed challengers: K = 2 (se1, se7) until 11-04, when se4 and se13 join.
- **First host refit** (`fits-20261021.jsonl`, fit 11:34Z, recorded as "partial"):
  - Every LightGBM `res_7d` fit fails the causal inner split (known; expected to start around 10-28).
  - se8, se9 and se10 are not fitted yet: their aux coverage is incomplete (se8 and se10 around 10-27, se9 around 11-04).
  - Total 2,519 s. Each LightGBM model takes 8.5-10.5 min (LightGBM `num_threads` 1).
  - Expected with se14 and se15: ~62 min, ~72 min once se10 fits (timeout 7200 s). The queue runs one job per CPU
    lane, so the refit holds the lane that long every day.
- **Queue:**
  - `q0512` refit: next due 10-22 ~07:34Z.
  - `q0513` score: tempfails until 20 h after its 07:22Z run, so next ~03:30Z. That is inside the resize window
    (see below), and the queue handles it.
  - `q0514` walk-forward: running since 12:28Z with se0, se1 and se7. Timeout 7200 s for this attempt, 10800 s for
    any retry. Output goes to `dev/walkforward_*.json` and `dev/latest.json`.
- **movetype tables:** 105 written at 14:06Z by a one-off backfill under the collector lock
  (`~/.arepo/signal_engine/aux_backfill_movetype.sh`, log next to it). New captures get theirs in the tick.
  - The family needs no snapshot rows, so se14 can fit at tomorrow's refit (full coverage).
  - Coverage on 10-21 12:31Z: `mt_db` 92%, never-traded 72%. Among 2 h movers: traded 30%, parallel 4.4%,
    one-sided 5.4%. Counts only, no target read.
- **surprise tables:** 105 written at 14:17Z in about 60 s, peak RSS 551 MB (`aux_backfill_surprise.sh`). Coverage:
  rv6h 98%, rv3d 85%, rv7d 78%. The 24 h denominator matches `ms_rv24` to 3e-8.
  - The first attempt hit a MemoryError under the backfill's 2 GB cap, so the cache was rewritten. The live tick has
    no cap and was not affected.

## Changes this session
1. New aux family `movetype` (`se-aux-movetype-v1`) in `aux.py`.
   - It is the first family with `needs_rows: False`: it reads only the engine's own quotes and features files of k
     and k - 1.
   - New embargo token `movetype` (E015, until 11-22).
   - New spec `se14_lgbm_movetype` (isolates `movetype` and `book`), pinned in `registry.json`.
2. `walkforward.py`: one `SE_WALKFORWARD_DAY` progress line per test day. `q0514` timeout raised 7200 -> 10800 s.
3. New aux family `surprise` (`se-aux-surprise-v1`) and spec `se15_lgbm_surprise` (token `surprise`, E011, 11-12).
   - The shared `SlotMids` cache evicts the newest slots and stores numpy arrays.
   - `run_aux` isolates builder errors (`errors` in its result).
4. Tests:
   - hand examples for movetype (every class plus the missing cases) and surprise (windows, ratios, minimum counts,
     older-than-window ignored);
   - builds without snapshot rows;
   - the surprise 24 h denominator equals `ms_rv24`;
   - builder-failure isolation;
   - the registry test was extended;
   - the CLI test's aux budget is now 60 items (4 families x 30 captures).
   33 engine tests pass; ruff is clean.
5. Docs:
   - DESIGN_V1 §8 (token rows) and §16 (third and fourth families, the differences from E015, host coverage);
   - CANDIDATES builder rows 12 and 13;
   - ledger entries for se14 and se15.

## Next actions
1. Tomorrow after the ~07:34Z refit, read `logs/fits-20261022.jsonl`:
   - se14 and se15 should show `ok` on the three direction targets;
   - check the total runtime and peak RSS.
   Then check that the next tick writes se14 and se15 predictions with `aux_sha256`.
2. After the ~03:30Z score run, read `leaderboard/latest.json` and `dashboard.json`:
   - the first non-empty leaderboard should cover se0, se1 and se7 only;
   - check that no embargoed model shows a number.
3. When `q0514` finishes, read `dev/latest.json` (the development baseline on the host), and update the ledger and
   this file. If it timed out, the retry runs with 10800 s; check the `SE_WALKFORWARD_DAY` lines.
4. After the resize (2 OCPU), consider fitting two models in parallel in the refit. LightGBM uses 1 thread, so the
   resize alone does not shorten the refit. That is a code change with a memory check (2 x ~1.3 GB peak).
5. Next candidate families: LightGBM versions of book, rewards and wallet. Settle the refit budget first: 8 LightGBM
   models already take about 70 min of the CPU lane a day.
6. Around 10-28, check that the LightGBM `res_7d` fits start.
7. Housekeeping: the merged PR worktree `/Users/DayyanSheikh/Projects/astrolabe-lab-se` can be removed (still
   pending approval).

## Notes for the other track
- `tests/unit/test_lab_clients.py::test_registry_experiments_schema` fails on the main branch: the LT5 description in
  the experiments registry is 474 characters, over the 450 limit. It is not from this track and was left untouched.
- **Owner resize:** the server resizes to 2 OCPU / 12 GB at 2026-10-22 02:40Z. No deploy or crontab edits during
  02:40–03:45Z.
- **E005 summary row:** the ledger summary row still says "REGISTERED, pending". Left for the experiments track.
