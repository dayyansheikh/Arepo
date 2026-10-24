# LT3 (E015-E019): challenger round 1, 2026-10-20

Reviewer: `science-reviewer` (read-only). Object: `docs/research_lab/LIVE_TESTS_3.md` at 1aa1500f (`feat/live-tests-3`). This is a design-only review: there is no code yet, so the code-level answers to LT2 faults 6 and 9 cannot be checked. Programme rule: one challenge, one response, then reject, revise or proceed.

**Verdicts:**
- E015: ACCEPT_WITH_CHANGES
- E016: REVISE
- E017: REVISE
- E018: REVISE
- E019: REVISE

Nothing is fatal. Every fix fits before `REGISTERED_UTC`, and none of them uses outcomes.

## Findings (ranked by severity)

1. **HIGH: E019's contrast is mechanically predicted by quote anatomy** (`LIVE_TESTS_3.md:377-386`).
   - In low-breadth intervals the movers are mostly lone one-sided quote changes, which are bounce by construction. High-breadth intervals are mostly parallel shifts. So D_HL > 0 follows from E015-S1's bounce with no "program update" at all.
   - The M1 sweep target does not fix this. A real book withdrawal that refills also reverts in the CLOB book.
   - **Fix:** add the share of one-sided and spread-change movers in the interval as demeaned controls. Pre-declare a binding label, *quote-anatomy composition*: it applies if the estimate on parallel and same-side movers only is below 50% of D_HL, or has one-sided p >= 0.05.
2. **HIGH: E019 cluster count is likely dominated by crypto ladders** (`:129-131`, `:387-396`).
   - The doc itself calls these "the natural high-breadth class". The high-breadth units may come from a handful of series. CR1 with a normal reference over few series is anti-conservative, and the floor of 50 clusters counts all clusters, not the ones that contribute high-breadth units.
   - **Fix:**
     - Compute p_series with a t reference on G_series − 1 df.
     - Set the floor at 50 or more series-or-event clusters that hold high-breadth units.
     - Census C4 prints: the top-series share of high units, and the share of neg-risk events with empty `series_slugs`.
     - Pre-declare: if one series family holds more than 50% of high units, the primary becomes ex-crypto and crypto becomes M2.
3. **HIGH: E016/E018 inputs and the census inputs are not where the doc says.**
   - `scripts/oracle/archive_retention.json:5-12` deletes `trade_samples/*` (except manifest and plan) after 3 days. The C2 input "CSVs on the host from 10-16" (`:448`) is therefore probably gone and has to be restored byte-for-byte (`restore_from_archive.py`).
   - The reader must consume each sample within 3 days. It reads online, so that is fine, but state it.
   - **Fix:** name the restored release and sha256s for C2, and add a retention rule that leaves `live_tests3/` alone.
4. **HIGH/MED: the "walked" construct is unvalidated** (`:274-276`; Q8).
   - `trade_sample.py:271` stores `float(it["price"])`, raw bodies are not kept (`keep_raw` off), and pandas writes the float's repr.
   - If the API price is `usdc/size` on 6-decimal micro-units, an on-grid fill shows up as something like 0.4500004, and the ">= 4 decimals" rule marks it walked. That would make W proxy small or fractional orders. The identical 23% walked share in both tick regimes (CREATIVE:98-99) fits an artefact as well as walking.
   - **Fix:** define walked as distance to the nearest grid point of the sidecar tick >= 1e-4. C2 prints the distance-to-grid histogram (counts only). Drop E016 if more than 20% of ">= 4 decimal" rows lie within 1e-4 of the grid.
5. **MED: E016's moderator is confounded with order size and life-cycle** (`:279-282`).
   - Larger orders walk, and HB1 already tested size features (pooled).
   - **Fix:** add these controls, all demeaned the same way: `x6·zSize` and `zSize` (mean notional per signed row), `x6·log hours-to-end` and `log hours-to-end`, and F4's `x6·zVOL`.
   - Without the hours-to-end controls, the distant-donor gate passes for a life-cycle trend, not for timing.
6. **MED: E015 has no binding label for temporary impact** (`:213-215`, `:234-238`).
   - Traded moves include impact that refills. M1 only separates Gamma quotes from the book.
   - **Fix:** add a secondary M3 on quote-only parallel units versus traded units whose quotes also moved in parallel (same anatomy). Label *impact/anatomy mechanics* if M3 is below 50% of D_PT.
7. **MED: E017 uses outcome 0 as YES** (`:317-319`; Q11).
   - Up/Down and head-to-head binaries carry no YES direction, so they dilute the effect or flip its sign.
   - Neg-risk members are about 92% of eligible pairs, because standalone binaries are 7.7% (CREATIVE:277). Restricting to them costs little power.
   - **Fix:** make the neg-risk-only population the primary. Standalone binaries become a secondary.
