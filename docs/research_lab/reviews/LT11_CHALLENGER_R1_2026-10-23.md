# LT11 challenger R1 (science-reviewer, read-only), 2026-10-23; filed by the orchestrator

**Verdict: REVISE** (re-check required after the fixes; none of the fixes loosens a threshold).

Verified: the ledger's draft sha256 `c1def3d4…` matches the file at ea67cd56 and HEAD. Arithmetic holds: 745 x 252 = 187,740; CH234 MDE 0.31c, F-MDE 0.46c with the 1.5 design factor; CH233 0.17c; CH232 0.69c; expected k 1.05; P(no test) 0.26. Kill lines (745, 58, ~500) reproduce. The CH240 map did not leak into the gates in a passing direction: the 745 and 60 lines are the stricter of the round's own pre-map values (6.1 item 13). Registry entry (`registry.json:1678-1700`): stage idea, verdict pending, no interim numbers, no edge language; complies with the README.

## MUST-FIX
1. **CH233: the target starts before the state is observed (1.3, 3.3).** `ds` starts at the member's own row at capture k; `cl_sib` uses sibling rows of capture k that may arrive minutes later, so part of the target interval precedes the state and a sibling's bid can react to the member's own spread change. E005 excluded groups whose member receipt times span > 120 s (ledger:320). Required: exclude any event-capture (at k - 1 or k) whose member `received_utc` span exceeds 120 s, counted as `receipt_span`; census gate: retained share >= 60% of complete pairs; print the span distribution.
2. **CH232: tick-created crossings (4.2, 4.3, 1.8.1).** At m_{k-1} = 0.10 (bid 0.09 / ask 0.11), an ask tick down to 0.10 gives mid 0.095: an outward crossing with the spread at its 1-tick minimum, so ds >= 0 mechanically at about the 1.0c floor; linear spread controls do not remove this floor effect; worlds 9-11 simulate a mid walk, not separate bid/ask quotes. Required: `|d_k| >= 0.01` (as CH234), counted `half_tick`; spread-at-k-in-ticks dummies (1, 2, 3, 4+) and own-spread-change-in-ticks dummies; a binding world with bid and ask each simulated on a 1c grid, mid as their average, 1-tick floor, spread reversion, no boundary effect.
3. **CH232: falsification twin undefined / low coverage (1.9).** "Approach-zone rule at k + 2" does not say whether a unit outside the zone gets twin 0 or NaN; if NaN, the arm is probably below 50%, so the test is always "falsification unavailable" and never Supported. "First of the day" read at k + 3 counts the lead crossing itself, so the twin is mechanically 0 whenever xo_k = 1 on the same day. Required: twin = 1[m_{k+2} in B and m_{k+3} outside B], 0 otherwise, NaN only if a mid is missing; no first-of-day condition on the twin; census gate: F-arm coverage >= 60% of primary units.
4. **CH232: market-level gap earlier in the day (4.2).** `day_gap` covers missing captures only, not the market's own mid being undefined at an earlier slot (one-sided, absent, not tight). Required: crossings defined only between consecutive slots where both mids are defined, never across a gap; a unit with any undefined same-day earlier mid is excluded, counted `day_gap_market`.
5. **CH234: `volume_num` could be carried forward (2.3 vs 2.7).** "The reader keeps ... the last volume_num" lets a stale k - 2 value stand in for k - 1. Required: store the value keyed by slot; if the k - 1 slot is missing, class `vnum_missing_km1`, never the last non-missing value; add a unit test (8.3).
6. **Distinct-event gates projected upward (7).** "Distinct events x 21 / covered days (pessimistic)" is anti-conservative (events recur across the window). LT10 corrected this ("over the covered days (pessimistic; never projected upward)", LIVE_TESTS_10.md:860). Required: every distinct-event gate (>= 500, >= 100) uses the unprojected count; projected forms printed only.
7. **"Unavailable" and "failed" merged at census (7, minimum covered days; 1.1).** A restore shortfall makes every gate NaN, a permanent drop in both lanes. Required: check coverage first; if it fails compute no gate and record `census_unavailable (coverage)`, distinct from `census_dropped`; declare now whether such a test may re-census in the ordered lane (recommended: yes, no gate value was seen).
8. **Lapse decided after an adjacent analysis (1.1).** The pin is planned 11-15..11-16, after T_E015, so the fast-lane lapse decision could be made with E015 known. Required: if the fast lane lapses after T_E015, CH234 carries *informed (E015)* in the ordered lane; if after T_E022, CH232 carries *informed (E022)*.

