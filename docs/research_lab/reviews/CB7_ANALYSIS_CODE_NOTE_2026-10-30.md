# CB7 analysis code note, 2026-10-30

Branch `feat/cb7-analysis` (from `chore/arepo-claude-setup` b919b4b7). Implements MUSTs 1-3 of `CB7_FREEZE_CHECK_2026-10-30.md`. Nothing is frozen, queued, deployed or run on host data.
Not done here: MUST 4 (already applied in b919b4b7), MUST 5 (census hash re-check at freeze, `science-reviewer` code freeze check), `model_specs/cb7_v1.json` (not created).

## 1. What was built

| File | Role |
|---|---|
| `backend/astrolabe/research_lab/cb7_astats.py` | decision rule (`ways_test`, small-G via `cb2_weather.small_g_pvalue`), bootstrap CI, top-5 drop, month sign, attribution, placebo summary, Holm / BY / k2, `OutcomeGate`, `require_freeze`, `load_census`, result and trial writing |
| `cb7_g_analysis.py` | G1: units, cost model, `g1_test`, `inverted_tail_gate`, `breakeven_g1`, robustness (i)(ii)(v)(vii)(ix)(x), reported tables, `decide`, `screen_g` |
| `cb7_x_analysis.py` | X1: vectorised definitions, `x1_test`, `route_gate`, wrong-side attribution, `time_shift_placebo`, robustness (i)(ii)(iii)(iv)(v)(viii), lead decomposition, `screen_x` |
| `cb7_s_analysis.py` | S1: the counted "not testable" line only (GS false); dependency on q0156 removed and recorded |
| `cb7_declaration.py` | `HYPOTHESES_CB7`, `declaration_sha256()`, `spec_payload` / `write_spec` (write-once), `mismatches` |
| `backend/scripts/run_cb7.py` | new `screen --family S|G|X` and `write-spec [--dry-run]` |
| `battery2.py` | `cb7_test`, `cb7_replication` in `KIND_RULES` (EXCLUDE, counted by the `creative_batch_7:*` count line) |
| `backend/tests/test_cb7_analysis.py` | 41 tests, synthetic fixtures only |

## 2. Hashes (at commit 08d6a431; change if any file below changes)

`declaration_sha256` = `8eb396ba74bcaecd2c21b54d58c17db5b649c77c7a4e11d7ab13f14a52e2438f` (rules_sha256 `05bf365c...21e9`).

| File (sha256 of bytes) | sha256 |
|---|---|
| cb7_declaration.py | 1f03b2419c3bb4eafb1811830296f357b39aebe589d70043e2b6bb57e3d12e9c |
| cb7_astats.py | cb48886e112530a8ed15b2275bce99470b5bb8d33402334e2e5a6750a464982b |
| cb7_g_analysis.py | 41109303b96154a1fe2285d5a48d9c2888095e295c06ac7e08ca366188b341fc |
| cb7_x_analysis.py | bdc38d563e1e6b3cc02ea40d1dedeb9d25280e20e6e392436dda0e1c033205b6 |
| cb7_s_analysis.py | c2883ca568382cdd8e3c2e16bdf700356e2ef5d88b8412c6eee1b2146adfbc0b |
| cb7_census.py | 351d436d039ef2558f3b4ad225f9d1a3c7a8417824494a0bd44dcff5ee82cb1d |
| cb7_xv.py | 0d8404e6fa9dd0b296b2864e88468d977e6064ac67d90483b1282ed95485c3a8 |
| cb7_common.py | 88dc0614f0c6296287fce93ba49ddea94e208b0af304a7bad88a2a6515ee29ef |
| scripts/run_cb7.py | 9584ac51ab15c2cf9c947e3502faae21cd58e6571361068962b49d10fa90a4a9 |

