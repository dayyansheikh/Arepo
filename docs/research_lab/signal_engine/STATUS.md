# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 08:27 UTC+1 (2026-10-30 07:27Z), signal-engine autopilot session 35

## In plain English
- **New signal family: the market's dispute settings.** Each Polymarket market carries settings that the listing
  desk chooses. They cover how much a challenger must stake to dispute the result (the UMA bond), the reward,
  whether the challenge window is custom, the fallback if the result is unclear, and which resolver contract
  settles it. CH207's idea is that the desk sets these higher on questions it expects to be contested, and that the
  crowd does not read them. The engine now reads them from the hourly `gamma_rules` stream as they stood before each
  capture. The row's end date is deliberately **not** read: it would copy the embargoed time-to-close family.
- Coverage is 34% of the markets the engine scores (69% of non-sports). One planned column, "dates not reviewed", was
  dropped because every covered market has reviewed dates.
- New challenger **`se29_lr_uma`**: the champion's simple (logistic) model plus these settings.
- New control **`se30_lr_framein`**: the champion plus one flag, "this market is in the rules stream at all". The
  independent review pointed out that this flag mostly means "the market is liquid enough to be polled". Rule text
  (se28) or dispute settings (se29) now earn credit only if they beat this control, both overall and in at least 2
  of 3 category groups (sports, crypto, the rest). Otherwise the gain is recorded as a frame or category stand-in.
  This rule was written down before any score existed.
- No embargo applies (the idea is engine-first; no live test claims these fields). Earliest creditable read is ~11-18,
  the same as se28. 31 models now. No existing model, target, score or promotion rule changed.
- Still needing the owner:
  - **disk retention by ~11-15** (session 33; see Next actions 3);
  - a public website version of the feed.

## Live state (host)
- **Code:** main `2f8bedda` deployed (host `uma_params.py` sha `75dd85e9...`). **`umaparams` and `framein`
  backfilled**: 210 tables each, the same count as `rules`. The run was a one-off `features --max-items 25` then
  `--max-items 5`, under the collector lock at nice 19 (41 s, 320 MB peak). Newest capture: `up_has` 0.340, identical
  to `fi_has` and to `rc_has`; tables before the stream are all-NaN. se29 / se30 fit for the first time at the
  13:40Z refit.
- **Engine `status`** (07:06Z): 210 captures, 198 fits, 11 leaderboards; input monitor ok, no alerts; disk 5.36 GB
  of 16 GB (0.335).
- **Queue:** two of the other track's jobs were running (`q0085_cb4_flip_trades_dev`, `q0733b_m2_j0`). Host memory had
  8 GB available. Nothing of theirs was touched.
- **`gamma_rules` stream:** day files 20261020..20261030 contiguous. Three engine families now need every day file
  (`rules`, `umaparams`, `framein`).
- **Tick cost:** the `rules` reader parses the whole stream cold in each tick process (20 s at 314 MB of stream, and
  growing about 26 MB a day). The UMA reader takes 2.9 s, and `framein` reuses it from memory. See Next actions 4.

## Embargo list (unchanged; se28 / se29 / se30 not embargoed; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full`, `se27_lgbm_stress`, `se28_lr_rules`, **`se29_lr_uma`**, **`se30_lr_framein`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **DESIGN_V1 §42**: definitions and census script committed `9d21cad7` (07:14:28Z) before the census (07:14:36Z).
   Then the result, the review and the reading rule.
2. **Census** (counts only; `census/se_umaparams_census_2026-10-30.{py,out}`): the family passes. Five value columns
   were kept and `up_unreviewed` was dropped. The top `resolvedBy` address was pinned, as declared in advance.
3. **Code:**
   - `signal_engine/uma_params.py`: its own reader; `rules_text.py` is untouched, so se28's sha is unchanged.
   - aux families `umaparams` and `framein`.
   - specs `se29_lr_uma` and `se30_lr_framein`, with registry pins.
   - 6 new tests; 94 engine tests pass; ruff clean.
4. **Science review: REVISE (minor).** Causality, embargo and census order PASS. All fixes were applied before any
   table existed:
   - the control arm se30;
   - the within-category reading rule;
   - NaN, not 0, for an absent fallback type or a "none" resolver;
   - the missing-liveness count by category (sports 28%);
   - the same-day gap-guard looseness disclosed for both stream families.
5. Ledger entry; CANDIDATES row 32.

## Next actions
1. **After the 10-30 refit (~13:40-15:20Z):**
   - confirm the fits of se27 (3 directions), se28, se29 and se30, or `insufficient_coverage`;
   - check that the fits carry `.json.gz` artifacts, and peak RSS against 3,400 MB;
   - check that `aux` logs show no `RulesGap` / rules / umaparams errors.
2. **Reading rule for se28 / se29 (DESIGN_V1 §42 review item 3):**
   - from ~11-18, compute the per-day `dir_2h` gain difference against se30, pooled and by category group;
   - credit only if the pooled 95% interval is above 0 and 2 of 3 groups are positive.
   This reading is separate from promotion, which stays `se-promotion-v2` against the champion.
3. **Disk:** read `status` -> `disk` each session. If the owner approves, move the engine `deferred_rules` into
   `rules` and add `signal_engine/aux/` at 45 days. **Do not** activate the proposed 14-day rule for
   `stream_gamma_rules/`: three families would then fail with `RulesGap`, unless the readers first gain a
   release-restore path.
4. **Tick cost (engineering, no model change):** the stream readers re-parse every day file in each tick process.
   Add a per-day parsed cache (an engine-side file per closed day file, keyed by its sha) before the `rules` read
   passes ~60 s (~12-01 at the current growth). Doing this changes the readers' shas; the tables record the sha they
   were built with.
5. **Input monitor:** read `state/input_health.json` each session. Later: a stream-staleness line from the tables'
   `rules_last_slot`.
6. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
7. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written and record the decision.
   se28, se29 and se30 count in K from today.
8. **~11-13:** se27's 14 days. If it beats se1 on `dir_2h`, register the slotfac-only reference arm (§36) before
   any credit to stress.
9. **Candidate pool:**
   - CH269's map (`reviews/CH269_MAP_2026-10-30.md`): LT15 was not drafted (20 scheduled closes a day), so se28 stays
     logistic and unembargoed.
   - CH228 `ruleedit` (edit age, same stream) is the next cheap family.
   - Round-18 `attn` still needs CB17's use of the comment count checked first.
10. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap`
    later, and `flow` before 11-16; check `rewards` against E022 before 11-18.
11. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
12. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
13. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*`, `/tmp/se_*` scratch (Mac and host,
    including `/tmp/se_uma/`) and old backfill logs.

## Notes for the other track
- Merged your tip and deployed main (`2f8bedda`). Nothing of yours was changed.
- The backfill ran under the collector lock between passes (07:26Z-07:28Z); your two running queue jobs were not
  touched.
- Three engine families now read `stream_gamma_rules/` read-only and need every day file since 20261020. Please do not
  activate that stream's proposed 14-day retention without telling this track.
- No job of yours was paused, cancelled or re-prioritised.
