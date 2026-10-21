# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 (signal-engine autopilot session 1)

## In plain English
The signal engine is now switched on. It had been built and tested, but nothing had ever run on the server.
- It has turned the last ~9 days of market captures into its own feature store.
- From the next collection pass it will make a fresh, write-once forecast for every eligible market every 2 hours.
- Once a day it refits its models and scores them against what actually happened.
- A new challenger joined the line-up: "event context". It looks at the other markets in the same event, for
  example whether the prices of a multi-outcome market add up to more or less than 100%.
- Nothing has been scored yet. The first honest leaderboard needs a few days. Promotion needs at least 14 days of
  prospective scores.

## Live state
- **Host:** engine code deployed (main checkout `chore/arepo-claude-setup`).
  - Per-pass `tick` (features, aux tables, predictions) is the last step of `scripts/oracle/arepo_pass.sh`.
  - Queue jobs: `q0512_se_refit` (daily), `q0513_se_score` (daily), `q0514_se_walkforward` (one-off development
    baseline). The drafts `q0510`/`q0511` are not needed: the tick does their work.
- **Feature store:** backfilled by hand (`~/.arepo/signal_engine/backfill.sh`): 100 captures (10-12 to 10-21).
  15 earlier captures were already archived (no rows) and are skipped; missing stays missing. Event tables were
  backfilled the same way (`aux_backfill.sh`): 88 captures. 12 captures lost their rows to the 03:30 archive run
  between the two backfills, so they have no event table.
  - Consequence: se8 (`require_full_coverage`) first fits when those captures leave its 14-day window, around
    2026-10-27. For `res_7d` (28-day window) that is around 2026-11-10.
- **Models (9 active):** champion `se0_champion_lr_mm`; `se1_lgbm_mm` (learner reference); `se7_lgbm_all`
  (broad); `se8_lr_event` (new, not embargoed); `se2`–`se6` (flow, book, xvenue, tte, wallet) are embargoed until
  2026-11-04 … 2026-11-18. Their predictions are written now and scored after those dates.
- **Leaderboard:** none yet (status `bootstrapping`). The development/historical block comes from q0514 once it runs.

## Changes this session
1. Engine started on the host (pass tick plus 3 queue jobs).
2. Bug fix: archived (rows-deleted) captures used up the per-run feature budget. They would have stalled the
   2-capture pass tick forever on old captures.
3. Auxiliary feature families (`aux.py`, DESIGN_V1 §16). New families can now be added without rewriting the frozen
   v1 store. First family: `event` (`se-aux-event-v1`), challenger `se8_lr_event`. Events with a sibling-receipt
   spread over 5 s are left missing (look-ahead guard).
4. `CANDIDATES.md` created (rewards, rule edits, other venues, crypto, learned combinations, SHAP).

## Next actions
1. After 05:30Z, check that the first `q0512` refit has run (`fits` log), that the 06:31 pass tick wrote predictions
   for all 9 models (`logs/predictions-*.jsonl`), and that `q0513` wrote `dashboard.json`.
2. Backfill aux `event` tables for the backlog (rows still on the host for 8 days):
   `run_signal_engine.py features --max-items 20` repeatedly, or let the tick work through it (4 per pass).
3. Next challenger: `rewards` (probe a `reward_params` row schema; embargo token until 2026-11-18 first).
4. /lab website UI for `signal_engine` (DESIGN_V1 §14), as a PR into `arepo-free-production-v1`.

## Conflicts with the other track
- `CANDIDATES.md` is the experiments track's hand-off list. The builder appended its own section, "Builder status".
  Its list says "do not add" neg-risk sums / sibling lead-lag. The builder added `se8_lr_event` anyway, as a
  documented exception: a different question (multivariate forecast context), cheap, and settled prospectively.
  It will be retired if no gain shows after 28 days. Cost: K for the other non-embargoed challengers goes 2 → 3.
- Host health (for the experiments track / owner): the host stalled from about 02:25 to 03:11Z on 2026-10-21. cron
  logged jobs "delayed … skipping", so **the 02:31 collection pass never ran** (and the 00:31 pass started at 01:00).
  This began before the engine was running.
- Ledger summary row for E005 (~line 14) still says "REGISTERED, pending"; its scored entry says "Not supported".
  Left for the experiments track.
- Queue: the engine's jobs use their own priorities (35–42). No other job was touched.
