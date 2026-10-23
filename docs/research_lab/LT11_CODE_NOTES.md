# LT11 code notes: spec ambiguities and conservative readings

Code phase of the frozen LT11 design (`LIVE_TESTS_11.md`, sha256 `991100db...`, never edited). Each item below is marked
`# LT11 ambiguity Ax` in the code. The most conservative reading was chosen. None changes a threshold, formula or gate. For the
independent code-freeze check.

| # | Where | Ambiguity and reading |
|---|---|---|
| A1 | `scripts/run_live_tests11.py` | The design (8) names `scripts/research_lab/run_live_tests11.py`; the LT9 / LT10 runners live in `backend/scripts/`, so the runner does too. Queue drafts use `scripts/run_live_tests11.py`. |
| A2 | `series11_frame` | The vendored series treats `ask <= 1` as two-sided; the design says two-sided means `ask < 1`. Rows with `ask >= 1` are `one_sided` (counted). |
| A3 | `momentum_cols`, `ch234_units` | CH234's momentum controls (`own6`, `own24`, `chg_1h`) are multiplied by `sign(d)` (the sign-adjusted form); the design does not say. |
| A4 | `tick_rule` | The text excludes a tick change; an unknown tick (sidecar missing) is excluded too and counted `tick_unknown`. |
| A5 | `rv` block of the spec | `rv24` needs at least 10 observed 2 h changes in the 12-slot window (LT9 CH212's value); the design does not state it. |
| A6 | `ch232_units` | The first interval of a UTC day has its previous mid on the previous day; only same-day undefined mids exclude (`day_gap_market`), so no exclusion if that mid is undefined. |
| A7 | `ch232_units` | `v` and `log_rate` (the carry source's band and rate) are 0 for the control panel, which has no carry source. |
| A8 | `zcl_term` | The size-2 and 11+ arms use the nearest class scale of the census-fixed `zcl` scales (the census fixes the 3-5 and 6-10 classes). |
| A9 | `fee_dummies` | The `fee_category` dummy set is not fixed by the design: every category with at least 0.5% of the frame, the most frequent as reference. |
| A10 | `live_tests11_worlds.py` | The 15 worlds generate the analysis frame directly (declared controls computed from the simulated paths in the world code); LT10's worlds push synthetic captures through the reader's builders. The gate path, minima (16), estimator, F rule and point condition are the analysis' own. The generators are conventions and are not tuned. |
| A11 | worlds 3, 3b | The census `vnum_unknown` share `q` is not available to the worlds at generation; the 0.20 convention (floor 0.15) is used. |
| A12 | `ch232_units` | Re-crossing (`xr`) is measured per market on intervals of the same UTC day, among units that pass the zone and mover filters. |
| A13 | `pair_frame`, `member_states` | CH233's completeness and receipt-span universe: category-ok, non-augmented neg-risk events of 3-10 members; member-level filters (tightness etc.) do not affect pair completeness. |
| A14 | `ch233_units` | `nr_key_conflict` = a row key group spanning more than one Gamma event; counted, the group is excluded. |
| A15 | `census_ch233` | The CH233 block share is computed on the 16 captures of the unscaled census (no 21/days scaling). |
| A16 | `ch233_units` | The within-event SD of the census uses the `cl_sib` of the units. |
| A17 | `seal_coverage` | Twin coverage of at least 5.0 days is a coverage condition in the same sense as 7.0 (`census_unavailable (coverage)` when missing). |
| A18 | `census_ch232` | `cap_share` is computed over reward-status-finite units. |
| A19 | `run_once` | CH232's M3 (sweep depth) is implemented as `s0` / `s1` outcome files from the sweep root; absent sweeps give no file. |
| A20 | spec, reader | The CLOB-disagreement label (secondary) is not computed: there is no feed reader in LT11. |
| A21 | `seal_inputs`, `census_ch233` | The zero-bid sensitivity is counted in the census (`zero_bid_added_pairs`) only; no refit is run. |
| A22 | `live_tests11_analysis.py` | Secondary readings are limited to the holiday-excluded and month-start-excluded refits, crypto / non-crypto refits, attrition (Lee bounds on a >2 pp class differential) and gross economics; the arm, placebo (S1, S2) and M1-M3 secondary tables are not produced by `analyze` (their units are written by the reader and can be read from `live_tests11/`). Never verdict-bearing. |
| A23 | `point_condition` | The "difference p" label uses the interaction regression (`xw x traded`, `zcl` against `zca`, `xo x panel`) under the 1.7 rule; the design gives no formula. |
| A24 | `fit11` | With CH232's `G_minor`, the two-way and day p-values and the CI hull are computed as for the other tests; `p_event` alone uses `min(G_event, G_minor) - 1` df. |

## Not done / for the independent check
- The size-check worlds have not been run at scale (only shapes, seeding, refusals, planted-effect detection); projected
  run time is 8-20 h single core. A first dry run at `--dev` is the next step before the freeze check.
- `analyze` has been exercised only on synthetic reader output (loose floors); the verdict machinery is unit-tested.
