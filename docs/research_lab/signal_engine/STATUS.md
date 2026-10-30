# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 18:27 UTC+1 (2026-10-30 17:27Z), signal-engine autopilot session 37

## In plain English
- **The daily model refit was close to its memory limit; it now has headroom.** Today's refit trains 31 models.
  Its memory use reached 3.9 GB, up from 2.9 GB a week ago, and it took 1 h 45 min, up from 48 min. Both grow each
  time a model is added. The queue had reserved only 3.4 GB. The hard limit that crashed a refit on 10-22 was probably
  ~0.4 GB away. Both limits are now raised: memory reservation 4.3 GB, hard cap 8 GB, time limit 4 h. The engine also
  now logs the number that actually hits that cap, which it did not record before. No model or number changed.
- **The four newest challengers fitted for the first time today** (stress, rules, dispute settings and its control).
- **Three idea families were set aside, with reasons written down, instead of being built:**
  - `shock`: one favourite collapse affecting others in its category. Only ~1.7 such collapses a day, so too few.
  - `rowq`: data-quality flags. The models already see most of this.
  - `xent`: cross-venue entity moves. It waits for the 11-04 read of the stronger, direct cross-venue models.
  Each extra challenger also makes promotion harder for the good ones, which are due their first read on 11-04.
- **Leaderboard (development, 10 days scored, not a claim):** unchanged since this morning. Every tree-based challenger
  beats the simple champion on the main 2-hour target. No promotion is possible before 14 scored days (~11-04).
- **Still needing the owner:** disk retention by ~11-15 (session 33); a public website version of the feed; the
  sports-scope decision.

## Live state (host)
- **Code:** main `344c0914` deployed 17:23Z (q0512 `mem_mb` 4,300, `as_cap_mb` 8,000, `timeout_s` 14,400; `peak_vm_mb`
  in the refit summary and every engine marker line). `4b1b5e48` (input-monitor `stale_stream`) was already live.
- **Engine `status`** (17:1xZ): 215 captures, 229 fits, 12 leaderboards; input monitor ok, 0 alerts; disk 5.72 GB of
  16 GB (0.358).
- **Refit 10-30** (q0512, 13:34-15:19Z): exit 0, 6,295 s, peak RSS 3,870 MB, 31 models. se17 alone 1,191 s; the
  ineligible se3 / se7 / se14 together 552 s (they stay: they count in K, and retiring them now would loosen the level).
- **Trend (refit):** RSS 2,903 MB (10-22) -> 3,494 (10-29) -> 3,870 (10-30); seconds 2,887 -> 5,775 -> 6,295.
- **Queue:** q0512 / q0513 in retry_wait (daily); q0518 (se17 refit_full dev probe) queued at priority 30. The host had
  ~2.1 GB available at 17:16Z (the other track's `run_ml_dev.py` at 5 GB RSS; swap full). Nothing of theirs was touched.

## Embargo list (unchanged; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full`, `se27_lgbm_stress`, `se28_lr_rules`, `se29_lr_uma`, `se30_lr_framein` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **DESIGN_V1 §46** (ops): q0512 headroom as above; `store.peak_vm_mb()` (VmPeak from `/proc`, None on macOS), wired
   into `training.refit` and `run_signal_engine.out`. 124 engine/lab unit tests + 1 new test passed; ruff clean.
   Commit `546080a5`; ledger line.
2. **CANDIDATES rows 35-37:** `shock` and `rowq` deprioritised (no census run; reasons written down); `xent` sequenced
   after the 11-04 `xvenue` read.
3. Two ledger conflicts on sync were resolved by keeping both sides, theirs first.

## Next actions
1. **Next refit (10-31 ~13:30Z):** read `peak_vm_mb` and `peak_rss_mb` from `logs/fits-20261031.jsonl` (the first
   refit to log VmPeak). If VmPeak is above ~7,000 MB (cap 8,000) or the runtime is above ~12,000 s (timeout 14,400),
   write the saving section §46 asks for before adding any LightGBM challenger.
2. **Done this session:** `4b1b5e48` was deployed; se27 (3 direction fits), se28, se29 and se30 (4 targets each) fitted
   at 10-30 13:34Z with `.json.gz` artifacts. Their first predictions and scores follow on the normal path.
3. **Reading rule for se28 / se29 (§42 item 3):** from ~11-18, compute the per-day `dir_2h` gain difference against
   se30, pooled and by category group. Credit needs the pooled 95% interval above 0 and 2 of 3 groups positive.
4. **Disk:** read `status` -> `disk` each session. If the owner approves, move the engine `deferred_rules` into
   `rules` and add `signal_engine/aux/` at 45 days. Do **not** activate the proposed 14-day rule for
   `stream_gamma_rules/`: three families need every day file (the parse cache does not replace the files).
5. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
6. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written and record the decision.
7. **~11-13:** se27's 14 days. If it beats se1 on `dir_2h`, register the slotfac-only reference arm (§36) before any
   credit to stress.
8. **Candidate pool** (CANDIDATES rows 35-37, 2026-10-30):
   - `shock` and `rowq` are deprioritised, with reasons and no census run.
   - `xent` waits for the 11-04 `xvenue` read.
   - `headline` (CH255): two-member events are held to 2027-01-03, and CH261's map gives a median of 11 flips a capture.
     Designable for 3-10 member events.
   - `disp` only as a lagged (k - 1) redefinition. `batch` is held for the LT13 freeze.
   - Prefer logistic challengers (~30 s per refit) over LightGBM (~5-7 min) until the refit has headroom.
9. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap` later,
   and `flow` before 11-16; check `rewards` against E022 before 11-18.
10. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
11. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
12. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*` and the `/tmp/se_*` scratch (Mac and
    host, including `/tmp/se_uma/`, `/tmp/se_ruleedit/`, `/tmp/se_parentsib/`) and old backfill logs.

## Notes for the other track
- Merged your tip twice and deployed main `344c0914` (your commits up to `0ba37be0` included). Ledger conflicts were
  resolved by keeping both entries, yours first. Nothing of yours was changed.
- q0512 now reserves 4,300 MB (was 3,400), so its start gate needs ~5.5 GB available. With the host's swap full this
  afternoon, the refit may start later than 13:30Z on days when your heavy jobs run. It is daily, so a delay of a few
  hours costs nothing. Please do not lower its reservation.
- `stream_gamma_rules/` still needs every day file since 20261020. Please do not activate its proposed 14-day
  retention without telling this track.
- No job of yours was paused, cancelled or re-prioritised.
