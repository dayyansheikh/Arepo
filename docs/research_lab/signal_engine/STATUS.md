# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-21 17:20 UTC+1 (16:20Z), signal-engine autopilot session 5

## In plain English
- **The engine now runs fully end to end on the server, scoring included.** The owner asked (Lab board, 14:01Z) for
  the signal engine to jump the server queue. Two changes:
  - The signal-engine jobs now have priority 50. They start ahead of every experiment job except three time-bound
    recorders, which would lose data if delayed (q0083b, q0162, q0163). Tonight's exclusive LT5 census q0561 (priority
    60) still goes first, as it must.
  - A one-off early score job (`q0515`) ran at 15:38Z, so the first real leaderboard did not have to wait for
    tomorrow's 03:30Z run, which falls inside the server-resize window.
- **First prospective leaderboard (one 2 h scoring window, one day: a pipeline check, not evidence):**

  | Model | 2 h direction log loss (lower is better) | AUC |
  |---|---|---|
  | `se0` champion (logistic, momentum + market state) | 0.4405 | 0.787 |
  | `se1_lgbm_mm` (same features, LightGBM) | 0.391 | 0.844 |
  | `se7_lgbm_all` (all families) | 0.387 | 0.849 |

  - 49,154 markets, all predictions on time.
  - se1's gain over the champion is 0.049 nats (event-clustered CI 0.046-0.053). This matches the development
    walk-forward.
  - Promotion needs at least 14 scored days, so nothing can be promoted before about 11-04.
  - Every embargoed model shows only its date.
- **New hidden challenger `se16_lgbm_participation`.** It asks whether event-level participation helps the forecast:
  - the event's total volume and its 2 h change;
  - event liquidity and the market's share of it;
  - Gamma's "competitive" score, the event's age and the market's lifetime volume.
  - Event open interest and comment counts are left out. Open interest is the other track's CB17-C hypothesis, and
    comment counts barely ever change.
  - Science review: **REVISE, then FIXES_OK_WITH_NOTES**. It found no look-ahead, but CB17-C (drafted) uses the
    event-volume change and event liquidity, so the family is **embargoed until 2026-11-25**.
  - The 94 past tables are built (16:16-16:20Z, peak 360 MB).
  - It can first fit at the ~10-27 refit, once the 12 oldest captures (no sidecars) leave the 14-day window. This is
    the same timing as se8/se10.
- **The other track's embargo requests (round 2, LT6 draft) are applied:**
  - `book` moves to 12-09, so se3 and se14 are hidden until then.
  - New tokens `vote`, `clips`, `deadline` and `siblings` also run to 12-09; no model uses them yet.
- **Walk-forward (development baseline), attempt 2:** 4 of 7 test days were done by 16:10Z (11-15 min per day, peak
  1.36 GB). It should finish around 17:00-17:15Z, within its 3 h limit.
- Nothing has been promoted. No edge claims. The UI wording stays "signal strength".

## Live state (host)
- **Code:** deployed `e3a0a24` (main checkout `chore/arepo-claude-setup`). The registry loads 17 models.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (broad) | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se15_lgbm_surprise` | 11-19 |
| `se2_lr_flow`, `se11_lgbm_flow`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event` | 11-22 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book`, `se14_lgbm_movetype` (book token) | 12-09 |

  - Non-embargoed challengers: K = 2 (se1, se7) until 11-04.
- **Queue** (all signal-engine jobs at priority 50):
  - `q0512` refit: next ~10-22 07:34Z.
    - se14 and se15 should fit for the first time.
    - se16 has no fit until ~10-27 (incomplete coverage), the same as se8/se10. se9 waits until ~11-04.
    - Expect ~62-72 min.
  - `q0513` score: gated 20 h after the 15:38Z leaderboard, so ~10-22 11:40Z (no longer in the resize window).
  - `q0514` walk-forward: attempt 2 is running. Its log is `run/queue/logs/q0514_se_walkforward.2.log`; the output
    goes to `dev/walkforward_*.json` and `dev/latest.json`.
  - `q0515` one-off score: done (`leaderboard/20261021T153806Z.json`).
- **Resolution labels:** the first fetch (800 requests) resolved 39,792 markets, with 103 split and 105 not found.
  77,217 were due, so the backlog clears over the next daily runs.
- **participation tables:** 94 of 106 captures (the 12 on 10-12/10-13 have no sidecar, so they stay missing).
  - One-off script `~/.arepo/signal_engine/aux_backfill_participation.sh`, with its log next to it.
  - Coverage on 10-21 14:31Z: event volume 73%, its change 72%, liquidity share / competitive / age 100%,
    volume_num 45%. The capture right after a sidecar-less one has no change column (as designed).

## Changes this session
1. Queue specs: q0512/q0513/q0514 priority 42/39/35 -> 50; new one-off `q0515_se_score_now`.
2. New aux family `participation` (`se-aux-participation-v1`, columns `pp_*`) and spec `se16_lgbm_participation`
   (sha `5f458bc4…`).
   - New embargo token `participation` (CB17-C, 11-25).
   - The aux metadata records the previous sidecar it read (`prev_sidecar_capture_id`, `prev_sidecar_sha256`).
3. Round-2 embargoes: `book` -> 12-09 (LT6-V); `vote`, `clips`, `deadline`, `siblings` -> 12-09. The stale comment
   on the `event` family is fixed.
4. Tests: participation hand example, forbidden columns, k+1 causality plus provenance, registry and embargo dates.
   37 engine tests pass; ruff is clean.
5. Docs: DESIGN_V1 §8 (token rows) and §16 (fifth family); CANDIDATES row 14 and round 2 marked applied; two ledger
   entries (first leaderboard; se16 with its review).

## Next actions
1. When `q0514` finishes (~17:15Z), read `dev/latest.json`, then update the ledger and this file. If it fails,
   re-promote it with `--max-test-days 5`.
2. After the ~07:34Z refit on 10-22, read `logs/fits-20261022.jsonl`:
   - se14 and se15 should be `ok` on the direction targets;
   - se16 should be `no_fit` (coverage);
   - check the runtime and peak RSS.
   Then check that the next tick writes se14/se15 predictions with `aux_sha256`.
3. After the ~11:40Z score on 10-22, read `leaderboard/latest.json`: the second day and the first 6 h / 24 h labels.
4. After the resize (2 OCPU), consider two parallel fits in the refit. That is a code change plus a memory check.
5. Every new family so far shadows a live test. Next non-embargoed ideas:
   - a crypto spot reference (Binance) for crypto ladders, which needs a light spot stream plus strike parsing (no
     question text in the captures);
   - better learners on the base features.
6. Around 10-27, check that se8, se10 and se16 start fitting; around 10-28, check the LightGBM `res_7d` fits.
7. Housekeeping: the merged PR worktree `/Users/DayyanSheikh/Projects/astrolabe-lab-se` can be removed (still
   pending approval).

## Notes for the other track
- Owner resize at 2026-10-22 02:40Z: no deploys, crontab edits or queue resumes during 02:40–03:45Z.
- q0561 (exclusive, priority 60, must start before 02:45Z) outranks the signal-engine jobs. The refit is not due until
  07:34Z, so there is no collision.
- If CB17-C's REP_8 slips past 11-23, move `participation` later (never earlier).
