# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 03:15 UTC+1 (2026-10-30 02:15Z), signal-engine autopilot session 31

## In plain English
- **New challenger: `se27_lgbm_stress`.** It tests whether big swings in Bitcoin / Ether volatility make all other
  markets behave differently in the next two hours (makers share one balance sheet). The idea passed its census, the
  "is there enough to test" check written down before it ran: 6 stress moments in 11 days (needed 5), and the BTC
  volatility measure is not just the market-wide activity level under another name (correlation 0.29, limit 0.8).
- **Built and backfilled on the host:** two new input families (`stress`, plus `slotfac`, the "how busy was the whole
  market in the last slot" control). 195 past captures each in 34 s, 0 errors; the values reproduce the census exactly.
  se27 should fit for the first time at today's refit (~13:40Z) and then predict at every capture.
- **Honesty guard written in advance:** se27 holds both the stress columns and the control, so beating se1 alone will not
  be credited to crypto stress. That needs a control-only reference model first (registered only if se27 beats se1 at
  its first 14-day read). An independent science review found no leakage; its three must-fixes were applied first.
- **Scores (unchanged, not a promotion read):** LightGBM models lead the logistic champion by ~0.045 nats on `dir_2h`;
  the 14-day minimum means first promotion reads ~11-04 (se27's own: ~11-13).
- Still needing the owner: a public website version of the feed (the North Star asks for an owner-approved web deploy).

## Live state (host)
- **Code:** main `f2e106fb` deployed 02:10Z; registry loads 28 models, se27 active.
- **Backfill (02:11Z):** `run_signal_engine.py features --max-items 30` under the tick lock, nice 19: 195 `stress` + 195
  `slotfac` tables, 34 s, peak 277 MB. Stress tables from 10-13 (inputs start), 7-day ratio finite from ~10-20 (68% of
  slots), same-clock-hour ratio 76%, control 97%. Log `/tmp/se_stress_backfill.log`.
- **Refit `q0512`:** daily, last fit 10-29 13:40Z (96 min, 3.5 GB). se27 adds one LightGBM x 4 targets (~5 min); its
  `res_7d` will be `insufficient_coverage` like the other aux models (28-day window starts before the inputs).
- **Score `q0513`:** daily, healthy (`tempfail` = not due). **Probe `q0518`:** still queued (priority 30) behind the other
  track's `q0116k` (5.5 GB, running).

## Embargo list (se27 added, not embargoed; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
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
1. **`stress` census (DESIGN_V1 §35):** run as written; passes. Script + output committed under `census/` (it was
   uncommitted when it ran; disclosed in §35).
2. **Families `se-aux-stress-v1` + `se-aux-slotfac-v1` (§36), challenger `se27_lgbm_stress`.** Both families read only
   engine files (kept), so they backfill after snapshot rows are pruned; they wait (`AuxNotReady`, counted as `waiting`,
   no error, no budget) rather than write a permanent NaN while an input table is still buildable; `AuxUnbuildable`
   when it never will be. Stress tables record every inputs file read with its sha256 (replay dependency).
3. Science review (read-only): causality / census / embargo PASS; must-fixes applied (census provenance, splitting the
   control into its own family + the attribution rule, inputs-read provenance). Also fixed a build-order bug it hinted
   at: a newest-first backfill would have written stress before earlier captures' klines existed.

## Next actions
1. **After the 10-30 refit (~15:20Z):** confirm se27 fitted on the 3 direction targets (fit.json) and predicts at the
   next capture; check the refit's peak RSS against 3,400 MB.
2. **Input monitor:** read `state/input_health.json` each session; `stress` / `slotfac` join it automatically (slot-level
   columns, so one failed kline fetch shows as a whole-family drop).
3. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
4. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written; record the decision.
5. **~11-13 (se27's 14 days):** if se27 beats se1 on `dir_2h`, register the slotfac-only reference arm (se1 + `slotfac`)
   before any credit to stress (§36). Later: CANDIDATES' spread / flat-class diagnostics on non-crypto rows (development).
6. **Round-18/19 families:** `attn` needs CB17's use of the comment count checked first; `disp` would be display only.
   Look at round 19 (CH262-CH269, recorded by the other track 10-30 ~02:20Z) for engine-first candidates.
7. **Before 11-14:** check that LT2's analysis (q0461) has run; if not, move `tte`, `chg1d_x_liq`, `dispgap` later, and
   `flow` before 11-16; `rewards` against E022 before 11-18.
8. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
9. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
10. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*`, `/tmp/se_*` scratch (Mac and host,
    incl. `/tmp/se_stress_census.py`, `/tmp/se_stress_backfill.log`) and old backfill logs.

## Notes for the other track
- The backfill was a 34 s, 277 MB run under the engine's own tick lock at nice 19, between passes; no queue job of
  yours was paused, cancelled or re-prioritised. The daily refit grows by about 5 minutes (one more LightGBM model).
- Ledger: one signal-engine entry appended; the ledger merge kept both sides (your round-19 / CB3 / LT13 entries first).
