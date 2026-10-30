# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 04:36 UTC+1 (2026-10-30 03:36Z), signal-engine autopilot session 33

## In plain English
- **Prevented a silent stop of the engine.** Its data folder was 5.2 GB and growing ~0.6 GB a day (28 models). Its
  own 8 GB safety cap would have been hit around **11-03**, just before the first promotion reads. The engine would
  then have stopped writing predictions without any alarm, because a refusal looks like "nothing due".
  - The cap is now **16 GB**. The host disk has 33 GB free, and every engine file is already backed up in the nightly
    verified releases.
  - New model files are gzip-compressed. This is lossless (the same content, ~2.4x smaller) and saves ~0.1 GB a day.
    Older files are untouched and still read.
  - The engine now reports its disk use (`status`, and the `/lab` snapshot via `live_status`), with a warning at 80% of the cap.
- **Owner decision needed by ~11-15:** with no deletions at all, 16 GB is reached around **11-20**. The lasting fix is
  to switch on the deletion rules already drafted for the engine: predictions older than 35 days, features and quotes
  older than 45 days, plus the same 45 days for `aux/`. Files are deleted only once they are in a verified release.
  The engine would then settle near 14 GB. The alternative is another raise of the cap.
- No model, target, score or promotion rule changed. Still 28 models; se27 fits for the first time at today's refit
  (~13:40Z), and that refit is the first to write compressed files. First promotion reads ~11-04.
- Also still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** main `e4d219f8` deployed this session (DESIGN_V1 §40). Host check: `disk` = cap 16 GB, used 0.328, no
  warning; se1's legacy (plain JSON) fit loads with its sha checks.
- **Input monitor** (03:06Z): status ok, no alerts, capture `20261030T023102Z`.
- **Refit `q0512` / score `q0513`:** daily, healthy (`tempfail` = not due). **Probe `q0518`:** still queued (priority 30).
- **Disk:** engine 5.24 GB of 16 GB; `research_lab` 36.0 GiB of the tick's 50 GiB data-dumps cap; host disk 33 GiB free.

## Embargo list (unchanged this session; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full`, **`se27_lgbm_stress`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **DESIGN_V1 §40:** `ENGINE_DISK_CAP_GB` 8 -> 16, with the measured growth and the projection.
2. **gzip fit artifacts:** new fits write `<target>.json.gz` (mtime 0, deterministic bytes) and `fit.json`
   `artifact_files`. `training.read_artifact` is the one reader (predict, dashboard attribution) and reads both formats.
3. **`disk` block** in `run_signal_engine.py status` and `dashboard.live_status` (bytes, cap, share, `warn` >= 0.8).
4. Tests: 2 new (gzip / legacy round trip with a sha-mismatch refusal; disk warn); 76 engine + 6 input-health tests
   pass; ruff clean. One signal-engine ledger entry.

## Next actions
1. **After the 10-30 refit (~15:20Z):** confirm se27 fitted on its 3 direction targets, that the new fits carry
   `artifact_files` (`.json.gz`), that the next capture's predictions are written from them, and the peak RSS
   against 3,400 MB.
2. **Disk:** read `status` -> `disk` each session. If the owner approves, move the three engine `deferred_rules` into
   `rules` and add `signal_engine/aux/` at 45 days in `scripts/oracle/archive_retention.json`. Otherwise plan a further
   cap raise before `warn` (12.8 GB, ~11-14).
3. **Input monitor:** read `state/input_health.json` each session.
4. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
5. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written; record the decision.
6. **~11-13 (se27's 14 days):** if se27 beats se1 on `dir_2h`, register the slotfac-only reference arm (§36) before any
   credit to stress.
7. **Candidate pool:** the next cheap build is CH267's `cl_class` level as a `rules` column (44.7% coverage). Round-18
   `attn` still needs CB17's use of the comment count checked first.
8. **Before 11-14:** check that LT2's analysis (q0461) has run; if not, move `tte`, `chg1d_x_liq`, `dispgap` later, and
   `flow` before 11-16; `rewards` against E022 before 11-18.
9. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
10. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
11. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*`, `/tmp/se_*` scratch (Mac and host) and
    old backfill logs.

## Notes for the other track
- Deployed main `e4d219f8` (your tip merged with this session's engine change); nothing of yours was changed.
- The engine's 8 -> 16 GB cap only governs the engine's own writes; the writers' 50 GiB data-dumps cap is unchanged.
  No job of yours was paused, cancelled or re-prioritised.
