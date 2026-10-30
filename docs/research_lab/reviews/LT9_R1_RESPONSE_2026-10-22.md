# LT9 R1 response, 2026-10-22

**Responds to:** `reviews/LT9_R1_CHALLENGER_2026-10-22.md` (REVISE; commit 118cf498).
**Reviewed text:** `docs/research_lab/LIVE_TESTS_9.md` sha256
`01c4989065c35743c47baa7c191f5956a1a734d9270a0c8e9c107605f82bef0a` (commit b2882734).
**Revised text:** `docs/research_lab/LIVE_TESTS_9.md` sha256
**`bbfeb62add0e24860947e9413025cece5bdfbd4f8ebbe46b27974b8b29a354e1`** (still DRAFT, not frozen; summary in its 6.4).

Every required change is made as worded. Every should-fix item is taken; none is declined. No threshold, floor, gate or
formula was loosened. Where a fix changes a planning input, the MDE is recomputed and the arithmetic is in the section
named. Nothing was read from data: no host, network, census output or evidence file. Nothing counted.

## Required changes

| # | R1 requirement | What changed | Where |
|---|---|---|---|
| 1 | Remove `f_binding`; CH213's F binds unconditionally with a CC9 gate F-MDE <= 1.0c and world 14 binding unconditionally; CH212's F a reported label fixed now | `f_binding` deleted from the text, spec list, tests and pin steps. F roles fixed per test by design: CH213 and CH214 binding (each with a census F-MDE <= 1.0c gate), CH212 a label (*far-future not excluded*), CH215 none. World 14 binds for CH213 whenever it is in `k_tests`. **Consequence: CH213's F-MDE is 2.24c (low) / 1.005c (high), so the new gate fails at both planning ends; CH213 is expected to die at census.** | 0 (table, expected outcome), 1.8 (table row 14, reported list), 1.8.1 world 14, 1.9 F rule and Supported, labels, 2 (falsification, planning MDE), 4 (falsification), 7 (CC9 rows for CH213 and CH212), 8.1 (analysis, spec), 8.3, 8.4 step 5, 10, 13 |
| 2 | CH213's panel is the market's status at its first unit; later opposite-status units excluded, counted `panel_switched` | Panel `panel_m` = `rewarded_k` at the market's first unit; later units whose status differs are excluded (`panel_switched`); `rew` is constant within market and so drops out under demeaning (removed from the regressor list). The block gate's "panel label never shifted" is now well defined. Planning MDE recomputed with a declared panel retention 0.85 | 2 (unit and population, state, primary statistic, planning MDE, missing data), 1.8 (block gate), 7 (descriptive print), 8.3, 10.1 |
| 3 | Binding world 4c: control 0.25, listed reward rows 0.15, omitted rows 0.30 | World 4c added, binding for CH213; 4r stays reported and its direction (against the hypothesis) is stated | 1.8 table, 1.8.1 world 4, 1.8 leak-world list and expectations, 2 (who would be wrong, gate worlds) |
| 4 | CH213 control `break x (log s_k - expanding-past mean of log s)` and binding world 3b with panels differing in mean(s)/2v | `relpos_k` frozen and `break x relpos_k` added as a control. World 3b added (binding; 160 markets a panel, normal level `q x 2v` with q 0.35 reward / 0.55 control, SD `0.25 x 2v`, AR 0.8; the direction that favours the hypothesis). Planning `VIF_w` 2.0 unchanged; the control enters the census's design-based MDE and its `VIF_w` gate | 2 (state, primary statistic, planning MDE), 1.8 table, 1.8.1 world 3b, 7 descriptive, 8.3, 10.1 |
| 5 | CH212 route B: tested term `om_k` on the two-class population | Route-B model now `om_k` alone on its two-class population (where `om_k = om_k x clob_dropped_k`); MDE unchanged (the contrast was already the class contrast) | 4 (unit and population, primary statistic, planning MDE), 8.3 |
| 6 | CH212 route A: require (causally) that the feed-listed programme end is after capture k + 1; report, never for the verdict, the subset still listed at the next feed capture | Route A requires the latest positive-rate end listed in the same pre-capture feed capture to be after the start of slot k + 2 (open-ended qualifies, `feed_end_open`; malformed NaN; earlier end `feed_end_soon`). New reported reading S2b on the next-feed-listed subset. Planning share 0.97 declared; MDE recomputed | 0 table, 4 (unit and population, secondaries, planning MDE), 7 (descriptive), 8.3, 10.1 |
| 7 | F-arm membership: end > t + 11 h (CH213), > t + 9 h (CH212) | Stated in 1.4 for all three (CH214's existing t + 9 h kept); failing units stay in the primary and are counted `f_end_short`. Planning effect not modelled (a 4 h end band is a small share); the census F-MDE uses the actual arm | 1.4, 2 (falsification, missing data), 3 (falsification, missing data), 4 (falsification), 7 (CC9 F-MDE gate), 8.3 |
| 8 | Print "broken at k - 1 given broken at k - 2" pooled only | Pooled over both panels only, never split by panel (reason stated) | 7 (descriptive, CH213) |
| 9 | CH214: non-fill volume noise of equal variance on the observed fill control in world 8; `max(0, zdD)` tested, `min(0, zdD)` a control; recompute MDEs; world 8 binding | Tested term `zdD+ = max(0, zdD)`, control `zdD- = min(0, zdD)`; twin and arm model use the lag's split the same way; S2 now reports the full linear slope and the departure coefficient; the label *departures, not arrivals* is retired (now the design). World 8's control is `log1p(u x 1[fill] + w)`, `w = 0.693 abs(N(0, 1))`, `Var(w) = 0.1745 = Var(u x 1[fill])`. Every CH214 world fits the new primary model. World 8 stays binding. `VIF_w` gate now on `zdD+` (planning 1.92 against 2.0); correlation gates on both `zdD` and `zdD+`; `r_gate` on the arrival parts | 0, 1.8 table, 1.8.1 (worlds 5-8, 13), 1.9 (twin), 3 (direction, state, primary, falsification, secondaries, planning MDE), 7 (CS9 row), 8.3, 10.1 |

## Should-fix items

| Item | What changed | Where |
|---|---|---|
| Whether census counts include planning's 0.8; reconcile count gates with kill lines (70 vs 68; 240) | Count gates use gross projected counts, no 0.8; the declared MDE uses the measured effective share in place of 0.8, never on top. CH213's 70 is kept above the recomputed 68 (lowering it would loosen a gate); its binding F-MDE kill line is about 154. CH212's 240 equals its MDE kill line (about 239). CH214's 1,000 sits above its slope kill line (454) and inside its F kill range (908-1,297). CH215's 30 a day is below its MDE kill line (51) | 7 ("What the census counts are"), 2, 3, 4, 10.1 |
| One feed-flag clock; CH213's decision time = capture k's last row receipt | One rule: the last usable feed capture finished before the start of the unit's eligibility capture j. CH213 **and CH212** decide at capture k's last row receipt (both use other markets' rows through `n_members`; CH213 also through the cell medians) | 1.2, 1.3, 2 (state), 4 (state), 8.3 |
| CH214: half-spread < v at both state sweeps | Added (`touch_out_of_band`); planning share 0.95 declared and the MDE recomputed | 0 table, 3 (population, planning MDE, missing data), 7 (descriptive), 8.3, 10.1 |
| CH215: which ends fall in the window; placebo reaches pre-window data; "day" = UTC day of T_e; ban or cluster reused controls; gate on `end_moved` | Ends with `T_e` in `[REGISTERED_UTC + 48 h, END_UTC]`; pre-window decisions counted; placebo's pre-window reach disclosed and backfilled only if CH215 enters; day = UTC day of `T_e`; reuse banned across ends with overlapping 48 h spans and the remaining reuse clustered (connected components of events linked by a shared control) for CR1, the sign-flip gate and event counts; CR9 gate `end_moved` share <= 20% (a declared convention). Planning MDE unchanged (no planning input changes) | 1.8 (sign-flip gate), 5, 7 (CR9 row), 8.1 (backfill), 8.3, 10.1 |
| Run CS9 after `T_E022`, otherwise label it | CS9 (q0644) runs only after `T_E022`; if it starts earlier CH214 carries *informed (E022)* | 7 (order, q0644), 8.4 step 5 |
| Bar LT9 staff from census-span data before the seal | No LT9 designer, coder or reviewer opens any census-input file before the seal commit, except header-only pre-checks and the restore's byte and sha256 checks | 1.6 |
| Disclose the late-LT8 kill at `T_LT7`, or allow an earlier pin with a rule-based `REGISTERED_UTC` | **Disclosure chosen.** Reason: a rule-based start would pin a date that depends on a later registration event and add reader logic the code check must verify, for a risk LT8's own timetable already makes small | 1.1 |
| Attribution limits into `config.EMBARGO` and `CANDIDATES.md` | At filing the limits are entered in both, by the engine track (not this branch); 8.4 step 8 verifies both before the pin | 9, 8.4 step 8 |
| No LT9 result can satisfy the economic check | Stated in the summary and in 1.10 | 0, 1.10 |
| Fix the scoring-rule wording in 1.4 | 1.4 now quotes the study's row ("two-sided only outside [0.10, 0.90]", i.e. one-sided quotes also score inside, at the reduced weight c = 3.0 sets) and notes round 14 called the reverse "the usual reading". It states the design did not read the venue's page and depends on neither reading, and that a re-read at the pin changes no value, rule, band or gate (R1 answer 12.7) | 1.4 |

Also recorded from R1's answers: the skip of (k - 1, k] and the quiet filter's role (1.3, answer 11.5); that CH212's
agreement table is seen before `T_LT7` (10, answer 11.2); sections 11 and 12 are kept as put, with a pointer to R1's answers.

## Recomputed planning MDEs (multiplier 3.47, DE 31, `C` = 252 x 0.8 = 201.6 effective captures)

- **CH213 interaction** (panel retention 0.85 on every cell): `n_rb` = 35 x 0.85 x 201.6 = 5,998 (low) / 176.4 x 0.85 x
  201.6 = 30,228 (high); `n_rn` 593,762 / 977,369; `n_cb = n_rb`, `n_cn = 2 n_rn`. Low: `sqrt(2/5,998 + 1/593,762 +
  1/1,187,524) = 0.018330`; `x 6.94 = 0.12721`; `x sqrt(31) = 0.70826`; `x 1.5 = 1.06239`; `x sqrt(2) =` **1.50c**. High
  **0.67c**. DE 51: 1.93c / 0.87c; a quarter of the low count 3.01c. **F-MDE (binding)** `x sqrt(2 / 0.9) = x 1.4907`:
  **2.24c / 1.005c, failing the 1.0c gate at both planning ends.** Kill lines (counted strict reward-panel breaks a capture,
  gross): MDE about 68, F-MDE about 154; the plan gives 30 / 150. **CH213 is expected to die at census.**
- **CH214 slope** (`zdD+` tested, `zdD-` control, in-band touch 0.95): units 1,544 x 0.95 = 1,467 / 3,242 x 0.95 = 3,081 a
  capture; `n_eff` 295,732 / 621,037. Half-normal arithmetic: `Var(max(0, z)) = 1/2 - 1/(2 pi) = 0.34085` (SD 0.58382);
  `corr(max(0, z), min(0, z)) = 0.15915 / 0.34085 = 0.46694`; pair VIF 1.27883; `VIF_w` = 1.5 x 1.27883 = 1.918. Effect scale
  kept at the `zdD` tercile gap 2.2 (conservative; the `zdD+` gap of 1.09 would halve the stated MDE). Low: `6.94 / 543.81 =
  0.012762`; `x 5.5678 = 0.071056`; `x 1.5 = 0.10658`; `x sqrt(1.918) = 0.14762`; `/ 0.58382 = 0.25285`; `x 2.2 =` **0.56c**;
  high **0.38c** (fix 9 alone: 0.54c / 0.37c, matching R1's rough 0.54c). DE 51: 0.71c / 0.49c. **A quarter of the low count:
  1.11c, which fails the 1.0c floor.** **F-MDE** `x sqrt(2 / (1 - r))`: **0.79c (r 0), 0.88c (r 0.2), 0.94c (r 0.3)** low,
  0.54c / 0.61c / 0.65c high (R1's 0.77-0.92c before the in-band factor): under the 1.0c gate, with little margin at the low end.
  Kill lines (counted units a capture): slope 454; F 908 (r 0), 1,135 (r 0.2), 1,297 (r 0.3).
- **CH212 route A** (end filter 0.97 on both classes): `n1` 35,322 / 96,719, `n2` 155,200 / 436,500. Low: `sqrt(1/35,322 +
  1/155,200) = 0.0058953`; `x 3.47 x 3 = 0.061370`; `x sqrt(31) = 0.34169`; `x 1.5 = 0.51254`; `x sqrt(1.3) =` **0.58c**
  (0.5844); high **0.35c**. DE 51: 0.75c / 0.45c; a quarter 1.17c. **The low planning end fails the 0.5c floor** (as in the
  draft). Kill line: about 48,240 effective omitted units, about 239 counted a capture. F (label): 0.87c / 0.53c.
  **Route B** (fix 5 changes the model, not the contrast): 0.61c / 0.30c (the draft printed 0.31c, a rounding of 0.305c); F
  0.90c / 0.45c (label).
- **CH215:** 2.23c / 0.92c, unchanged (no planning input changes).

## What the re-check should focus on

1. **CH213's binding F at planning.** The required gate (fix 1) makes CH213 a planned census death (F-MDE 2.24c / 1.005c).
   Nothing was loosened to rescue it. Please confirm that keeping CH213 in the design, to be dropped by its own census gate,
   is acceptable, rather than withdrawing it now.
2. **The declared new planning shares** (CH213 panel retention 0.85; CH214 in-band 0.95; CH212 end filter 0.97). All are
   unprobed conventions, chosen before data, and enter only the planning MDEs. The census measures each.
3. **CH214's `VIF_w` gate on `zdD+`** (planning 1.92 against 2.0). Applying the declared gate to the new tested term is the
   strict reading. Please confirm that this, and the doubled correlation gates (on both `zdD` and `zdD+`), are the intended
   reading.
4. **CH214's effect scale.** The slope MDE uses the `zdD` tercile gap, not the `zdD+` gap. This is conservative, and the
   *material* label uses the same scale.
5. **World 3b's construction** (q 0.35 / 0.55, SD `0.25 x 2v`) and **world 8's noise** (equal variance through
   `w = 0.693 abs(N(0, 1))`). Is each an adequate stress of its named confounder?
6. **CH212 route A's end rule.** Open-ended programmes qualify; the end is "after slot k + 2's start", read from the same
   pre-capture feed capture.
7. **CH212's decision time** moves to capture k's last row receipt, like CH213's. The reason is `n_members`. R1 named only
   CH213.
8. **CH215's control-reuse rule** (ban across overlapping spans, clustering for the rest) and the `end_moved` gate at 20%.

## Addendum: re-check fixes 1-6

**Re-check:** `reviews/LT9_R1_RECHECK_2026-10-22.md` (ACCEPT_WITH_FIXES; commit 2414b6bb). **Text before:** sha256
`bbfeb62add0e24860947e9413025cece5bdfbd4f8ebbe46b27974b8b29a354e1`. **Text after:** sha256
**`098aa3fb5f6765f08dcad3f85ad63ec70e29df65249413608f0f7ad5fd505b77`** (still DRAFT, not frozen; the freeze commit is
separate). Only the lines below changed. No gate, threshold, floor or planning value was changed; fix 2's planning
arithmetic and fix 5's gates are unchanged. Each edit carries the tag "re-check fix N" in the text. Nothing read from data;
nothing counted.

| # | Re-check requirement | What changed | Where (sections) |
|---|---|---|---|
| 1 | CH215 controls assigned in decision-time order over already-decided ends only | The reuse ban now assigns greedily in decision-time order (receipt of each end's decision feed capture, ties by `condition_id`); each end considers only ends already decided and takes its nearest candidates unused by them. The 8.3 test list adds a planted later-decided earlier-`T_e` end that leaves the earlier-decided end's controls unchanged | 5 (which ends, control reuse); 8.3 (CH215) |
| 2 | `zdD± = max/min(0, dD) / scale_census`; same for the lag twin and worlds 5-8 and 13; centred `zdD` only for S2 and the gates | Every live definition of the split is now at zero change of `dD` (and `dD_lag`), divided by the census scale and not centred; the centred `zdD` is stated to be used only for S2 and the census gates. Planning arithmetic (3, 10.1) unchanged; the 6.4 R1 history line left as written | 0 (CH214 row and summary), 1.8.1 (worlds 5-8, 13), 1.9 (CH214 twin), 3 (direction, state, falsification), 8.3 (CH214 split test), 13 (draft ledger CH214 line) |
| 3 | Exact instant for route A's slot k + 2 start; feed `end_date` parse rule; route A earliest consistent instant; CH215 `T_e` instant plus sensitivity; CC9 and CR9 print date-only and sentinel shares | New parse rule in 1.2 (offset timestamp; no-offset read as UTC; date-only `D` covers `[D 00:00Z, D + 1 00:00Z)`, `end_date_only`; absent/null/empty open-ended; year >= 2100 sentinel, open-ended, `end_sentinel`; other values incl. before 2020-01-01 malformed). Route A: slot k + 2's start is the nominal `grid0 + 2 h x (k + 2)`; each end at its earliest consistent instant; sentinel ends qualify as open-ended. CH215: `T_e = D 00:00Z` for date-only ends; open-ended, sentinel and malformed ends give no unit; reported sensitivity at `D + 1 00:00Z` (unit set unchanged) and a refit without date-only ends. CC9 (CH212) and CR9 print the date-only and sentinel shares. 8.3 tests for both readers | 1.2 (feed), 4 (route A), 5 (unit), 7 (descriptive prints, CH212 and CR9), 8.3 (CH212, CH215) |
| 4 | CH214's *material* label: name the scale, report the census `zdD+` gap beside it; the 1.0c power run states the scale | The label now reads per change of `zdD+` equal to the census tercile gap of the centred `zdD` (planning 2.2), stated to be a declared scale and not a `zdD+` tercile contrast (about 2x easier to earn), with the census `zdD+` gap between `zdD`'s top and bottom terciles reported beside it (planning about 1.09). The power run line states CH214's 1.0c is on that scale and its output states it | 1.8 (power run), 1.9 (labels) |
| 5 | Correct the reason for the 0.95 in-band share; sensitivity at 0.80 | Reason corrected: "half-spread < v at both sweeps" is the complement of the level state s >= 2v, not the 1-3% crossing rate. Sensitivity added: at 0.80 the slope MDE is 0.61c and the F-MDE 0.86c (r 0) to 1.02c (r 0.3), failing the 1.0c F gate at r = 0.3. Text only; no gate change | 3 (planning MDE (i)), 10.1 (CH214 row) |
| 6 | Three definitions: first-unit filters; `relpos_k`'s earlier units; control-cell median rows | (a) The first unit passes every filter of the paragraph including the band filter of its status at that origin (`band_changed` if rewarded, `ctrl_band_uncovered` if not), so it is itself a unit. (b) `relpos_k`'s strictly earlier units are the market's CH213 units only; `panel_switched`, `band_changed`, `ctrl_band_uncovered` and other excluded origins never enter. (c) The cell median and its >= 20 count use every carry-rewarded (`rewarded_k = 1`) non-sports ex-crypto row of capture k eligible under 1.4 at k with a finite `v`, regardless of `panel_m` and the other unit filters | 2 (unit and population, control band; state, `relpos_k`) |

**Optional world-3b rule (ruling 5) not applied.** Setting the per-panel q to the larger of the declared values and the
census medians of s/2v would add a census-fixed value to section 7's list and change 1.8.1 and 10.1, so it is not a one-line
change; world 3b stays as declared.