8. **MED: E017's `volume24hr` can lag the move it belongs to** (Q10).
   - If Gamma refreshes `volume24hr` late, an "attention-only" surge may be the volume of a move that happened in k − 1.
   - **Fix:** add `x_{k−1}` as a control, and define `SM` on max(|x_k|, |x_{k−1}|) >= 1c. C3 prints the counts.
9. **MED: the reader's timing exposes it to the late rule** (`:486-490`; Q13).
   - A cron run at :10 is 39 min after the pass starts. The measured 18 min pass (`COLLECTION_HOST.md:42`) predates the CB1/CB3/CB4/CB5 steps (600 s timeouts each) and the 5-minute snapshot retry (`arepo_pass.sh:24-35`).
   - If the run misses, the next one comes after slot k + 1, and every 2 h unit (E015, E019) of that pass is lost.
   - **Fix:** run every 20 min under `flock`, idempotently. Process only manifests that are `state=complete` and renamed into place. Pre-declare: if late losses exceed 2% of a class, the result is labelled.
10. **LOW: E015's MDE overstates the effective sample** (`:242-248`).
    - With expanding-past demeaning, only markets whose history holds both P and traded units identify D_PT. 30,000/100,000 counts every unit.
    - **Fix:** project from C1's parallel-and-traded market counts. The 0.5c floor probably still binds.
11. **LOW: E016/E018 sign** (Q5). The E007 convention is acceptable at flow level: mis-signing at random only attenuates. Add the C2 walked-versus-on-grid `side`/touch agreement count. Drop E016 and E018 if walked agreement is more than 5 pp below on-grid. For E018, mis-signing also breaks same-sign trains, so report M3 (unsigned trains).
12. **LOW: specify the look-back and permutation strata.**
    - State whether the expanding-past means include pre-window lines. They must come from the pinned code and be labelled.
    - The permutation strata are market × day with >= 4 units (`:141`), so many strata stay unpermuted. That is conservative, but print the share in C1.
    - E016/E018 primaries include sports while the others exclude it (`:267`). State this as a category parameter.

## LT2 faults: claims in §1.12 checked

- **1:** answered. A 12 h donor gap is exactly sufficient in both directions.
- **2:** answered for Gamma noise. Not answered for book bounce in E019 (finding 1) or impact in E015 (finding 6).
- **3:** answered.
- **4:** mostly answered. Residual truncation still depends on the future, but it is NaN, counted and labelled, which is what LT2 asked.
- **5:** answered.
- **6 and 9:** design-only; cannot be verified until code exists.
- **7:** partial (finding 10).
- **8:** generic rather than LT2-specific, but acceptable.

## Checks that passed

- The fields exist: `extract.py:26-53`, and the sidecar fields in `ext_sidecar.py:30-43`.
- The sports rule is at `cb17_census.py:66-69`.
- Sweep `best_bid`/`best_ask` exist (`book_sweep.py:50`), and the sweep covers the eligible universe.
- Trade timestamps strictly before origin, and `_sign`: `trade_sample.py:284-301`.
- Origin is the row's `received_utc` (`collector.py:12`).
- The queue blackout exemption is 500 MB (`queue_worker.py:65-66`).
- Holm and k are fixed at registration; a gate failure gives p = 1; economics are kept separate and the short-leg algebra is correct.
- The fixed window has no extension. The last 24 h target plus 3 h lands before the analysis at 11-15T12:00Z.
- The census gates are counts or feature-level only, so dropping tests before registration is acceptable.

## Rulings on §11

1. Yes, parallel minus traded is the primary, plus M3 (finding 6).
2. The coupling argument is overstated (an unsigned class barely biases a symmetric target), but the mix is acceptable: expanding-past is conservative.
3. Valid after finding 5's controls. p = 1 on failure is right.
4. Enough. Report two-day blocks for 6 h as a sensitivity.
5. See finding 11.
6. Keep E018 only if it passes the C2 degeneracy and correlation checks. Corr <= 0.5 is right.
7. Acceptable. Record each drop in the ledger with its counts.
8. Not shown to be faithful; adopt the grid-distance rule (finding 4).
9. Keep 2 pp. For 24 h, always report the bounds.
10. See finding 8.
11. Neg-risk only becomes the primary.
12. Plausible, unverified; C4 checks it.
13. Cron every 20 min (finding 9).
14. Agree, drop CH158.

## Not verified

- q0400's 93.3% figure and the P1/P2 counts.
- The actual pass duration since the CB steps were added.
- Whether the trade samples from 10-16 are still on the host.
- Whether sidecar presence holds for every capture.
- Whether daily crypto ladders carry `series_slugs`.
- The Data API price encoding.
