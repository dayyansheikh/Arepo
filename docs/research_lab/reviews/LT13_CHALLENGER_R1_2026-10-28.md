# LT13 challenger R1, 2026-10-28

Reviewer: `science-reviewer` (independent, read-only). Draft `LIVE_TESTS_13.md` d35e2dd0, sha256 `5136e7b2…ce9f9`, 970 lines.
**Verdict: GO_WITH_CHANGES.** A re-check is required. No fix may loosen a line that round 18 kept.

## Go / no-go ruling
- **The map is not the census.** Round 18 puts the 0.25 and 0.90 lines under "Cheapest census … the worn LT12 seal or the
  ordered lane's fresh seal" (CREATIVE_HYPOTHESES_2026-11-01:457-467, 559-565). CH261 has "Kill criteria: none (a map)" (l. 858).
  Its only stops are the 40 line (l. 897-899) and the 690 line (l. 895). CH261 was also meant to run on [11-07, 11-17) (l. 840),
  but it ran on 10-20..10-28 without the design's filters (LT13:32-34). So neither 0.108 nor 0.755 is a measured census line.
  Recording `census_dropped` now would be a mis-record.
- **Is 7.75 days enough to kill?** For CH253, nearly: the placebo shortfall is structural (young batches), the reading is close
  to the design's (population_map_ch261.py:474-480), and n is 266,149. For CH252, no: the map's fee panel cannot be interpreted.
  `fee_class` has not changed since 0b4c103b (git log), yet the implied fee-free complete units (12,850) are 2.8x CH251's
  fee-free open rows (4,577), and the lumpiness moved from the fee-free cell (CH251_MAP:53) to the fee-on cell (CH261_MAP:26).
- **A value-based withdrawal is allowed (mission l. 102, 128).** It must be labelled `withdrawn_pre_census (map-informed)`,
  never `census_dropped` or "died at line X".

## MUST-FIX
1. **Headline undercounts the failed lines** (l. 36-47, 0 l. 77, 11 l. 965). On the map, CH252 fails three round-18 lines,
   not one: non-stationarity 0.108; "fee-on >= 5x fee-free" (l. 460: ratio about 0.008 at the median); cell coverage 0.096.
   Two are restated in 5 items 1-2. Say so plainly in all three places.
2. **Stage the build** (0 steps 3-6; 7.4). Write and freeze the census code first. Write the world, size-check and analysis
   code only for tests that survive the census. Worlds stay fully specified in 1.8.1 at the freeze; the code check verifies the text.
3. **Declare q0717's decision rule now** (7.5, 10 item 1), before it runs:
   (a) q0717 may change only the field reading of 1.4.3 and the census prints, never a threshold (0.25, 77, 5x, 60%/20, 95%, 5%, 0.90).
   (b) If q0717 does not explain the CH251/CH261 shift with a field-semantics cause that a declared reading rule fixes,
   CH252 is `withdrawn_pre_census (fee reading unresolved)`.
   (c) If CH252 is withdrawn, CH253 still goes to census under item 2.
   Run q0717 before the 8-day retention removes more of 10-20..10-21. Print its covered span.
4. **CH252 identification** (2.3, 5 items 2 and 4). 5 item 2 accepted. Round 18's age class (before or after 2026-03-30,
   l. 396-397) is the fee rule itself (l. 207); exact matching on it is a positivity failure by construction. Fee and age are
   then separated only by functional form, so: (i) condition (b) uses a restricted cubic spline in log age, knots declared now,
   none at the 03-30 step; (ii) the Supported text reads "fee-on/post-03-30 versus fee-free/pre-03-30 contrast", never "fee
   effect"; (iii) add the geopolitics-young versus fee-on-young contrast as a reported secondary (M6).
5. **No placebo change for CH253** (10 item 4). The nearby-batch alternative is rejected (a map-informed change to a rule-21
   line after it failed). Keep cap 30 (10 item 8); cap 10 (l. 532, 952) would raise placebo coverage by lowering m, a loosening
   after the map. Disclose round 18's own cap inconsistency (l. 507/941 against 532/952).
6. **Monotonicity claim** (l. 46, 3.4 l. 646-648). "Can only lower" is unproven (the tight rule changes both the decile base and
   m). Write "expected to lower".

## SHOULD-FIX
1. Non-stationarity "each cell" (CREATIVE_HYPOTHESES_2026-11-01:466-467): state that the rewarded cells are print-only, and why.
2. Report world 1 (S38) under the label-permutation gate as a diagnostic (1.8); the gate is not a valid null under composition.
3. population_map_ch261.py:16 says "same category", but the code (l. 474-480) applies none. Correct the docstring in a new commit.

## Rulings on section 10
1. GO with MUST 2-3. 2. Accepted with MUST 4. 3. Keep two-sided (LT12 R1 MUST 5). 4. Rejected (MUST 5). 5. Acceptable as an
extra binding gate; FL gate printed. 6. Sidecar primary, contingent on MUST 3. 7. Acceptable; freeze before `T_LT12c`, else
*informed (LT12 census)*. 8. Cap 30 (MUST 5). 9. Acceptable with label. 10. Planning only; the census decides.

## Verified
0.108, 69.65 < 77, 19,404, 704.4/1,704.6 kill constants, MDE 1.07c, 217,224, 0.058, P(no test) 0.828, 0.09 valid verdicts.
Implied units 12,848/910. Census span disjoint from the map spans. Placebo reading per map code l. 474-480.

## Not verified
The cause of the fee-panel shift. CH251's row definition against CH261's `units_complete` (l. 512-514). Retention 0.5.
Whether q0717 fits before the snapshots are deleted.
