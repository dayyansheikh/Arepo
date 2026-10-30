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
| `backend/tests/test_cb7_analysis.py` | 43 tests, synthetic fixtures only |

## 2. Hashes (re-taken after the code-freeze-check fixes, branch feat/cb7-cf-fixes; change if any file below changes)

`declaration_sha256` = `cf84f91053385c371a875f39f72cd09bcc519dc446829b3b1fed47c7f481fd8e` (rules_sha256 `05bf365c...21e9`).

| File (sha256 of bytes) | sha256 |
|---|---|
| cb7_declaration.py | 5017283862f5638e141f0f37472883a8804a281573743aec67035a58b234b605 |
| cb7_astats.py | a9c8b20565906c32aa2c33f1752de6bd5fbe264b186cc18f3d7c8b57e21c70b4 |
| cb7_g_analysis.py | f0972287e2cbaf4dd729ca933a74523d46a55e8c4fe47f4a6df53dff79f51109 |
| cb7_x_analysis.py | 141ebdc653662f1809b2b6a65b9b2e8a040e20eb7c4490ff04975a73bb819cb8 |
| cb7_s_analysis.py | 070a10d3a432407a28fb58532e95c3c12cd28c3f1b300c1468d7a52b54f2770a |
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

- **A1 (RULED AN AMENDMENT AND REVERTED, code-freeze check 2026-10-30).** 2.3 says "testability otherwise >= 100 units and >= 30 clusters per way" (parent: CB6 2.3, "in each declared way"). An earlier reading lowered the theme (G1) and date (X1) ways to 15; the check ruled that less conservative and written after the census was seen. `MIN_CLUSTERS` is now 30 for every declared way (G: event_week 30, theme 30; X: event 30, date 30). No effect at the census counts (G: 663 event, 177 theme; X: 70 events, 295 dates).
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

- **A21 (undisclosed reading, check).** G1 robustness (i) also requires the p threshold (g_analysis ~l.251); the text asks only net > 0, so this is stricter.
- **A22.** The event x week clusters use the scheduled-end ISO week, not the resolution week (as the census does; outcome-blind).
- **A23.** The inverted tail gate re-implements `cb1_history.tail_bound` (same algorithm: one-sided Wilson on n/deff, `norm.ppf(0.99)`) instead of importing it, so that 50-50 outcomes count as half.
- **A4 disclosure.** The X worst case for robustness (v) is invented here; it touches only 6 of 23,760 S prints (23,754 with an available mark) and fills them with a value >= 0, which is conservative.
- **Placebo discordance (check SHOULD 1).** With comonotone per-unit draws the same market can resolve differently at its 30-day and 7-day origins (21 of 400 synthetic markets in the probe), so the G placebo has weaker within-market dependence than the real data and is a somewhat weaker check. Unavoidable if each unit's expected net must be 0.
- **Theme imbalance (check SHOULD 2).** The theme way has 177 clusters; the 8 named themes hold about 494 of 663 events and 169 clusters are singletons. CR1 with a normal reference can be anti-conservative here; the break-even placebo is the declared guard. Per-named-theme unit counts and G end-date shares (`|close-end_at| < 1 h`, `close < end_at - 7 d`) from sample.csv.gz / origin_prices (no outcomes) are still to be reported by the operator before the screen.

## 5. Not implemented as written

- S1 slope, S placebos, marker shuffle, S2, S1-rep: never run (GS false; Stage 2 only if S1 advanced). `screen_s` refuses if a census ever recorded GS true.
- Reported variants: "G1 with status-quo questions" (not producible; section 10 deviation 1), "X1 with the 4 outcome-surfaced pairs re-added" (pair ids are not in the declaration), "+1c costs" (X1 has no cost shift).
- 2.6 (iii) / (vi) / (xi) are S or X items; (iii) for X1 is implemented (size-weighted sign), (iv) for G1 is reported only, as the text says.

## 6. SHOULD items left as TODO for the orchestrator (host access)

- G1 and X1 MDE from the census counts (G: 1,756 units, 663 event clusters; X: 23,760 non-sports S prints against the assumed ~75k) per 2.7 "MDEs recomputed from these counts".
- Per-named-theme unit counts for G1 (census lists 8 named themes with a unit but not the counts).
- G end-date checks: share of frame markets with `|closed_time - end_at| < 1 h` and `closed_time < end_at - 7 d` (census computed these for S only).
- Re-check the census declaration hashes at freeze (`write-spec` already refuses if `census.json`'s `cb7_xv_definitions_sha256` / `constants_sha256` differ from this code).

### 6b. Operator notes added after the code-freeze check

- `write-spec` refuses unless |freeze_utc - now| <= 1 h (`--now-utc` exists for tests only). `spec.queue.promote` order is q0148, q0150, q0149.
- At screen time G compares the `verify_seal_copies` sha256s/states with `spec["seals"]` and refuses on mismatch.
- Union step (A16): run `scripts/oracle/union_jsonl.py` on the host before each screen and pass `--union-recorded-utc <time>`; without it the result carries `cumulative_count_label: "pre-union lower bound"` (feeds only the BY triage label).
- Crash recovery: if the job crashes after `results_<T>.json` and the Stage-1 copy are written but before the trial lines, a re-run refuses (write-once) and the test stays uncounted. Manual recovery: do not touch the results; append the four trial lines (`cb7_test`, optional placebo, `cb7_descriptive`, the `ml_explain` count line with n_tests 1) to the trials file with `provenance.append_trial`, using the results file's sha256 and `declaration_sha256` (copy the payloads from `cb7_astats.log_trials`), then verify `battery2.cumulative_count` rose by exactly 1.
- Queue drafts q0148 (S, not-testable mode), q0150 (X), q0149 (G, depends on q0148 and q0150) now parse with `build_parser()`; `not_before` is null and the freeze commit sets it to `screen_not_before_utc`.

## 7. Freeze procedure these files support (not performed)

`python scripts/run_cb7.py write-spec --census-json <census.json> --freeze-utc <freeze commit time> --screen-not-before-utc <t> [--dry-run]` writes `model_specs/cb7_v1.json` once. It pins the
declaration hash, rules hash, source file hashes, `census.json` sha256, the seal pins and `h_geo` pins read from the census, `T7_X_list` = max(2026-11-03T06:00Z, freeze + 24 h),
`T7_S_rep_start` "not applicable", promote q0148 / q0150 / q0149, do not promote q0151 / q0152 / q0156, q0153-q0155 conditional on X1.

## 8. Not verified

- No host data was read. The column names of `legs.csv.gz`, `prints/<pair>.csv.gz` and `cross_venue/series/*.npz` (`kc`, `ps`, `win`) and the `outcomes_guarded.csv.gz` columns are taken from `cb7_census.py` / `cb7_xv.py` / `cb7_common.py`; fixtures were built to those layouts.
- Runtime and memory of the X screen on the real ~145k non-sports prints with 200 placebo draws; of the G placebo on ~1,700 units (the 400-unit fixture runs in seconds).
- The `h8_geo` seal was exercised only on a synthetic seal made with `h5_seal.seal_run`; real `drops.csv.gz` block values are only read for market ids (as in the census).
- Numerical reproducibility of `declaration_sha256` across Python / numpy versions (it hashes source text and `repr` of constants only).
- No `science-reviewer` pass; only the listed files were linted; the whole backend suite was not run (the `-k "battery2 or cb7"` selection passed).
