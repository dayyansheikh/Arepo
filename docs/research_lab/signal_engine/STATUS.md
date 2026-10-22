# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 17:40 UTC+1 (16:40Z), signal-engine autopilot session 14

## In plain English
- **The daily refit and the daily score were failing, and both work again.**
  - After MC1 finished, the refit (`q0512`) and the score (`q0513`) both started and crashed with "out of memory".
    The machine had plenty of memory free. Each job hit its own virtual-memory cap.
  - **Refit:** the new 900k-row model se17 made the training table 3x larger. The code copied that table two or three
    times while picking rows. It now copies once, with the same rows in the same order (a test checks this). The
    memory caps now match measured use.
  - **Score:** it only needed a higher cap (its real memory use is about 0.6 GB).
- **Results after the fix:**
  - Refit: 15:44-16:32Z, every direction target of every visible model fitted. This includes the first-ever fits of
    se14, se15, se17, se18 and se19.
  - Score: day 2 of the prospective leaderboard was written at 15:46Z.
- **Early leaderboard, development stage (2 days, no promotion before 14).** The LightGBM momentum model (se1) and
  the all-features model (se7, ineligible) have lower log loss than the champion by about 0.05-0.07 on the 2 h, 6 h and
  24 h direction targets. The confidence intervals are tight but cover only 2 days. This is signal strength, not an
  edge claim.
- **/lab shows the real refit time.** The "last refit" and "last prediction" times are now re-read from the engine's
  logs on every 10-minute push. A stopped refit will show its true age instead of yesterday's date.

## Live state (host)
- **Code:** deployed with the merge of this session's commits (see the git log on the host: `git -C ~/arepo log -1`).
- **Refit `q0512`:** exit 0 in 2,887 s, peak RSS 2,902 MB, VmPeak 4.6 GB. Frames: 892,476 direction rows and 819,454
  resolution rows. Spec: mem_mb 2200 -> 3400 and as_cap_mb 3500 -> 6000 (host: 2 OCPU / 11.4 GiB). Not exclusive.
  - `insufficient_coverage` (expected): se8, se9, se10, se16 and se20.
  - Every LightGBM `res_7d` fit fails with "inner split too small (train 0)". This is the known, self-healing issue in
    DESIGN_V1 (resolution labels are timed by fetch receipt; the backlog was first fetched on 10-21). It should clear
    around 10-28. Logistic `res_7d` fits are fine.
- **Score `q0513`:** exit 0 in 73 s, peak RSS 589 MB. Spec: as_cap_mb 2000 -> 3000. Resolve: 12 requests, 278 resolved,
  15 split 50/50, 301 not yet closed (`not_found` under `closed=true`; re-fetched after 12 h, never final).
- **Leaderboard (day 2):** K = 7, champion `se0_champion_lr_mm`, promotion null (fewer than 14 days). Embargoed models
  show only their dates.
- **Queue:** both jobs were re-armed with `queue_worker.py retry` (own jobs only) and are back in `queued` for
  tomorrow. Nothing on the other track was touched.

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se8_lr_event`, `se10_lgbm_event` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-01-23 |

## Changes this session
1. `training.select_rows`: positions first, one `take`, and the index set in place. Test
   `test_select_rows_matches_the_pre_2026_10_22_two_copy_version` checks equality with the old version.
2. Queue specs: q0512 (mem_mb 3400, as_cap_mb 6000) and q0513 (as_cap_mb 3000), with measured notes.
3. `dashboard.live_status()` is shared by the daily dashboard and `lab_host.build_signal_engine`, so the last refit and
   last prediction are refreshed every push. It carries times and counts only, no scores. Test added. No frontend change.
4. Tests: 52 engine tests and 11 queue tests pass; ruff is clean.

## Next actions
1. Tomorrow (~10-23 15:44Z): check that q0512 and q0513 ran without help. Expect the refit at ~2,900-3,100 MB RSS.
2. Check that the 16:31Z capture's predictions use the 15:44Z fits (16 models instead of 11).
3. **Before 11-16:** check that LT2's analysis (`q0461`, not before 11-13T12Z) has run. If not, move `flow` later. Do
   the same for `rewards` against E022's analysis before 11-18.
4. Around 10-27/28: se8, se10, se16 and se20 start fitting, and the LightGBM `res_7d` fits should start working. That
   adds memory. If the refit peak RSS passes ~3,300 MB, raise mem_mb, or cap the resolution frame below the direction
   cap (it now reuses the 900k direction cap; that is a spec change and needs a note).
5. Remaining ideas: CH207-CH211 engine-first families, CH198 `theta`, and `hwm` with a short look-back. Each raises K,
   so build only those with a real prior.
6. Housekeeping (needs approval): remove the merged worktrees `astrolabe-lab-se` and `astrolabe-lab-se-promo`, plus
   `/tmp/se_dev`, `/tmp/se_e2e` and the host's `/tmp/se_b0`.

## Notes for the other track
- `tests/unit/test_lab_clients.py::test_registry_experiments_schema` fails on the current main: LT7's registry summary is
  552 characters (limit 450). It is the experiments track's text, so I did not change it.
- MC1 (exclusive) delayed the engine's refit by ~6 h today. When the refit then ran, it crashed for its own reasons
  (fixed above), not because of MC1.
