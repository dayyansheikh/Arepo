# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 19:20 UTC+1 (2026-10-30 18:20Z), signal-engine autopilot session 38

## In plain English
- **New challenger that costs nothing to train: `se31_ens_pool3`.** It averages, with equal weights, what three good
  models already predict for each market: se1, se17 and se18, the three tree models due their first promotion read on
  11-04. It has no training step, so it adds nothing to the daily refit, which is the engine's tightest resource. On
  every row, an average like this can never do worse than the average of its members. Only its own prospective score
  will show whether it beats the best one. Its members were picked by their review date, not by their scores, and no
  look at outcomes was made. That choice is recorded.
- **It starts with the 20:31Z capture tonight.** It cannot fill in earlier captures, because late predictions would
  count against it. A dry run on the real 16:31Z capture took 0.4 s and pooled all four targets.
- **An independent science review accepted it with five fixes, all applied before release.** A pool cannot include a
  model barred from promotion or hidden by an embargo. It must name its members' exact versions. It cannot start
  before its registration time.
- **Leaderboard (development, 10 days scored, not a claim):** unchanged since this morning. Every tree-based challenger
  beats the simple champion on the main 2-hour target. No promotion is possible before 14 scored days (~11-04).
- **Still needing the owner:** disk retention by ~11-15 (session 33); a public website version of the feed; the
  sports-scope decision.

## Live state (host)
- **Code:** main `50956085` deployed 18:14Z (se31 + `ens_pool`; registry loads 32 models on the host; se31 not
  embargoed). Session 37's q0512 headroom (`mem_mb` 4,300, `as_cap_mb` 8,000, `timeout_s` 14,400) is unchanged.
- **Engine `status`** (18:15Z): 215 captures, 229 fits, 12 leaderboards; input monitor ok, 0 alerts; disk 5.73 GB of
  16 GB (0.358). All 31 existing models predicted the 16:31Z capture.
- **Refit 10-30** (q0512): exit 0, 6,295 s, peak RSS 3,870 MB, 31 models. se31 adds no refit work.
- **Queue:** q0512 / q0513 daily; q0518 (se17 refit_full dev probe) still queued at priority 30. The other track's
  exclusive `q0116k_mc1_dev_pinned` was running at 17:58Z. Nothing of theirs was touched.

## Embargo list (unchanged; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full`, `se27_lgbm_stress`, `se28_lr_rules`, `se29_lr_uma`, `se30_lr_framein`, `se31_ens_pool3` (inherits its members' embargo: none) | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **DESIGN_V1 §47:** learner `ens_pool` (`ensemble.py`; hooks in `predict.py`, `specs.py`, `training.py`,
   `walkforward.py`) and spec `se31_ens_pool3` (sha `74544860...dc82`, `added_utc` 2026-10-30T20:00:00Z).
   - Pools are written after their members and only when every member has a file. They start at `added_utc`, never
     fit, and inherit any member's embargo.
   - `load_registry` refuses: a pool of pools; a retired, unknown or promotion-ineligible member; a member spec-hash
     mismatch; a missing `added_utc`.
   - 14 new tests; all 114 engine tests pass; ruff clean. Commit `c6282b0a`; ledger line; CANDIDATES row 38.
2. Science review (`science-reviewer`): ACCEPT_WITH_FIXES. All five fixes were applied before the commit (see §47).
3. Two ledger conflicts on sync were resolved by keeping both sides, theirs first.

## Next actions
1. **After 20:31Z:** check that `predictions/20261030T203102Z_*/se31_ens_pool3.parquet` exists and that its log line
   follows se18's. If it shows `members_pending` for long, check se18's `book0` aux timing.
2. **Next refit (10-31 ~13:30Z):** read `peak_vm_mb` and `peak_rss_mb` from the 10-31 refit summary. If VmPeak is
   above ~7,000 MB (cap 8,000) or runtime above ~12,000 s (timeout 14,400), write §46's saving section before adding
   any LightGBM challenger. Pools and logistic challengers stay cheap.
3. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written; K now includes se31.
4. **~11-13:** se27's 14 days (§36 slotfac reference arm if it beats se1). **~11-13/14:** se31's information-only read
   against se17 (§47). If se31 does not beat se17 at 28 days, it is retired by the normal check.
5. **~11-18:** the reading rule for se28 / se29 against se30 (§42 item 3).
6. **Disk:** read `status` -> `disk` each session. If the owner approves, move the engine `deferred_rules` into `rules`
   and add `signal_engine/aux/` at 45 days. Do not activate a 14-day rule for `stream_gamma_rules/`.
7. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
8. **Candidate pool:**
   - `xent` waits for the 11-04 `xvenue` read.
   - `headline`: designable for events with 3-10 members.
   - `disp` only as a lagged redefinition; `batch` waits for the LT13 freeze.
   - A fitted-weight (stacked) pool would be a new spec. Consider it only after se31 has been read.
9. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap` later,
   and `flow` before 11-16. Check `rewards` against E022 before 11-18.
10. **Census drops / LT13:** as in session 37 (CH214 -> `book` / `book0`; CH232-CH234 -> LT11; CH245 / CH244 -> LT12;
    `payreturn`, `batch` and `attrlimit_lt13` at the LT13 freeze).
11. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*` and the `/tmp/se_*` scratch.

## Notes for the other track
- Merged your tip twice (ledger conflicts resolved by keeping both entries, yours first) and deployed main `50956085`,
  your commits up to `ebf1f43e` included. Nothing of yours was changed.
- se31 adds about 1 s per capture to the engine tick and nothing to the q0512 refit.
- `stream_gamma_rules/` still needs every day file since 20261020. Please do not activate its proposed 14-day
  retention without telling this track.
- No job of yours was paused, cancelled or re-prioritised.
