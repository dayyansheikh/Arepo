# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 12:03 UTC+1 (11:03Z), signal-engine autopilot session 13

## In plain English
- **Two hidden challengers become visible, and two more will be scored sooner.** Several "embargoes" (rules that hide a
  model's scores so it cannot spoil a registered live test) only protected tests that have since been dropped at
  their census, before registration. The programme's rule is that such a token is then withdrawn. As of 2026-10-22
  12:00Z:
  - **`event` is released.** `se8_lr_event` and `se10_lgbm_event` are scored and shown as soon as they fit (first fits
    ~10-27), about 4 weeks earlier than before.
  - **`flow` moves from 11-22 to 11-16.** se2 and se11 are scored 6 days sooner; the registered LT2 tests still keep
    their margin.
  - **`rewards` moves from 11-22 to 11-18, not fully released.** The science review found that registered E022 still
    compares rewarded and unrewarded markets.
  - Four unused LT6 tokens and LT7's `mm_fresh` are withdrawn.
- **LT8's protections are applied.** Its three new families are hidden to 2027-01-23. The book families are now hidden
  to the same date, 23 days longer. That is the price of protecting LT8.
- **The promotion bar gets slightly stricter.** The rule corrects for every visible challenger at once (K goes from 5 to
  7). This follows the rule declared in advance; no threshold changed.
- **The 2 h refit is late today.** The other track's 6 GB "exclusive" MC1 job has held the host since 07:42Z (it may run
  until 13:42Z). The refit (due 07:34Z) and the daily score (due 11:38Z) start after it. Predictions continue every pass
  from yesterday's fits. Nothing was touched on the other track's side.
- No promotion, and no edge claims. The UI wording stays "signal strength".

## Live state (host)
- **Host:** 2 OCPU / 11.4 GiB. Collector pass 10:31Z ran until 11:02:42Z (31 min; MC1 holds memory, swap 1.7 GB). The
  10:31Z capture has all 7 aux families and all 11 model predictions.
- **Code:** merged into chore at 09d26bab and deployed at 11:03Z, before the 12:00Z withdrawal time. Verified on the
  host: K = 5 at 11:59Z and 7 at 12:00:01Z. A second deploy by the other track (cloned after the merge) followed. Earlier
  in the session, some background-task notices reported a deploy that had not happened yet. Always check the host
  directly (`git -C ~/arepo log -1`).
- **Crypto backfill:** done at 09:26Z. 103 `aux/crypto` tables, no errors. The 08:31Z capture has all 7 aux families
  (last session's same-pass fix works).
- **Queue:**
  - `q0116f_mc1_dev_run` (other track, exclusive, mem 6000, timeout 6 h) has run since 07:42Z.
  - Waiting behind it: `q0512` refit (last fit 10-21 11:34Z; first fits of se14, se15, se17, se18 and se19) and
    `q0513` score (net lane, but mem 700 >= the 500 MB light-job exemption).
  - No job was changed. I did not lower q0513's mem_mb to slip under the exemption: that is meant for live collectors.
- **Promotion candidates (non-embargoed):** se1, se7 (ineligible), se8, se10, se17, se18 and se20. K = 7. Expected K as
  embargoes lapse: 9 at 11-04, 11 at 11-14, 13 at 11-16, 14 at 11-18, 15 at 11-19, 16 at 11-25, 17 at 12-07, and 20 at
  2027-01-23.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, **`se8_lr_event`, `se10_lgbm_event`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | **11-16** (was 11-22) |
| `se9_lr_rewards` | **11-18** (was 11-22) |
| `se15_lgbm_surprise` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | **2027-01-23** (was 12-31; LT8) |

## Changes this session
1. `config.EMBARGO`:
   - Withdrawn: `event`, `vote`, `clips`, `deadline`, `siblings`, `mm_fresh`. Each keeps its entry, with `until` =
     `withdrawn_utc` = 2026-10-22T12:00Z and `until_before`.
   - LT5 extensions undone: `flow` back to 11-16 (E013/E014) and `rewards` back to 11-18 (E022 S2).
   - Dropped tests pruned from the lists of `book`, `book0` and `wallet`.
   - LT8 round 5 applied: `quietbook`, `swclock` and `sched` added, `book`/`book0` moved to 2027-01-23.
2. DESIGN_V1 §8: table updated and a new "Withdrawal" paragraph. CANDIDATES: builder rows 1, 2, 6 and 9; round 5 marked
   APPLIED. Ledger entry: "embargo withdrawals after census drops".
3. Tests: date tests updated, a withdrawal test added (any date moved earlier must carry the withdrawal fields) and a
   lab_host check that a withdrawn family is shown again. 50 engine tests pass; ruff is clean.
4. Science review: ACCEPT_WITH_FIXES, all applied. The main fix: keep `rewards` for E022 S2 instead of withdrawing it.

## Next actions
1. After MC1 ends, check that `q0512` ran: `logs/fits-20261022.jsonl` should show se14, se15, se17, se18 and se19 `ok`,
   se16 `no_fit`, and se20 `insufficient_coverage`. Runtime should be under 10800 s and peak RSS under 2200 MB.
2. After `q0513` runs: day 2 of `leaderboard/latest.json`. Expect K = 7 and se8/se10 listed (without scores until they fit).
3. **Before 11-16:** check that LT2's analysis (`q0461`, not before 11-13T12Z) has run. If not, move `flow` later (the
   entry says "the later of 11-16 and LT2's analysis commit"). Do the same for `rewards` against E022's analysis before
   11-18.
4. Around 10-27: se8, se10, se16 and se20 start fitting. se8's 28-day retirement check counts from its first score.
5. If the refit runtime nears its timeout: LightGBM `num_threads` 2.
6. Remaining ideas: CH207-CH211 engine-first families (`umaparams`, `requote` after E015, `farmer`), CH198 `theta`, `hwm`
   with a short look-back. None isolates an embargoed token, but each raises K, so build only those with a real prior.
7. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`, plus
   `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0`.

## Notes for the other track
- Round 5 (LT8) is applied. `book`/`book0` are now 2027-01-23; they return to 12-31 only if both CH202 and CH203 drop.
- `rewards` is kept to 11-18 for E022 S2. LT7 has rewarded secondaries (and the new reward-null ruling) but requests no
  token. If LT7 wants `rewards` protected, file a request and I'll apply it (later only).
- `event` is released. If any new design uses event-sibling moves as a tested term, file a request before se8/se10 fit
  (~10-27).
- Disk: `data-dumps` is 33 GB at 11:00Z (`ml_cache` 4.3 GB, `snapshots` 6.8 GB, engine 1.1 GB; root 58% used). The
  10:31Z pass logged `refused_data_dumps_over_cap` for the cb4 close-window and cb5 extracts (their own lower cap). The
  engine's cap is 40 GB, so about 7 GB of headroom remains.
- Conflict noted: MC1 (exclusive, up to 6 h) delayed the engine's daily refit by ~6 h. Nothing was changed. If MC1 runs
  again, a not_before outside 07:00-12:00Z would avoid it.
