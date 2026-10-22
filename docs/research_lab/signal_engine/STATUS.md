# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 08:07 UTC+1 (07:07Z), signal-engine autopilot session 12

## In plain English
- **New challenger: a crypto spot-price reference (`se20_lgbm_crypto`).**
  - Thousands of Polymarket crypto markets (up/down windows, strike ladders, "hit price") are priced off one spot
    price. Until now the engine only saw each market's own price history.
  - The new `crypto` family gives the model the Binance spot path, with only bars that closed before the capture:
    recent spot returns, volatility, where an up/down window stands against its opening price, and how strongly the
    market has followed spot in the past.
  - It is not hidden: no live test uses a spot reference (CB13-R, the one that did, is closed). It makes the promotion
    bar slightly stricter for everyone (K goes from 4 to 5).
  - It can only start fitting at the 10-27 refit. Snapshot rows before 10-13 04:31Z are gone (temporary 10-day
    retention), so 14 early captures can never have the family. The model trains only once its whole window has it.
- **Fixed a defect that would have cost new models their 2 h forecasts.**
  - Each pass built at most 4 of a new capture's 6 extra feature tables. The last two (`participation`, `book0`) waited
    for the next pass, two hours later, when the capture's 2 h target had already started.
  - No forecast was lost yet: se16 has no fit, and se18/se19 fit for the first time at today's 07:34Z refit. Now every
    family of a new capture is built in the same pass, before its predictions.
- The science review accepted the crypto family with fixes. It found no leakage, and all the fixes are applied.
- Nothing has been promoted. No edge claims; the UI wording stays "signal strength".

## Live state (host)
- **Host:** resized to 2 OCPU / 11.4 GiB (owner decision; ledger 2026-10-22). LightGBM still runs on 1 thread.
- **Code:** merged into chore (908c48e9) and deployed at ~07:00Z (host at ea7f80fb, which includes it; registry lists
  se20). The deploy printed a harmless `rm: cannot remove ~/arepo_trials_from_mac.jsonl` (the file was already gone,
  probably a concurrent deploy by the other track).
- **Crypto backfill (running since 07:01Z):** `~/.arepo/signal_engine/aux_backfill_crypto.sh`, log next to it. It runs
  batches of 7 tables, each capped at 240 s, under `flock -n` on the collector lock, and never at even hours :19-:31.
  Binance answers in ~2 s per request, so ~40 s per capture and ~70 min for ~102 captures. It also built the 06:31Z
  capture's `participation` and `book0` tables, which the old-code tick had left out.
  - First table check (10-22 06:31Z capture, no outcomes): 3,917 of 54,366 eligible markets are mapped (3,441 up/down,
    143 strikes, 140 neg-risk, 193 hit-price). The spot columns are complete for every mapped market, `cr_beta` for
    65%, and `cr_ud_z` for only 25 markets (few eligible up/down windows have started at a capture). No symbol is
    unavailable. Inputs take ~140 KB per capture.
- **Queue:** `q0512` refit is due ~07:34Z. It is the first fit for se14, se15, se17, se18 and se19 (se20 reports
  `insufficient_coverage` until 10-27). `q0513` score is due ~11:40Z. No jobs were touched.
- **Promotion-eligible non-embargoed challengers:** se1, se17, se18 and se20 (once it fits). K = 5: se1, se7, se17,
  se18, se20 (se7 counts but is ineligible).

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, **`se20_lgbm_crypto`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se15_lgbm_surprise` | 11-19 |
| `se2_lr_flow`, `se11_lgbm_flow`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event` | 11-22 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 12-31 |

## Changes this session
1. `aux.py`: family `crypto` (`se-aux-crypto-v1`): sidecar slug mapping, write-once Binance kline inputs per capture
   (`aux_inputs/crypto/`), 15 columns. Review fixes: HTTP 400 symbols recorded as unavailable; `cr_has` NaN for
   markets missing from the sidecar; sidecar sha256 in provenance; a 120 s fetch budget per capture.
2. Spec `se20_lgbm_crypto` with its registry entry (`added_utc` corrected to 02:34Z), DESIGN_V1 §23, CANDIDATES rows
   5 and 20, and a ledger entry.
3. `run_signal_engine.py`: the aux budget is now `len(AUX_FAMILIES) x max_items`, not `max(2 x max_items, 4)`.
4. Tests: 50 engine tests pass (3 crypto tests and 1 budget regression test). Ruff is clean.

## Next actions
1. Check that the crypto backfill finished (`crypto backfill done` in its log; ~102 tables in `aux/crypto`, no repeated
   errors). If Binance latency grows past ~5 s per request, the live tick's 120 s budget will start failing captures;
   then fetch the symbols in parallel.
2. After the ~07:34Z refit, read `logs/fits-20261022.jsonl`:
   - Expect se14, se15, se17, se18 and se19 `ok`, se16 `no_fit`, and se20 `insufficient_coverage`.
   - Check that the total runtime is under 10800 s and peak RSS under 2200 MB.
   - At the 08:31Z pass, check that every aux family of the new capture exists and that se18 predicts.
3. After the ~11:40Z score: check day 2 of `leaderboard/latest.json`. Expect K = 5 under `se-promotion-v2`.
4. If the refit runtime nears its timeout: LightGBM `num_threads` 2 (the queue's cpu lane runs one job at a time; the
   second core serves the collector).
5. Around 10-27: se8, se10, se16 and se20 start fitting. Around 10-28: the LightGBM `res_7d` fits.
6. Remaining ideas: CH198 `theta`, CH201 rewards-v2 (check them against §21 and §22 first), the learner-matched
   `se21_lgbm_book0` (embargoed 12-31).
7. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`, plus
   `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0`.

## Notes for the other track
- `crypto` has no embargo token: no registered or drafted test uses a spot reference (science review checked CB13-R,
  E019 M2, the LT6 crypto classifier and LT7 `ivr`). If a future test uses spot, ask and se20 will be embargoed.
- LT5 F, H and R were dropped at census (ledger ~06:05Z). The `event`, `book` and `rewards` embargo dates still list
  them. Dates only move later, so nothing changes here unless you ask.
- No queue jobs were touched.
