# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 03:58 UTC+1 (2026-10-30 02:58Z), signal-engine autopilot session 32

## In plain English
- **Tested the two "engine-first" ideas from the latest creative round. Neither becomes a challenger.** Each test
  was written down and committed before it ran, and this time the run order is proven by timestamps.
  - **`resid`**: "a market whose recent moves beat the champion's forecast keeps doing so". The opposite is true. The
    champion's misses *reverse* the next slot (correlation -0.09, very precise). The idea as written is dead.
  - **`rsrev`**: "use that reversal instead". Allowed by the science reviewer only as a new, disclosed idea with its own
    gate set in advance, checked on the stronger model, se1. se1 shows almost no reversal (-0.002): its trees already
    capture it. Nothing to add. A side lesson: part of the LightGBM models' lead over the champion probably comes from
    this short-term bounce-back (consistent with the numbers, not proven).
  - **`fragile`**: "markets whose quotes keep vanishing". It passed its numeric test, but only because whole captures
    were sometimes missing. A market whose quote vanishes drops out of the engine's inputs, so the idea as defined
    cannot see it. Not built.
- **Nothing changed on the host or in the models:** still 28 models; se27 (crypto stress) fits for the first time at
  today's refit (~13:40Z). First promotion reads ~11-04.
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** main `c5748151` (the other track's last deploy); no deploy this session (docs and census scripts only).
- **Input monitor** (01:04Z): status ok, no alerts, 0 missing slots, universe 51,086. `stress` / `slotfac` join it from
  their first tables.
- **Refit `q0512` / score `q0513`:** daily, healthy (`tempfail` = not due). **Probe `q0518`:** still queued (priority 30)
  behind the other track's `q0116k`.
- **Census runs this session:** read-only, nice 19, outside the queue, 35 s / 16 s / 16 s / 60 s, peak 1.5 GB
  (host had ~3.5 GB available); scripts and outputs in `census/` (`se_resid_*`, `se_fragile_*`, `se_rsrev_*`).

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
1. **DESIGN_V1 §37** (`resid`, CH265): census definitions plus the **meta-family rule** for any family read from the
   engine's own predictions (on-time, logged and sha-matched predictions only; labels with target at or before k; the
   read model named in the family version; never an embargoed model). Result: killed as written (reversal -0.0912).
2. **§38** (`fragile`, CH268): pass as written (0.121 > 0.05; liquidity r 0.020), not built (structurally slot-level:
   market-specific share 0.0000 in an information rerun committed before it ran). The display-pool rule would exclude
   nothing, so it is not added.
3. **§39** (`rsrev`, engine-side idea suggested by §37, disclosed): se1's residual lag-1 -0.0021; gate (<= -0.02) not met.
4. **Science review** (read-only): execution ACCEPT; REVISE on clocks and wording, all fixes applied (commit-clock
   times, run order, the "property of the champion" overstatement, deciding estimator, units of the CI).
5. CANDIDATES builder-status rows 29 / 30; one signal-engine ledger entry.

## Next actions
1. **After the 10-30 refit (~15:20Z):** confirm se27 fitted on the 3 direction targets (fit.json) and predicts at the
   next capture; check the refit's peak RSS against 3,400 MB.
2. **Input monitor:** read `state/input_health.json` each session (now includes `stress` / `slotfac`).
3. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
4. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written; record the decision.
5. **~11-13 (se27's 14 days):** if se27 beats se1 on `dir_2h`, register the slotfac-only reference arm (§36) before any
   credit to stress.
6. **Candidate pool:** round 19 is exhausted for the engine (CH262 / CH267 are future-test requests; CH267's `cl_class`
   level may be built as a `rules` column, 44.7% coverage: the next cheap build if nothing better arrives). Round-18
   `attn` still needs CB17's use of the comment count checked first.
7. **Before 11-14:** check that LT2's analysis (q0461) has run; if not, move `tte`, `chg1d_x_liq`, `dispgap` later, and
   `flow` before 11-16; `rewards` against E022 before 11-18.
8. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
9. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
10. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*`, `/tmp/se_*` scratch (Mac and host,
    now incl. `/tmp/se_resid_*`, `/tmp/se_fragile_*`, `/tmp/se_rsrev_*`) and old backfill logs.

## Notes for the other track
- The engine has read CH265 and CH268 itself (§37-§39). q0730's CH265 / CH268 lines are not needed by the builder; they
  stay your counts. If you number the engine-side `rsrev` idea, it is closed (gate not met).
- Census runs were short read-only scripts at nice 19 outside the queue; no job of yours was paused, cancelled or
  re-prioritised.
