# D120 design: Fable 5.1 independent review (2026-10-11)

**Verdict: proceed with changes.** Nothing is fatal. All of the changes below are adopted by the lead.

## Verified
- **Root cause.** `sampling.py:259-263`; `event_group` is None and sits inside the stratum key (`selection.py:180`, `sampling.py:198-204`).
- **Frame facts, recounted from the retained D118 frame:**
  - `events[]` present on 100% of rows;
  - series present on 84.2%;
  - Gamma `category` on 0 rows;
  - `feeType` empty on 0.5%;
  - sports feeTypes cover 87.6% of rows;
  - no row has more than one event or series.

## Must fix
1. **Traceability.** Commit the series-group builder. Pin the sweep and snapshot ids by sha256. Commit the report JSON. Cite `P_fill_ok_and_ind_ge_3` for each scenario. State a lower bound of about 0.45 under S4q.
2. **Rename "independent pairs" to "group-disjoint pairs".** All origins occur within one minute and share run-level shocks. Phase 4 clusters by run.
3. **Predeclare disagreement between screening and origin state** (about 1 in 10 pairs).
   - Roles are fixed at screening.
   - The origin records the recomputed trigger state.
   - The evaluator counts disagreements descriptively and never relabels them.
   - Phase 4 must be told which computation (`origin_window` imbalance fields) to use.

## Improvements
- **Scheduled arm.** Keep it as a parameter set to 0 rather than removing it. Retain all screening assessments, with their inclusion probabilities, as the unconditional prevalence estimate.
- **Groups.** Union all events and series per row, not just `[0]`. Optionally add a frozen, versioned slug-token table for common underlyings (btc/bitcoin/eth…). This applies to slugs only, never to question text.
- **Category composition.** Report the category mix of the drawable strata and of the expected run.
- **Category storage.** Store it as a new field `fee_category` (selection v5). Keep the guard against collisions with literal values. Version the map.
- **Screening covariates.** Retain spread, best sizes and depth for every screened member, so that Phase 4 can register matched or post-stratified variants. Do not add covariate matching to D120.
- **No frame-contract change.** A blocked cursor causes a pre-selection abort, followed by a predeclared, bounded re-run of the frame only.
- **Reservation.** Add a protocol field `screened_slots` (receipts only, 64 KiB each), separate from the 12 origin slots, instead of a hand-measured profile. Today `panel_declaration.py:114-118` counts every screened member as an origin.
- **Simpler code path.** Extend `plan_sample` with `screen_per_stratum`, a one-per-group draw and `activate_screened=False`. A new evaluator is unavoidable.
- **Requests.** About 252 per run, not about 200.
- **What PASS licenses.** The mechanism, plus the population definition. It says nothing about fill reliability, which comes from only 6 Bernoulli trials. Effect studies need repeated runs: N runs give at most 6N pairs and at most N clusters.
