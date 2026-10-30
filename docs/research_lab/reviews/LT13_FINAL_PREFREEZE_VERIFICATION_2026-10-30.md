# LT13 final pre-freeze verification (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: FREEZE_AFTER_FIXES.** Two wording fixes are needed in the aliased-controls rule. The header can be updated in
the freeze commit itself, as LT12 did.

**Integrity.** `LIVE_TESTS_13.md` hashed to sha256 `0f7129cd…4af159` (1,233 lines) before the freeze commit, matching
3fec80a3.

**(1) MUST/SHOULD discharge.** MUST 1 at l. 732-737 and 468-471; MUST 2 at l. 944-947; SHOULD 1 (priors 0.10 x 0.6 x 0.9 =
0.054, annotations l. 871-872, 934, 970); SHOULD 2 at l. 774-778; SHOULD 3 at l. 842-843 and 1085; SHOULD 5 at l. 886-890;
refuse and print lists at l. 877-883. SHOULD 4 (aliasing rule, l. 739-747) is declared before data and deterministic, with
two gaps: (a) over-dropping: the fixed order dropped columns "until full rank" whether or not a column is part of the
dependency, which could remove non-redundant controls; dropping only redundant columns keeps the column space, so `b_bt`
is unchanged; (b) undefined end states (still rank-deficient after the three groups; "intercept-equivalent" undefined in a
demeaned fit; "`zs_bt` aliased" undefined).

**(2)** The remaining "unexplained" wording at l. 1129 (R1's open question, answered) and l. 1178 (dated draft ledger
block) is historical and acceptable.

**(3) Diff check e5dd31e3 -> 3fec80a3.** Every hunk adds a disclosure, an annotation, recomputed priors, the stage A/B
wording or the new aliasing and refuse/print bullets. No threshold, alpha, window, MDE target, placebo or estimand changed.
The CH253 census row (l. 907) is untouched.

**(4) Freeze completeness.** Apart from the fixes below, complete enough to freeze and to write stage-A census code
against. Stale CH252 lines are covered by l. 935 ("CH252's gates and prints in this section are not run").

**Fixes (minimal):**
1. Replace "drop columns ... in this fixed order until full rank" with: "in this fixed order, drop a column only if it lies
   in the span of the other retained columns (removing it leaves the rank unchanged); otherwise keep it and test the next
   one". Delete "never the intercept-equivalent".
2. Add: "Rank is computed on the demeaned controls without `zs_bt`; `zs_bt` is aliased if it lies in the span of the
   retained controls. If the controls are still rank-deficient after groups (1)-(3), or `zs_bt` is aliased, the fit is
   `NaN`, counted as `unavailable`."
3. In the freeze commit, following `LIVE_TESTS_12.md` l. 3-6: status block to "FROZEN (design text)", listing R1-full and
   this verification with the fixes applied, and the sha256 recorded in `EXPERIMENT_LEDGER.md`.

**Could not verify:** how the stage-A solver will implement the rule (no code yet); whether the 1,800 reclassified markets
are still open in November.
