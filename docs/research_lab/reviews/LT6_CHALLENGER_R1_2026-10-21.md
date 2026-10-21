# LT6 challenger review R1 (science-reviewer, 2026-10-21 ~16:00Z; `feat/live-tests-6` @ 5906c0b9)

**Overall verdict: REVISE.** Nothing fatal; several family-wide defects (few-treated-cluster inference, MDE gates
without VIF, seal dependency, memory plan, look-back timing) and substantive fixes for B. A short re-check of the
response is needed before any code.

| Test | Verdict |
|---|---|
| V (CH190) | ACCEPT_WITH_CHANGES |
| K (CH185) | ACCEPT_WITH_CHANGES |
| D (CH187) | ACCEPT_WITH_CHANGES (census-first) |
| B (CH188) | REVISE |

Verified: decision-time availability of every state, all targets at k+1 onward, planning-MDE arithmetic (V, K, D, B
recomputed), Holm and counting, seeds distinct from LT5's, no outcome fields used.

## Required changes
1. **Few treated clusters (D, B; 1.7, 1.8).** CR1 over all `G_event` clusters over-rejects with ~150 labelled events
   (MacKinnon-Webb). Use the event t with `G_treated - 1` df inside the p = max rule; the size check reports the CR1
   rejection rate in scenarios 6 and 7 at 0.0125 and 0.05.
2. **B volatility-clustering size scenario (1.8.1 scenario 7).** Add a binding scenario with stochastic volatility, a
   label hazard rising with current volatility, and the prior-|move| controls present (within market x day permutation
   does not keep intra-day timing).
3. **B control-class contamination (5).** No-birth = no newcomer and no lagged appearance in the event at k; exclude
   and count the others.
4. **B crypto exclusion (5, 7).** Use D's census category rule, or gate crypto <= 70% of births.
5. **MDE gates omit VIF (K, D, B; 7 and the table).** Put `sqrt(max(1, VIF_w))` from the census into all three gates
   (as LT5 R1 finding 4).
6. **V depletion kill line (7).** Bind on the 1c touch depth with an asymmetry gate fixed now, e.g. share(toward side
   halved) - share(away side halved) among traded movers <= 20 pp; print the round's original share.
7. **V and E022 boundary (1.1(c), 1.11).** V's first units read capture/sweep k-1 = 11-15T22:31, an E022 origin. First V
   origin = first slot whose k-1 inputs are at or after E022's END_UTC; key conditions and the freeze rule to E022's
   registration and END_UTC (LT4 is unregistered; E022 could drop); state that the family slides if LT4 slides.
8. **CB18 looks at D (1.6, 1.11, Q13).** SCREEN_18 files are read from 2026-11-11T08:00Z, possibly before LT6's pin,
   and CB18 reports an `end_date`-change class. (a) No LT6 designer / reviewer reads that output before the pin, or D's
   text is frozen at the accepted R1 text; (b) CB18 withholds that print for REP_18 origins at or after 11-16 until
   12-08T12Z. File (b) before the pin, or label D's S3 "partially seen".
9. **Seal dependency (7).** `seals/lt5_census_inputs_captures.json` is not committed yet (q0564 tonight). Cite its sha256
   once it lands, declare a fallback if its spans differ, and add minimum covered days (CV >= 1.5, CD/CB >= 5,
   CK >= 1.5; below that the gate is NaN and fails).
10. **Look-back timing (8.1, 8.4).** The reader writes `lookback` lines for captures in [REG-24h, REG) as they arrive;
    the backfill covers earlier ones; gaps are counted as `lookback_missing`.
11. **Memory plan (8.2).** Plan from LT3's measured 534 MB peak, not 300-420 MB; declare the final fallback if the split
    also fails (higher `mem_mb` with the blackout consequence and `.late` losses counted, never re-read).
12. **K train rule ambiguous (3).** A declared deterministic algorithm (e.g. greedy left to right, close the run when a
    gap leaves the band around the running median or the span exceeds 30 min, no overlaps); compare sizes as API
    strings or Decimals; unit tests.

## Recommended
- Raw target with expanding-demeaned regressors: print per-market label sums in the census (counts only); a
  both-demeaned sensitivity in the analysis (never changes a verdict); a non-binding size scenario where label
  incidence correlates with the market's level.
- Washout (D, B): exclude class-0 units in k+1..k+11 after an event in the same market.
- Gate power (D, B): a reported, non-binding planted-effect power run.
- D: disclose that `theta24` is survivor-conditional drift.
- B and D maker horizons: report the |move| over the widened pass beside `a22` / `y22`.
- K: add `H_unsigned` on K's own 2 h rows as a primary control (the census gate alone is near-vacuous).
- Engine: flow-family size-by-count features carry `clips`; any `se5_tte` revision column carries `deadline`.
- Seal archive within 48 h.

## Answers to the open questions
1 adequate with item 7; one window from 11-16. 2 skip target fine; M3 binding label; replace the halving gate (item
6). 3 block gate. 4 K distinct from E018; add `H_unsigned` as a control. 5 0.25 acceptable (0.5 as S2). 6 exact size by
string, 2 s minimum gap, distinct `tx_hash`, 30 min span; the band needs item 12. 7 keep D and B census-first with items
1-4 and 9. 8 keep `theta24` and `log T`; add an old-end >= 7 d reported subset. 9 fixed classifier acceptable; pin the
parse rules. 10 keep the 0.5c MDE gate; B's material label 1.0c. 11 adequate after items 3-4; optionally match fake
births on the event's leave-one-out |2h move| tercile. 12 keep rho 0.5 with size-weighted cluster size `Σm²/Σm`; keep
the 3.0 floor. 13 item 8. 14 acceptable given item 9. 15 agree; Thanksgiving-excluded sensitivity only. 16 net lane
fine after item 11. 17 agree. 18 extend `book`.

## Not verified
Release coverage of 10-12..10-21 captures and sweeps from 10-19T22:31 (orchestrator note: retention deletes only
files in a verified release with identical sha256, and daily releases continue; data-20261020 covers
10-18T04..10-19T02); the 3.388 multiplier derivation (conservative vs 3.08); `created_at` semantics,
`order_min_size` presence, `ts` units in the sealed files; se8/se10 feature lists.