## SHOULD-FIX
1. "E022's measured 6.196" (lines 45, 529; 1.0 (iii)) -> "computed" (LT4:872 "DE_gate 6.196 = computed": m_21 measured, the 0.02 a convention).
2. CH234's count gate 745 sits at DE 6.196, which 1.0 (iii) says is "not the plan"; lesson (i) says the gate is set at planned values. State honestly that 745 is the lenient line and the F-MDE gate decides.
3. CH233 pools all hb but the mechanism works only near zero (E005: bid sum above one in ~0.2% of groups, ledger:317). Add a declared reported secondary `cl_sib x 1[hb_{k-1} <= 2 ticks]`; define `hb <= 2 x tick` as signed or absolute, which tick an event uses, matched to the map's definition.
4. CH233 completeness gate: define on pair-complete rows with `members_changed` in the denominator.
5. Augmented events: a reported arm outside the primary (E005 precedent, ledger:320).
6. K's optional chg_1d / chg_1w: indicator pairs; commit the header result before the seal; a column disappearing mid-window must not silently remove units.
7. Event-phase gate: state how a member's missing residual at a shifted capture index is handled.
8. Print the Kish G_eff and gate it at >= 15 (LT10 R1 should-fix 6), at least for CH232's crossing events.
9. Measure size-check time per world at the code freeze (LT10 was ~17 h; LT11 has 14 scenarios); if it does not fit by 11-15, declare the ordered lane before the seal.
10. 1.4.2 "does not depend on the reading" is overstated (under the documented reading one-sided farmers may add the dear side, narrowing the spread). Keep > 0, described as a declared direction.

## Rulings on section 11
- A1: keep the approach zone and 0.04 width; not the whole panel (the zone is the causal fix).
- A2: keep > 0 for both readings, wording per SHOULD-FIX 10; re-reading the page at the freeze suffices (fixes M1's side only).
- A3: "disclosed, no label" only if the census output sha256 and host timestamp precede T_E015; else *informed (E015)*.
- A4: F stays binding; a label-only F chosen for power is rejected.
- A5: keep the centred product; M4 and M2 stay reported.
- A6: keep the 5.0 floor; the planning 31 must not override a census computation; max(declared, design) plus SHOULD-FIX 8 suffices.
- A7: keep the pre-map >= 3 definition (changing it after seeing 0.59 would be map-informed); disclose that the gate is weak and `xr` is the real guard.
- A8: "Other" and placeholder members stay in the sum; augmented events a reported arm; requiring two-sided members is right; report the zero-bid variant as a sensitivity.
- A9: acceptable with SHOULD-FIX 6.
- A10: acceptable (exclusion rule declared whatever the level); add a capture-level variant to world 3.
- A11: a point condition is enough, not a significance condition.
- A12: the lapse rule is right; drops stay dropped except `census_unavailable` (MUST-FIX 7).
- A13: CH233 is a new object (spread target, innovation not level); M2 stays *informed (E005)*.

## Per-test recommendation
- CH234: keep (causal from k - 1 and k; missing volume_num class honest once MUST-FIX 5 is in; F binds by design).
- CH233: keep (most power); MUST-FIX 1 essential.
- CH232: keep only if MUST-FIX 2-4 go in before the freeze, otherwise drop (tick mechanics can produce the predicted sign; the F arm may make Supported unreachable; census odds 0.20; a census drop costs nothing).

## Not verified
Actual within-capture received_utc spans; whether volume_num missingness is capture- or row-level; data-release coverage of captures from 10-28; the venue's reward-rule page (no network); size-check runtime; the T_E015 and T_E022 dates.
