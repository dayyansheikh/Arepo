# LT7 challenger review R1 (science-reviewer, 2026-10-22 ~00:30Z)

Scope: `docs/research_lab/LIVE_TESTS_7.md` DRAFT at 8c9f0328 (six round-12 candidates). Read-only.

**Verdict: REVISE.** The design is careful, but four defects decide outcomes: CH197's falsification-feasibility gate cannot
be computed as written, CH193 has a mechanical channel its falsification check cannot catch, CH194 is largely a re-test of
E002/E004, and CH191 breaks LT7's own gate rule. Several text contradictions also need fixing before any text freeze. A
re-check is needed after the fixes.

## MUST-FIX (most severe first)
1. **CH197's falsification-feasibility gate is undefined (section 7, CH197 row).** `r_w` uses within-market
   (expanding-past demeaned) values. The only possible pair is the 10-20 12:31Z unit with the 10-21T14:31Z sweep. The
   10-21 unit's k+13 sweep (10-22T14:31Z) is outside the seal: the sealed sweeps are 10-19T22:36Z to 10-21T22:38Z, 23
   passes (`seals/lt5_census_inputs_captures.json`, sha256 `fcd88926…8752`). That leaves one pair per market, and that
   unit is the market's first, so demeaning drops it. The gate returns NaN and CH197 dies by construction. Required: define
   `r_w` as the within-market correlation of `imbB` at every sealed pass pair 13 slots apart. Declare this now.
2. **CH193 has a stale-quote channel (6.A, 1.8.1 scenario 15).** "Volume rose, mid did not move" also describes a Gamma
   mid that was stale at k. If the target starts at `mid_k`, the catch-up shows up as a larger `a`. The lag arm does not
   see this, so falsification check F passes falsely. LT4 and LT5 label this risk "possibly mechanical (stale-mid
   catch-up)" (LT4:373, LT5:455); LT7 has no such label for CH193. Required:
   - move the target to `|mid_{k+2} - mid_{k+1}|` with the lag at (k+2, k+3] (answers Q6);
   - add a stale-mid world to the binding verdict-size scenarios;
   - add a sweep-mid label rule.
3. **CH193's missing-data rule contradicts 1.5.** 6.A says a missing `dV_lag` "enters as `log1p(max(dV_lag, 0))` with a
   flag", which imputes 0. Section 1.5 says such a unit leaves the falsification arm. Missing must mean excluded from the
   arm and counted. A negative `dV_lag` is observed data: state its clamp separately.
4. **CH194 is informed by E002 and E004, and they are not disclosed.** E002 confirmed a reversal of about 21% of the Gamma
   1h change (`chg_1h`) at about 5 h (slope −0.212, ledger ~409); E004 confirmed it over 11 periods. A "fresh" move
   (`chg_1h ≈ x`) reverting more than a "held" one is what that known result predicts. Required:
   - add E002/E004 to 1.11 and section 10, with an *informed (E002/E004)* label and the predicted sign stated in
     section 0;
   - either show content beyond that reversal (e.g. add `sign(x)·chg_1h` as a control) or drop CH194.
5. **CH194's basis gate cannot test `chg_1h` timing (section 7).** A check on `chg_1d` over 24 h is blind to offsets of
   tens of minutes, exactly the size that swaps held and fresh. Required:
   - a direct `chg_1h` timing gate on the CV7 trade samples, with a threshold declared now;
   - a gate on the share of exact-zero `chg_1h` (zero may be Gamma's default value).
6. **CH191's gate breaks LT7's own rule (1.0, LT5 R1 finding 1).** The grind/jump label is built over three intervals and
   adjacent labels share two steps; the label at k+3 is built from the same shocks as the target at k. Scenarios 4-5 use a
   Markov label independent of the target path, so they do not test this. Required: use the block (circular-shift) gate,
   or add a binding world where label and target come from one simulated mid path.
7. **The falsification-check MDE cap admits tests that cannot reach Supported (1.9, section 7).** Supported for the four
   level-built tests needs Δ (lead minus falsification) significant; with that MDE allowed up to 1.0c, a material 0.5c
   effect is mostly Inconclusive. Cap it at 0.5c, matching the floor (a tightening, not a relaxation). Put
   max(slope MDE, F-MDE) in the section 0 table.
8. **CH195 boundary text is false (section 2).** "k − 1 inputs after LT6's `END_UTC` + 24 h (automatic under 1.1)" is
   wrong: for pass 12-08T00:31Z, k−1 is 12-07T22:31Z, before 12-08T00:00Z. Follow LT6 R1 item 7's form (first origin
   12-08T02:31Z) or drop the clause.
