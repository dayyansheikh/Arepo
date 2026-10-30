# LT14 (CH262) challenger R1 (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: GO_WITH_CHANGES.** Draft `LIVE_TESTS_14.md` sha256 `9012d0d0…d47d` (verified) at e3d09a28. No defect forces a
REVISE. Two problems would let a Supported result be read as an edge (the gross's start point and the rung's description),
and the size check as written cannot detect an oversized p.

## MUST
1. **Name the start point honestly.** `g` starts at `mid_k`, the engine's label origin, before the decision time (1.4). The
   estimand, 0, 1.10 and 8 must call it "the label-origin gross; it starts before the prediction exists; it is not an
   executable entry". "At the touch" never without that qualifier.
2. **Audit the input clock of `P` at the freeze.** Every input of every family `P` uses must be received at or before
   `t_row(i)`; otherwise the reader refuses `P` (`DESIGN_V1.md:66-69`: `book` "can be credited for a move that has already
   happened").
3. **Describe the rung by where it came from.** 1.30c = `2(AS − h) − rebate` with h = 1.34c from F4/F5's 2.68c mean spread
   (`COST_MODEL.md:171,181`); the 10k-100k tier's own p50 half-spread 0.75c (`:147`) gives about 2.5c. Keep `H_A` = 1.30c
   (a lower bar makes Contradicted stronger) but delete "the most optimistic maker rung"; Supported prints the tier-spread
   rung beside the result.
4. **Make the size check able to fail.** Null worlds set the twin's mean to 0 and put the move on the unit, so F and the
   placebo can both pass; report the share of worlds with analytic p < 0.05 as a binding diagnostic for *analytic p
   oversized*.
5. **CH269 fee defect cause:** `census_map_ch269.py:951-952` builds the totals with a dict comprehension, so each capture
   overwrites the last; only the final capture survives (`20261030T023102Z`, `top_n` 1,059 = the reported total). Ledger
   note; the LT14 census code sums across captures, with a unit test.
6. **CH269 drafting line:** declared on CH262's object (ranked by `|s|`), but the map counted the signed decile (`:843`), with
   the engine's own `category` as scope (`:709`), not the pinned sidecar classifiers. Leave the map's outcome as recorded (no
   relabel); record "LT14 drafted on a defective count; |s| line unmeasured". The binding |s| gate (>= 100) stays in the
   census. A re-read of the CH269 inputs is optional: if done, declared in the ledger first, labelled *informed (CH269
   re-read)*, no declared value changed. Lower P(census A) from 0.80.
7. **Declare the order of exclusions** (`s_zero`, `sidecar_missing`, `tier_na`, `late`: before or after the `ceil(n/10)` cut)
   and the same `market_id` tie-break in the placebo's cut-off step 2.

## SHOULD
1. k = 1 now; B a reported arm (`H_B` 0.50c is not a round-trip rung; B fails its count line, mean 0.78 a capture, and its
   F-MDE line).
2. Design MDE uses the largest of the event, two-way and day SEs.
3. Latency label: a numeric trigger; `L` hardly varies within a capture, so a median-`L` split mostly splits by `t_off`.
4. Rename *informed (LT12 census)* to "census span shared with LT12" (LT14 reads no LT12 output).
5. Census tail: three slots after 11-17T00:00Z end at 04:31Z, not 06:31Z (`LIVE_TESTS_12.md:723`).
6. Collinearity (checked): primary has no regressors; M1 only `spread_k` (centre it). M6's controls are never listed: under
   within-market demeaning `category` and the neg-risk flag are zero and aliased, and decile membership is a function of
   `P`'s inputs. List the controls; adopt LT13's pivoted-QR aliasing rule.
7. `attrlimit_lt14` also covers computing `P`'s cents gross and top-decile hit rate by tier in any engine session; file a
   pre-freeze hold line in `CANDIDATES.md` now.
8. "Pinned `P`", not "the current champion"; freeze before 2026-11-07T00:00Z.
9. Supported prints `gbar − gbar_pl − H` and the M1 label in the same sentence.
10. Registry text "the cheapest trading cost": the 0.65c hold rung is cheaper; reword.

## Open questions
1. Parallel lane accepted (disjoint objects); readers under the heavy-job lock; disclose December thinning. 2. MUST 6.
3. F stays binding. 4. Placebo stays binding. 5. Keep 1.30c (MUST 3). 6. No latency exclusion (MUST 1-2). 7. k = 1.
8. Pinned sidecar classifiers. 9. Either; if `costs.py` is imported read-only, LT14 pins `costs.py` and the cost calibration
JSON itself (E026's pin expires 12-07). 10. Yes, a defect (MUST 5). 11. Pin at the freeze (SHOULD 8 deadline).

Arithmetic reproduced (0.0806, 0.20, 1.76, 0.49, B about 24 a capture, 0.22c, DE 1.3-2.8). Seed 20261814 unique.
**Could not verify:** sidecar field clocks within capture k; the `dir_2h` eligibility bit encoding (`el & 1`); real column
names (`dir_2h_up` / `dir_2h_dn`); whether demoted models keep writing prediction files; the `|s|` distribution.
