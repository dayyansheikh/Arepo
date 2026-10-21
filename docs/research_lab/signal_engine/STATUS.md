# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 10:20 UTC+1 (09:20Z), signal-engine autopilot session 2

## In plain English
- **The website now has a signal-engine section.** The owner's /lab page shows the champion, the challengers and
  their forecast-quality scores. PR #23 was merged into `arepo-free-production-v1` and the Vercel deploy is READY.
  - Models that shadow a live test show only "embargoed until <date>", never numbers. The site enforces this itself
    as well.
  - It reads "bootstrapping" until scores exist.
- **The engine works end to end, but the first daily refit is still queued.** On a copy of the server's data:
  - the refit took 6 min at a peak of 1.1 GB;
  - prediction writing worked for every model that had a fit.
  The refit has waited since about 04:30Z behind the other track's long CPU jobs (q0474 ran 3.7 h; q0475 started
  08:06Z). Nothing is broken. The first predictions follow the first refit.
- **First development reading** (historical walk-forward, 7 test days; NOT prospective, no edge claim):
  - The LightGBM learner on the same inputs as the champion (`se1`) beats the logistic champion on every direction
    target, by 0.04 to 0.05 nats of log loss. Every day was positive.
  - The broad LightGBM (`se7`) adds a little more.
  - Most of the near-term gain is the learner, not new information. `se1` is the likely first promotion once it has
    14 days of prospective scores.
- **New challenger `se10_lgbm_event`:** LightGBM plus event context. A family must be tested on the strong learner,
  because the logistic version tells us little once a LightGBM model is champion (DESIGN_V1 §18).
- **Embargoes extended on the experiments track's request.** Dates only move later.
  - `event` is a new token. It now covers se8 and se10.
  - flow, book and rewards: until 2026-11-22.
  - wallet, plus a new `wallet_skill` token: until 2026-12-07.
  - No event score had ever been computed or shown.
- **Rewards tables backfilled** on the server for 85 older captures, before their raw rows are archived.

## Live state (host)
- **Code:** deployed `38c13996` (main checkout `chore/arepo-claude-setup`).
- **Registry:** 11 models.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion) | not embargoed |
| `se1_lgbm_mm` | not embargoed |
| `se7_lgbm_all` | not embargoed |
| `se4_lr_xvenue` | 11-04 |
| `se5_lr_tte` | 11-14 |
| `se2_lr_flow` | 11-22 |
| `se3_lr_book` | 11-22 |
| `se8_lr_event` | 11-22 |
| `se9_lr_rewards` | 11-22 |
| `se10_lgbm_event` | 11-22 |
| `se6_lr_wallet` | 12-07 |

  - Non-embargoed challengers: K = 2 (se1, se7) until 11-04.
- **Queue:**
  - `q0512` refit: queued, priority 42. It runs after `q0475` frees the CPU lane, probably around 11:50Z.
  - `q0513` score: daily. First leaderboard written 07:22Z, empty: 0 captures scored, resolution backlog being
    fetched (800 requests/day).
  - `q0514` walkforward: priority 35, queued.
- **Feature store:**
  - Base: 100 captures.
  - `event` aux: 90 captures.
  - `rewards` aux: about 88 captures.
  - 12 (event) or 24 (rewards) captures are unbuildable because their rows were archived. Missing stays missing.
  - se8 and se10 first fit about 10-27 (`require_full_coverage`). se9 first fits about 11-04.
- **Development baseline** from the Mac run, test days 10-14 to 10-20, gain vs the champion with 95% CI:

| Model | dir_2h | dir_6h | dir_24h |
|---|---|---|---|
| se1 | +0.041 [0.040, 0.042] | +0.054 | +0.051 |
| se7 | +0.046 | +0.061 | +0.058 |

  The full numbers are in the ledger entry of 2026-10-21 ~08:40Z. The host's `q0514` remains the record.

## Changes this session
1. `/lab` signal-engine section: PR #23 merged (merge commit a48ed8c9). Validation:
   - frontend: 198 unit tests passed; tsc, lint and build OK;
   - e2e: 115 of 117 passed. One failure is the replay test "still being collected", which fails identically on the
     unmodified production base (local-DB dependent). The other was the new lab test's first version, which has
     since been fixed (11 of 11 lab e2e tests pass).
   - backend: 80 lab tests passed.
2. `se10_lgbm_event` spec and registry entry, plus a test. DESIGN_V1 §18 (learner-matched family challengers).
3. Embargo requests applied in `config.EMBARGO`. Tests, DESIGN_V1 §8 and §16, and CANDIDATES rows updated.
4. Rewards aux backfill on the host (`~/.arepo/signal_engine/aux_backfill.sh`, niced, 2 GB cap).
5. Ledger: two signal-engine entries (development look + se10; embargo application).

## Next actions
1. After `q0512` runs, check the fits log (`logs/fits-*.jsonl`): runtime under the 3600 s timeout, and peak RSS.
   The next pass tick should write predictions for se0, se1, se7 and the embargoed logistic models.
   - If the host refit takes more than about 30 min, consider raising q0512's timeout before adding more LightGBM
     models.
2. If the refit time allows, add LightGBM versions of the embargoed families as hidden predictions under their
   tokens (DESIGN_V1 §18), so they have history when their embargoes lift:
   - `flow` first (C01, the highest-priority candidate);
   - then `tte` and `xvenue`.
   Measure refit time per added model first.
3. Watch the leaderboard. se1 can meet the promotion rule after 14 days of prospective scores, around 11-05 at the
   earliest.
4. The per-market signal feed for the website: only after the leaderboard has real prospective scores.
5. Housekeeping: the merged PR worktree `/Users/DayyanSheikh/Projects/astrolabe-lab-se` can be removed. Removal
   needed approval this session.

## Conflicts with the other track
- **Queue:** the engine's daily refit waits behind long CPU-lane jobs (q0474, q0475). It was not re-prioritised. If
  this keeps delaying the refit by more than about 12 h, the owner may want the refit's priority raised. It is about
  15 min a day.
- **Ledger:** append-only conflict resolved by keeping both sides.
- **E005 summary row:** the ledger summary row for E005 still says "REGISTERED, pending". Left for the experiments
  track.
