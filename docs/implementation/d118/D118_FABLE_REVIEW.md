# D118 design: independent review by Fable 5.1 (2026-10-11)

**Verdict: proceed with changes.** Nothing is fatal; two items must be fixed before freeze.

1. **Diagnosis verified** in code:
   - controls are drawn only from untriggered members of the same stratum (`sampling.py:255-262`);
   - "unknown" liquidity bands create dead strata (`sampling.py:132-136`);
   - `event_group` is always None (`selection.py:180`);
   - no code defect.
2. **Must fix: the headline probabilities cannot be traced.** The committed `design_table2.csv` disagrees with the diagnosis table for the recommended row. Scenario and population codes are undefined, and no estimate script is committed. Commit the script and regenerate the numbers before the protocol cites any of them.
3. **Must fix: the stress scenario was reported selectively.** The harsher S4q gives 0.54 for liquidity 4×4 and 0.66 for spread 4×4. Because the observed pilots already reject the optimistic scenarios, the honest range is about 0.54–0.99, with the lower half favoured.
4. **The post-hoc liquidity restriction is legitimate but must be declared as post hoc.**
   - Liquidity is pre-t0 frame metadata (`metadata.py:73`), but it contradicts D116's "no price/book-based eligibility" rule.
   - The claim is limited to "control path exercised on temporal ∩ liquidity≥1000".
   - The Phase 4 trade-active frame is a different population.
   - Spread ≤ 0.10 is also defensible, but it ties selection to the book state the trigger reads.
5. **Dependence.** A pair formed by neg-risk or same-event siblings is disclosed as dependent and counts as mechanism execution only. One pair is an engineering check, not a statistical result.
6. **The timing risk is in a different place.** The binding constraint is origin concurrency: `concurrent_runtime.py:41-43` permits concurrency−1 origins. Raise `runtime_concurrency` to 8. The dry run must report max window age and audit duration, with abort above 40 s. The 300 s audit timeout literal is unchanged.
7. **Evaluator subclass.** The hard-coded 8/8 slots and `strata_limit` need overrides. E5's oversubscribed branch becomes live for the first time and needs a test. Equality of the table sha is a sound check.
8. **Decision rule.** A single run with no retry. If the result is another PASS_WITH_LIMITATION, it stands, the control path remains unvalidated, and the next step is the screen-then-activate re-architecture, not a D119 that changes the population again.

**Lead decision:** adopt every change and keep the liquidity ≥ $1000 filter. Implementation is delegated to Opus 5.5 at medium effort.