The declaration hash covers every UPPER_CASE constant and the source of every function / class in the four analysis modules, the source of each imported helper
(CB2 `small_g_pvalue`, `battery._cr_var_of_sum`, CB1 `holm` / `wilson_bound` / `half_spread` / `parse_outcome0`, CB6 `event_key_split`, `cb7_geo.theme_of`, `topic_of`, the
`cb7_xv` definition functions, census readers), the constant tables read (half-spread, fee and rebate tables, status-quo and theme patterns, census gates) and the committed
rules file hash. The spec additionally pins the file bytes above (so `cb7_declaration.py` and `run_cb7.py`, which cannot be inside the hash, are pinned there).
`screen` refuses (exit 2) on any mismatch. Re-take the hashes after any edit; the numbers above are the commit-time values.

## 3. Text-to-code map

| Design text | Code |
|---|---|
| 2.1 G1 cost: `a = min(m + half_spread, 0.999)`, `f = r a (1-a)`, `r` by `fee_category`, unknown / `other:*` 0.07 | `cb7_g_analysis.ask_of`, `fee_of`, `fee_rate_g`, `priced` |
| 2.1 binding spread robustness `a = m + max(half_spread, h_geo)` | `ask_of(h_floor=)`, `robustness["ix_measured_spread"]`; `h_geo` read from the pinned `census.json` |
| 2.1 X1 forgone rebate `rho r p(1-p)` from 2026-03-30 | `cb7_x_analysis.rebate_rate`, `XSet.finish` (`reb`) |
| 2.2 clocks: Kalshi `end_ts + 120 s`, mark at `<= u - 600` | `XSet`, `mark_at`, `in_skip_vec` (same definitions as `cb7_xv`; `test_x_vectors_match_census`) |
| 2.2 / (vii) end-date drop `closed_time < end_at - 2 d` | `build_units` (`early_close`), `robustness["vii_..."]` |
| 2.3 decision rule, small-G, `p = max over ways` | `cb7_astats.ways_test` |
| 2.3 G1 Stage-P only if batch Holm (alpha 0.01, k1 = 3) | `cb7_astats.batch_holm_label`, `cb7_g_analysis.decide` |
| 2.3 Stage-2 Holm k | `cb7_astats.stage2_k` (k2 = 1 if X1 advances, 0 if not, `None` until `results_X1.json`) |
| 2.4 floors (G1 +1.0c and R_ann 10%; X1 <= -0.5c) | `G.floor_ok`, `X.floor_ok` |
| 2.5 counting: `cb7_test` + `creative_batch_7:S|G|X` count lines, placebo lines count 0 | `cb7_astats.log_trials`, `finish` |
| 2.6 G1 break-even placebo (200 draws, seed 7174, p + tail gate, <= 1.5%) | `G.placebo_structure`, `G.breakeven_g1` |
| 2.6 X1 time-shift placebo (seed 7175, offset `[6 h, W - 6 h]`, p only) | `X.shifted_taus`, `X.time_shift_placebo` |
| 2.6 X1 wrong-side attribution (`X1' - X1 >= abs(X1)/2`) | `st.attribution(sign=-1)` in `evaluate_x1` |
| 2.6 robustness (i)-(x) | `G.robustness`; `X.robustness` |
| CB7-G inverted tail gate (99% lower Wilson bound on n/deff > pi* + 0.005; >= 10 YES clusters) | `G.inverted_tail_gate`, `G.g1_test` |
| CB7-G clustering (event x week; theme in the declared order) | `build_units` (`ew`, `theme` via `cb7_geo.theme_of`) |
| CB7-X route gate (mean mark-out over N u S' >= 0) | `X.route_gate` |
| CB7-X lead-implied decomposition (reported) | `X.lead_decomposition` |
| 2.7a / freeze check MUST 3: S1 not testable, p = 1, counted, no q0156 | `cb7_s_analysis.screen_s` |
| 5.2 screen refuses without the freeze file / before the declared date / on pin mismatch | `cb7_astats.require_freeze`, `load_census`, `run_cb7.cmd_screen` |
| 5.2 no outcome file before the declared time | `cb7_astats.OutcomeGate` is the only door; `cb7_g_analysis.screen_g` calls it once |

## 4. Implementation readings (A1-A20). Items marked AMENDMENT-RISK need the reviewer's explicit decision

- **A1 (AMENDMENT-RISK, no effect on the census counts).** 2.3 says "testability otherwise >= 100 units and >= 30 clusters per way" and "G < 15 in any declared way -> not testable"; both cannot be literal for a way with 15-29 clusters.
  Read as CB3 / CB8 do: >= 100 units; each EVENT-TYPE way (G1 event x week, X1 Polymarket event) >= 30 clusters; each non-event way (G1 theme, X1 UTC date) only the small-G minimum 15.
  With the census counts (G: 663 event, 177 theme; X: 70 events, 295 dates) the literal reading gives the same answers.
- **A2.** Fee rate for `other:*` is 0.07, as the 2.1 text says; `cb1_history.fee_rate` would give 0.05 (prefix rule), so it is not used. Conservative.
- **A3 (AMENDMENT-RISK, small).** G1's primary statistic is over RESOLVED units. The text lists "censored units -> Y = 0" under "worst cases and sensitivities (binding)", so censored / undecided units enter only robustness (v). A stricter primary (censored as Y = 0) is possible; (v) binds either way.
- **A4 (AMENDMENT-RISK).** CB7-X declares no worst case for (v). Adopted CB8-W's rule: S prints whose mark is unavailable enter with mark-out `max(0, mean mark-out of kept fills)` plus rebate; the estimate must stay negative and keep the p threshold.
- **A5.** The legs store only the Kalshi category. The rebate rate uses `REBATE_SHARE x DOCS_CATEGORY_RATE` when the lower-cased Kalshi category is a key of both tables, otherwise the LARGEST such rate (a larger rebate makes X1 harder to pass). Rebates only apply from 2026-03-30.
- **A6 (AMENDMENT-RISK).** The route gate is treated as binding for an X1 ADVANCE (it is "binding" in the text, with a verdict label "no route"). Computed WITHOUT the rebate the kept fills would earn (literal "mark-out"; harder to pass); the with-rebate value is reported. Wrong-side attribution does not block an advance (the text says so).
- **A7.** "YES event cluster" = an event key with a unit of Y = 1.0 (50-50 is not a YES cluster; stricter). Tail-gate deff bootstrap: 500 draws (CB1's `tail_bound` default), seed 7176 (the design lists seeds 7171-7176 without assigning 7176).
- **A8.** G1 placebo layout: one uniform per event key; neg-risk members of an event get consecutive sub-intervals (market-id order, width = the largest `a + f` among the market's units, scaled down by `1 / sum` if the sum exceeds 1, so at most one resolves YES); non-neg-risk markets are nested from 0 (comonotone). Only resolved units are redrawn. The "G1 p condition" is p < 0.01 (alpha 1), and a draw advances only if the inverted tail gate (including >= 10 YES clusters) also passes.
- **A9 (operational).** `screen --family G` exits 75 until `results_S1.json` and `results_X1.json` exist, so its batch Holm (k1 = 3) is final in its write-once file. Run q0148, then q0150, then q0149. G1 `advance` requires the Holm rejection; X1 `advance` does not (label only, as 2.3 says).
- **A10.** Unknown (None) checks never count as met: `advance` requires every check True.
- **A11 (AMENDMENT-RISK, operational).** The design gives no calendar date for the Stage-1 screens (only "after the CB7 freeze"). The freeze spec must carry `dates.screen_not_before_utc` (not in the declaration hash, must not precede the freeze); `screen` refuses before it and `OutcomeGate` refuses to open the guarded file before it. The freeze commit chooses the value.
- **A12.** Robustness (ii): for each way separately (G1: event x week and theme; X1: event and UTC date) the 5 clusters with the largest absolute summed contribution of net / mark-out are dropped; p threshold AND floor must hold in each way.
- **A13.** (iv) X1 months = UTC month of the print, >= 500 S prints; none qualifying -> unverified (not met). G1 quarters (end-date quarter) are reported only.
- **A14.** (viii) latency 300 s changes only the lag (window length stays 1,200 s). (i) alt mark: S prints whose pair has both sides' prints in `[s + 50 min, s + 70 min]`; compared with the main X1 mean.
- **A15.** The time-shift uses one offset per pair and draw for the pair's up and down events; if `W < 12 h` the offset is clamped to 6 h (no C1 window is that short per the design).
- **A16.** The cumulative count recorded is `battery2.cumulative_count()` on the trials file the run appends to; the host union step is run by the operator before the job (the code does not run it).
- **A17.** `h_geo` is read from the pinned `census.json` (`G.h_geo.h_geo_binding`); the census is read only if its sha256 equals the spec pin and its declaration hashes equal this code's.
- **A18.** X1 prints with an unavailable mark are excluded from the primary (counted in `print_classes` vs `n_S_mark_available`), per "unit unavailable if none".
- **A19.** Holm: a sibling with no Stage-1 file enters at p = 1 (only matters for S1 / X1 labels; G1 waits, A9).
- **A20.** `R_ann` hold = close - origin in days, floor 1 day; unresolved excluded.

## 5. Not implemented as written

- S1 slope, S placebos, marker shuffle, S2, S1-rep: never run (GS false; Stage 2 only if S1 advanced). `screen_s` refuses if a census ever recorded GS true.
- Reported variants: "G1 with status-quo questions" (not producible; section 10 deviation 1), "X1 with the 4 outcome-surfaced pairs re-added" (pair ids are not in the declaration), "+1c costs" (X1 has no cost shift).
- 2.6 (iii) / (vi) / (xi) are S or X items; (iii) for X1 is implemented (size-weighted sign), (iv) for G1 is reported only, as the text says.

## 6. SHOULD items left as TODO for the orchestrator (host access)

- G1 and X1 MDE from the census counts (G: 1,756 units, 663 event clusters; X: 23,760 non-sports S prints against the assumed ~75k) per 2.7 "MDEs recomputed from these counts".
- Per-named-theme unit counts for G1 (census lists 8 named themes with a unit but not the counts).
- G end-date checks: share of frame markets with `|closed_time - end_at| < 1 h` and `closed_time < end_at - 7 d` (census computed these for S only).
- Re-check the census declaration hashes at freeze (`write-spec` already refuses if `census.json`'s `cb7_xv_definitions_sha256` / `constants_sha256` differ from this code).

## 7. Freeze procedure these files support (not performed)

`python scripts/run_cb7.py write-spec --census-json <census.json> --freeze-utc <freeze commit time> --screen-not-before-utc <t> [--dry-run]` writes `model_specs/cb7_v1.json` once. It pins the
declaration hash, rules hash, source file hashes, `census.json` sha256, the seal pins and `h_geo` pins read from the census, `T7_X_list` = max(2026-11-03T06:00Z, freeze + 24 h),
`T7_S_rep_start` "not applicable", promote q0148 / q0149 / q0150, do not promote q0151 / q0152 / q0156, q0153-q0155 conditional on X1.

## 8. Not verified

- No host data was read. The column names of `legs.csv.gz`, `prints/<pair>.csv.gz` and `cross_venue/series/*.npz` (`kc`, `ps`, `win`) and the `outcomes_guarded.csv.gz` columns are taken from `cb7_census.py` / `cb7_xv.py` / `cb7_common.py`; fixtures were built to those layouts.
- Runtime and memory of the X screen on the real ~145k non-sports prints with 200 placebo draws; of the G placebo on ~1,700 units (the 400-unit fixture runs in seconds).
- The `h8_geo` seal was exercised only on a synthetic seal made with `h5_seal.seal_run`; real `drops.csv.gz` block values are only read for market ids (as in the census).
- Numerical reproducibility of `declaration_sha256` across Python / numpy versions (it hashes source text and `repr` of constants only).
- No `science-reviewer` pass; only the listed files were linted; the whole backend suite was not run (the `-k "battery2 or cb7"` selection passed).