9. **Embargo timing (section 9, 8.4 step 8).** `movetype` lapses 2026-11-22 (`config.EMBARGO`); se14_lgbm_movetype already
   isolates the traded flag and volume changes, which is CH193's state. Required:
   - apply the `movetype` and `book` extensions and the six new tokens when the design is accepted, and in any case before
     11-22; not as a registration step;
   - embargo until the later of 12-31T00:00Z and LT7's analysis commit.
10. **Import versus vendoring (8.1, Q9).** LT5 R1 ruling 9 required vendoring so that "later LT3/LT4 maintenance cannot void
    LT5 lines" (`live_tests5_base.py` header). live_tests4 and live_tests4_analysis changed 6-7 times since 10-12; under
    import, one edit voids all six tests. Vendor instead.
11. **CH191 hypothesis and rule disagree (section 3).** The hypothesis says three same-signed steps, but
    `sa >= 0.9, pc <= 0.5` admits (2c, 2c, 0). Either require every `|s_j| >= 1` tick with the same sign, or reword the
    hypothesis. Also fix the `rv24` cross-reference ("1.8 of section 7" should point to 6.B, and say whether it is `rv24*`).

## SHOULD-FIX
- **Planning MDEs assume DE 3.0.** E022's measured design effect on the same mover family was 6.196 (m_21 260.8; ledger
  ~3326). Re-derived: CH195 0.37c; CH191 at its count gate 0.67c (fails); CH194 about 0.27c. For CH197, event-weighted daily
  clusters could push it past 0.5c (not verifiable without data). Update section 0's expected fates.
- **CH193 dependence (1.7).** "Share nothing" is false: consecutive targets share `mid_{k+1}`, and a unit at k+1 exists
  only if unit k's target is below 0.005. Make scenario 15's path world a binding gate world for CH193.
- **CH197 gate worlds 7-8** have targets independent across days. Add one with market drift persistent across days.
- **No-read rule (1.6).** Extend the ban on reading E022, LT5 and LT6 outputs (including E022's coefficient on
  `log1p D_{k-1}`) to the period up to the pin, not just the text freeze.
- **CH193 semantic gate (Q7).** Add a rank-correlation check of `dV` against sampled interval notional, and a latency check
  on late-interval prints. As written, the 70% test mixes roll-off with timing.
- **Sweep timing.** Sweeps start about 5-7 min after the :31 capture (`20261019T223652Z`), so the "pre-move" sweep k−1 is
  taken after the move window has started. Disclose this.
- **End-date filter.** Tighten to > t + 7 h for the 6 h `c_skip` targets (LT3 used 7 h; LT4-LT6 used 3 h).
- **Smaller fixes:** cite the LT5 seal sha256 `fcd88926…8752` (commit 59b17969 is not an ancestor of 8c9f0328); the
  census's lag-slot loader must expose only `spread` or `volume24hr`, enforced by a unit test; fix the garbled small-wall
  definition in CH193; disclose ML-r4_book for CH197; record a dependency on the 8-day capture retention.

## Answers to section 11
1. The Δ rule is better than round 12's forms; the cap should be 0.5c (MUST 7).
2. Accept the labels for CH191. CH194's real threat is E002, not the far-future arm.
3. Disjoint origins plus registration before `T_V` is sufficient.
4. Accept, with VIF_w (liquidity in controls) and the residual-IQR gate.
5. The redesign removes the lag-0 problem at the target start. Keep CH192 census-first and disclose that the tested
   coefficient is `log spread`.
6. Move the target to k+1 (MUST 2).
7. Not sufficient (SHOULD).
8. Not valid for timing (MUST 5).
9. Vendor (MUST 10).
10. Accept.
11. Accept all four choices.
12. Acceptable with column guards.
13. M-B and M-C are adequate twins. M-D lacks a stale-quote world. Omitting the gate is fine (it can only raise the rate).
14. Agree.
15. Extend `book` and `movetype` to 12-31. A narrower token would not hide se14's scores.
16. Agree (exact value 3.4725).
17. A text freeze is enough only with MUST 9 and the extended no-read rule.
18. Acceptable.

## Per-candidate viability
- **CH195:** the most viable; likely passes its census; the falsification check is weak at DE ≈ 6.
- **CH191:** borderline; likely dies under the block gate or at DE ≈ 6.
- **CH194:** not viable as written (E002 contamination).
- **CH197:** dies as written (MUST 1); borderline after the fix.
- **CH193:** likely dies; invalid until MUST 2-3 are fixed.
- **CH192:** amply powered; likely dies on the pooled liquidity correlation; little novelty.

## Not verified
Event-size distributions (so the computed DE), what the CV7 samples cover, sweep completion times relative to the :55 cron,
and whether `attach`, `fit`, `verdict` and `gross` exist. `strata_of` lives in `live_tests4_analysis`, not `live_tests4`.
