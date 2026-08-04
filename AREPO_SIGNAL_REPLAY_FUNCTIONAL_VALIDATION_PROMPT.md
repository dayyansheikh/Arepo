# Arepo Signal Intelligence and Replay Trust System
## Autonomous Functional Refinement and Validation Prompt

## Mission

You are the Opus lead product manager, quantitative research manager, data-engineering manager and QA manager for Arepo.

The user is leaving and will not be available to answer routine questions.

Continue autonomously.

Your job is to make **Signal Lab** and **Replay** the strongest and most defensible parts of Arepo from a functional, statistical and product-logic perspective.

This is not an aesthetics pass.

Do not spend time changing colours, fonts, spacing, branding or decorative layout unless a visual change is strictly required to make the functionality understandable or usable.

The goal is to produce a system that:

- finds meaningful current prediction-market signals
- distinguishes directional evidence from unusual but non-directional activity
- ranks signals sensibly
- explains what each signal implies
- measures uncertainty honestly
- evaluates past signals without look-ahead bias
- shows whether Arepo has performed better than simple alternatives
- grows its evidence base automatically through backend collection
- withstands scrutiny from experienced prediction-market professionals

Do not optimise for impressive-looking metrics.

Do not alter thresholds, samples, time windows or market selection merely to improve reported performance.

Do not claim an edge unless the evidence genuinely supports one.

A truthful inconclusive result is preferable to a misleading success claim.

Do not pause after planning.

Do not ask the user questions about reversible engineering, research or product decisions.

Stop only for:

- unavoidable external authentication
- paid-service approval
- secrets or credentials
- an irreversible deployment action
- a genuine ambiguity that cannot be resolved from the repository, documentation or current product intent

Use natural British English.

Do not use em dashes in user-facing copy.

---

# 1. Safe starting procedure

Before changing anything:

1. Read completely:
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
   - `FINAL_STATUS.md`
   - all Arepo implementation prompt files
   - all recent completion reports
   - `docs/DAYYAN_FINAL_LOCAL_ACCEPTANCE.md`
   - `docs/quant-final-review.md`
   - `docs/replay-product-review.md`
   - `docs/replay-regression-investigation.md`
   - `docs/component-availability-audit.md`
   - `docs/final-production-architecture.md`
   - current Signal Lab code
   - current Replay code
   - current Opportunity Board ranking
   - current Market Detail hypothesis logic
   - current alert eligibility
   - current collectors and scheduled jobs
   - recent Git history for all relevant branches

2. Inspect current official Polymarket documentation for:
   - market metadata
   - price history
   - public trade history
   - order-book data
   - WebSocket data
   - identifiers
   - resolution data
   - rate limits

3. Confirm:
   - current branch
   - latest commit
   - Git status
   - current local database
   - collector status
   - scheduled-job status
   - stored microstructure snapshots
   - stored prospective cohorts
   - stored reconstructed cohorts
   - stored synthetic cohorts
   - current backend test result
   - current frontend test and build result

4. Create a new branch:

`arepo-signal-replay-functional-validation`

5. Tag the current starting state:

`arepo-before-signal-replay-functional-validation`

6. Record the complete current baseline before modifying signal logic or Replay selection.

Create:

`docs/signal-replay-functional-baseline.md`

The baseline must include:

## Signal Lab baseline

- total signals
- directional signals
- observational signals
- inconclusive signals
- duplicate binary complements
- signal-strength distribution
- confidence distribution
- Research Priority distribution
- evidence-family distribution
- number of signals with one family
- number with two families
- number with three or more families
- component-availability rates
- stale-data rate
- signal age
- current load time
- repeated-request count
- current API response shape
- screenshots

## Replay baseline

For every available cut-off:

- exact cut-off timestamp
- mode
- market-universe size
- historical-data count
- eligible count
- directional count
- selected count
- correct
- incorrect
- flat
- pending
- unavailable
- hit rate
- confidence interval
- average signed forward move
- median signed forward move
- baselines
- provenance
- sample age
- screenshots

Do not alter thresholds before this baseline is recorded.

---

# 2. Independent agent structure

Deploy independent agents with non-overlapping responsibilities.

## Agent A: Dayyan functional acceptance reviewer

Act as Dayyan using Arepo to determine which markets deserve further research.

This reviewer wants:

- a short ranked list of useful current signals
- a clear Yes, No, Up, Down or Inconclusive interpretation
- evidence that makes sense
- confidence that is not arbitrary
- a clear distinction between strength and reliability
- a clear next research step
- a Replay page that shows what Arepo would have selected previously
- honest historical outcomes
- no unexplained technical noise
- no fake reassurance
- no requirement to understand Arepo's internal architecture

This agent must test the running product rather than reviewing screenshots or reports only.

Create:

`docs/dayyan-signal-replay-review.md`

## Agent B: prediction-market quantitative reviewer

Audit:

- universe construction
- market eligibility
- signal construction
- feature normalisation
- component weights
- direction resolution
- confidence calibration
- Research Priority
- evidence-family independence
- correlated evidence
- sample selection
- historical cut-offs
- look-ahead bias
- survivorship bias
- leakage
- baseline choice
- hit-rate interpretation
- Brier score
- log loss
- forward-price measurement
- resolution-based evaluation
- liquidity
- spread
- transaction-cost limitations
- threshold stability
- whether any edge claim is justified

Create:

`docs/signal-replay-quant-review.md`

This reviewer must reject any statistically weak or misleading conclusion.

## Agent C: historical-data and provenance reviewer

Trace every historical field from source to output.

Create a point-in-time availability matrix for:

- market existence
- market title
- close date
- outcome token IDs
- condition ID
- price history
- public trades
- order books
- spread
- depth
- wallet activity
- liquidity
- volume
- resolution
- category
- metadata
- evidence tags
- confidence inputs
- Research Priority inputs

For every field classify it as:

- available historically from an official source
- stored prospectively by Arepo
- reconstructable with limitations
- current-only
- unavailable
- synthetic

Create:

`docs/replay-point-in-time-data-matrix.md`

## Agent D: signal-system implementation reviewer

Review the entire signal pipeline:

- ingestion
- persistence
- feature creation
- normalisation
- direction
- confidence
- ranking
- API
- Signal Lab
- Opportunity Board
- Market Detail
- alerts
- Replay compatibility

Create:

`docs/signal-system-implementation-review.md`

## Agent E: Replay trust reviewer

Review Replay against this question:

> If I had opened Arepo in a comparable situation last week, which five to ten opportunities would it have shown me, and what happened afterwards?

This reviewer must judge whether Replay gives genuine reassurance or merely looks like a backtest.

Create:

`docs/replay-trust-review.md`

## Agent F: adversarial reviewer

Try to disprove the system.

Look for:

- hidden look-ahead
- current metadata leaking into historical selection
- cherry-picked cut-offs
- unstable API responses
- inconsistent evaluation horizons
- contradictory result summaries
- incorrect confidence-at-time
- duplicated binary markets
- evidence double counting
- stale values
- missing treated as zero
- selection changed after outcomes were known
- synthetic data leaking into real results
- misleading edge language
- metrics that change after refresh
- unhandled pending markets
- closed markets included incorrectly

Create:

`docs/signal-replay-adversarial-review.md`

## Agent G: independent final QA reviewer

After implementation, review the final running system independently.

Do not show this agent the implementation summaries until after its first test pass.

Create:

`docs/signal-replay-final-qa.md`

## Opus responsibility

Opus must synthesise the reviews and make final decisions.

Do not follow every suggestion blindly.

Resolve conflicts using this priority:

1. causal validity
2. statistical honesty
3. functional usefulness
4. consistency
5. reliability
6. simplicity
7. performance
8. aesthetics

Run the reviewers again after implementation.

---

# 3. What “best possible Signal Lab” means

Signal Lab is successful only if a user can answer these questions quickly:

1. What happened?
2. Which market and outcome does it affect?
3. Is it directional or merely unusual?
4. Which direction does it support?
5. How strong is the evidence?
6. How reliable is the evidence?
7. Why did it fire?
8. Which independent evidence families support it?
9. What would confirm the view?
10. What would invalidate the view?
11. Does it qualify for the Opportunity Board?
12. Can it be evaluated historically?
13. What should the user research independently?

The system must provide these answers from actual computed evidence.

## Functional success criteria

A high-quality Signal Lab must be:

### Selective

Do not treat every anomaly as an opportunity.

Classify signals as:

- Directional opportunity
- Directional observation
- Non-directional anomaly
- Insufficient evidence
- Data-quality warning

### Ranked

Support meaningful ranking by:

- signal strength
- confidence
- Research Priority
- recency
- time to close
- evidence-family count

Sorting must work in both directions where relevant.

### Consistent

The same signal must have consistent:

- direction
- strength
- confidence
- evidence families
- qualification status

across:

- Signal Lab
- Opportunity Board
- Market Detail
- alerts
- Replay

Different values are allowed only where the timestamp or available data differs, and the reason must be explicit.

### Non-duplicative

Do not show complementary Yes and No outcomes as independent opportunities when they are mathematically linked.

Consolidate binary complements unless:

- the evidence genuinely differs by token
- both sides contain distinct order-book evidence
- the distinction is explained clearly

### Honest about missing data

For every component:

- use a value only when valid
- keep missing as missing
- never convert missing to zero
- explain why the component is unavailable
- show required observations
- show last successful update
- show whether the collector is running
- remove unsupported components rather than displaying permanent empty placeholders

### Stable

The same request against the same frozen input must return the same result.

Add deterministic tests for:

- ranking
- direction
- confidence
- evidence families
- eligibility
- explanations

### Fast enough to use

Measure:

- cold response time
- warm response time
- upstream request count
- database query count
- payload size

Use caching and precomputation where safe.

Do not return stale data as current without labelling it.

---

# 4. Signal construction audit

Audit every component currently displayed or used.

Potential components include:

- recent price movement
- rolling price z-score
- volatility change
- large relative trade
- consensus-opposing flow
- late large trade
- concentrated flow
- clustered trades
- limited wallet history
- order-book imbalance
- spread change
- available depth change
- faster trading activity
- liquidity weakening
- cross-market divergence
- freshness
- data quality

For every component document:

- exact formula
- input source
- time horizon
- minimum observations
- normalisation method
- direction implied
- evidence family
- weight
- missing-data behaviour
- stale-data behaviour
- false-positive risk
- whether historically reconstructable
- whether available prospectively
- whether currently wired into the live model
- whether it materially changes output

Create:

`docs/signal-component-register.md`

## Remove false complexity

A component should remain only if:

- it has a valid source
- it is computed correctly
- it contributes meaningful information
- it can be explained
- missingness is handled honestly
- it is tested

Remove or disable components that exist only in copy, methodology or UI but do not affect the real model.

## Evidence-family independence

Audit whether multiple components are measuring nearly the same thing.

Do not count highly correlated price features as several independent lines of evidence.

Create a defensible family structure such as:

- price movement
- trade flow
- order-book state
- wallet concentration
- timing and clustering
- cross-market consistency

High-priority or high-confidence signals should require corroboration from genuinely different families where the data permits.

---

# 5. Directional view logic

Arepo must not be neutral on everything.

Arepo must also not force a direction where evidence is weak.

Find the best selective balance.

## Required categories

Each signal and market must be assigned one of:

- Favouring Yes
- Favouring No
- Favouring Upward repricing
- Favouring Downward repricing
- Direction unresolved
- Evidence insufficient

## Required measurement

Report:

- total markets screened
- directional markets
- unresolved markets
- insufficient-evidence markets
- coverage rate
- abstention rate
- coverage by category
- coverage by time to close
- coverage by evidence-family count
- coverage by confidence band

## Calibration

Do not choose thresholds based on the same outcomes used to report success.

Where data permits:

- choose thresholds on one period
- evaluate them on another
- use walk-forward evaluation
- record threshold changes in `DECISIONS.md`

If the data is too limited, retain conservative rules and say so.

## Product behaviour

Signal Lab should show all meaningful signals.

Opportunity Board should default to directional opportunities only.

Market Detail should use the same directional gate.

Alerts must use the same directional gate plus stricter confidence and quality conditions.

Replay must reproduce the gate as it existed at the historical cut-off.

---

# 6. Signal strength, confidence and Research Priority

These must remain distinct.

## Signal strength

Meaning:

> How unusual and directionally coherent is the observed market behaviour?

It should depend on the magnitude and combination of active evidence.

## Confidence

Meaning:

> How reliable is the signal estimate given data quality, completeness, freshness and corroboration?

Confidence must not be another name for strength.

Confidence should generally decrease with:

- one evidence family only
- missing components
- stale observations
- thin liquidity
- wide spread
- short history
- incomplete price history
- incomplete trade history
- incomplete order-book history
- inconsistent direction across components

Audit calibration and saturation.

Report:

- minimum
- median
- mean
- 90th percentile
- maximum
- percentage at 100%
- percentage above 90%
- confidence by family count
- confidence by data-quality band
- historical confidence versus outcome where sample permits

Do not display 100% unless the implementation can defend what 100% means.

Consider capping displayed confidence below 100% if it is an estimate rather than a mathematically certain probability.

## Research Priority

Meaning:

> How urgently this market deserves further research relative to the current universe.

It is not:

- expected profit
- probability of success
- betting recommendation
- edge estimate

Audit whether its inputs duplicate strength and confidence excessively.

Show which factors raised or lowered it.

Ensure the same ranking is used by:

- Opportunity Board
- historical top-opportunity Replay
- alerts where appropriate

---

# 7. What “best possible Replay” means

Replay is successful only if it answers:

> If I had opened Arepo at a real historical cut-off, which opportunities would it have shown me, what did Arepo believe at that moment, and what happened afterwards?

Replay is not merely a chart of old prices.

Replay is not a synthetic demonstration of what might have happened.

Replay is a trust and evaluation system.

## Core requirements

Replay must:

- use only information available at the cut-off
- use the same eligibility and ranking rules as the live product
- preserve historical confidence, strength and Research Priority
- show the top opportunities at that moment
- show subsequent price movement
- show resolution where available
- separate pending from incorrect
- compare with simple baselines
- report sample size and uncertainty
- explain missing historical features
- grow prospectively over time

---

# 8. Historical modes and whether synthetic is needed

Make a deliberate product decision.

## Prospective Replay

Definition:

Signals genuinely selected, ranked and frozen by Arepo at the time.

This is the strongest evidence mode.

It should become the primary long-term performance record.

Required:

- immutable cohort
- cut-off timestamp
- exact universe
- exact selected signals
- strength at cut-off
- confidence at cut-off
- Research Priority at cut-off
- component values at cut-off
- data-quality state
- later price observations
- final resolution
- code version or model version

## Reconstructed Replay

Definition:

Signals rebuilt later using only data provably available at the historical cut-off.

This is useful for expanding the sample but is weaker than prospective evidence.

Required:

- provenance label
- point-in-time field audit
- no current order book
- no current liquidity
- no current wallet state
- no current close date if it changed after the cut-off
- no current market status used in historical eligibility
- explicit list of unavailable components
- confidence reduced to reflect missing historical inputs

## Synthetic Replay

Synthetic data is **not required for the production trust experience**.

Synthetic should be retained only if it has a valid development purpose, such as:

- deterministic automated tests
- demonstrations when no real data exists
- onboarding examples clearly labelled as fictional
- stress-testing rare cases

Synthetic must:

- be excluded from all headline performance
- be excluded from any edge calculation
- never appear as the default Replay view
- never be labelled as current or prospective
- never be mixed with reconstructed or prospective samples
- live under a separate `Demo` or developer-only mode

If synthetic data provides no remaining test or educational value, remove it from the user-facing product while retaining minimal fixtures in automated tests.

Document the decision in:

`docs/synthetic-replay-decision.md`

The preferred production hierarchy is:

1. Prospective
2. Reconstructed
3. Synthetic Demo, hidden by default

---

# 9. Historical universe integrity

For every cut-off, reconstruct or load the market universe that genuinely existed then.

Audit:

- market creation time
- market close time known then
- market active state
- token identifiers
- eligibility
- liquidity requirement
- price-history availability
- category
- resolution state

Do not use today's active market list and filter backwards unless it is proven complete.

If a complete historical universe is unavailable:

- disclose the limitation
- label the universe as partial
- do not compare its sample size directly with today's Signal Lab
- prioritise prospective cohorts for future evidence

Show the funnel:

- markets known to exist
- markets with usable point-in-time data
- eligible markets
- directional markets
- selected top opportunities

---

# 10. Replay default user question

The default Replay experience should be:

## Last week's Arepo opportunities

At a clearly displayed historical cut-off, show up to five to ten opportunities Arepo would have ranked highest.

Do not force five or ten if fewer qualify.

Prioritise:

- same ranking rules as live
- meaningful liquidity
- sufficient historical evidence
- markets closing within a useful timeframe
- independent evidence families
- reliable data

Support lenses:

- closing within 24 hours
- closing within 3 days
- closing within 7 days
- all horizons

Do not imply closing soon means better.

For every opportunity show:

- historical rank
- market
- selected outcome
- directional hypothesis
- signal strength at cut-off
- confidence at cut-off
- Research Priority at cut-off
- evidence families at cut-off
- entry probability
- one-hour forward move
- 24-hour forward move
- seven-day forward move where available
- close date known at cut-off
- time remaining
- final resolution where available
- correct
- incorrect
- flat
- pending
- unavailable
- provenance

Define correctness consistently.

Do not mark a small favourable move as a success without a predeclared rule.

---

# 11. Replay evaluation horizons

Separate evaluation questions.

## Forward repricing

Did price move in the predicted direction after:

- one hour
- 24 hours
- seven days

## Resolution accuracy

Did the selected outcome ultimately resolve as predicted?

Do not combine forward repricing and final resolution into one hit-rate number.

A signal can correctly predict short-term repricing but not final resolution.

A market may remain pending.

Report both separately.

---

# 12. Baselines

Compare Arepo against causally valid alternatives.

Required where possible:

- no-change
- current implied probability
- price-only
- momentum
- always-up
- always-down
- order-book-only when historical order-book data exists

Do not silently substitute one baseline for another.

For each baseline document:

- prediction rule
- inputs
- horizon
- sample
- unavailable data
- result

Report:

- sample size
- correct
- incorrect
- flat
- pending
- hit rate
- confidence interval
- Brier score where applicable
- log loss where applicable
- mean signed forward move
- median signed forward move
- Arepo minus baseline difference

Do not claim outperformance from tiny samples.

---

# 13. Statistical evidence and edge

Define edge carefully.

Arepo has not demonstrated edge merely because:

- hit rate exceeds 50% on a small sample
- a few markets moved favourably
- confidence was high
- selected markets resolved correctly
- it beat one weak baseline once

A defensible edge claim requires:

- predeclared evaluation
- held-out or prospective sample
- meaningful sample size
- uncertainty intervals
- baseline comparison
- stable performance across time
- no look-ahead
- no survivorship bias
- reasonable liquidity
- consideration of spread and costs

Until then, use wording such as:

> Current results are inconclusive. Arepo has not yet demonstrated predictive advantage over the tested baselines.

Audit all user-facing and portfolio copy for edge claims.

---

# 14. Replay sample growth and self-sustaining operation

The browser being open must not be required.

Replay must grow through backend jobs.

Audit and verify:

- market snapshot collection
- microstructure snapshot collection
- prospective ranking
- cohort freezing
- forward-price observation
- resolution collection
- alert evaluation
- retries
- idempotency
- failure logging
- stale-job detection

Add a Replay data-status API and UI section showing:

- collectors running or stopped
- last successful run
- next scheduled run
- latest error
- stored market snapshots
- stored microstructure snapshots
- prospective cohort count
- reconstructed cohort count
- oldest cut-off
- newest cut-off
- unresolved cohort count
- code or model version

Explain:

- leaving the browser open does not grow the sample
- running backend collectors does
- one day may improve component availability
- meaningful performance evidence requires weeks or months
- historical data never stored may remain unavailable

---

# 15. Replay cut-off strategy

Review whether current cut-offs are useful.

Support:

- 24 hours ago
- 3 days ago
- 7 days ago
- 14 days ago
- 30 days ago
- weekly prospective cohorts

Avoid arbitrary cut-offs that produce misleading comparisons.

For each cut-off show:

- timestamp
- universe size
- eligible count
- selected count
- evaluation data available
- why fewer than five or ten may qualify

Prefer recurring prospective cut-offs aligned with the product's real usage pattern.

Document the chosen schedule.

---

# 16. Replay stability and reproducibility

A reconstructed cut-off must not change unpredictably on refresh.

Freeze or cache:

- exact cut-off
- exact universe
- exact selected rows
- exact entry prices
- exact model version
- exact provenance

If upstream historical data changes:

- retain the original frozen result
- record a revision
- do not silently rewrite past evaluation

Add reproducibility tests.

---

# 17. Cross-surface integrity

Create automated consistency checks.

For the same timestamp and market:

- Signal Lab direction equals Market Detail direction
- Opportunity Board qualification matches the gate
- alert eligibility matches stricter documented rules
- Replay uses the historical version of the same logic
- confidence is timestamp-correct
- strength is timestamp-correct
- Research Priority is timestamp-correct
- evidence-family count matches
- source identifiers resolve consistently

Create:

`docs/signal-replay-cross-surface-contract.md`

Make contradictions test failures.

---

# 18. Market identifier and routing integrity

Audit:

- Gamma market ID
- event ID
- condition ID
- token ID
- internal ID
- slug

Choose and document a canonical market identity.

Ensure:

- search result opens the correct market
- Signal Lab opens the correct market
- Opportunity Board opens the correct market
- Replay row opens the correct historical context
- saved market opens correctly
- alert link opens correctly
- mode selection does not make a valid market disappear

Add regression tests for known failing IDs:

- `2694364`
- `2822017`

---

# 19. Functional failure states

Signal Lab and Replay must never fail silently.

Implement clear states for:

- loading
- empty
- insufficient evidence
- no eligible historical markets
- partial historical data
- collector stopped
- stale data
- upstream API error
- database error
- invalid identifier
- unsupported historical reconstruction
- all selected markets pending

Each state must explain:

- what happened
- what data is missing
- whether the user should retry
- whether future collection can resolve it
- whether the limitation is permanent

---

# 20. Performance and reliability

Profile before changing.

Measure:

- Signal Lab cold and warm load
- Replay cold and warm load
- upstream API calls
- duplicate requests
- database queries
- historical price-history calls
- cache hit rate
- payload size
- frontend render time

Optimise through:

- precomputed signal snapshots
- batched requests
- safe caching
- pagination
- background refresh
- request deduplication
- database indexes
- lazy detail loading

Do not trade causal correctness for speed.

---

# 21. Automated tests

Add or update tests for:

## Signal system

- component formulas
- minimum observations
- missing data
- stale data
- evidence-family independence
- direction
- confidence
- Research Priority
- ranking
- complementary outcome consolidation
- deterministic output
- component availability
- collector integration

## Replay

- no look-ahead
- historical universe
- cut-off timestamp
- confidence-at-time
- strength-at-time
- Research Priority-at-time
- entry price
- forward prices
- pending handling
- resolution handling
- prospective immutability
- reconstruction provenance
- synthetic separation
- baseline calculations
- confidence intervals
- Brier score
- log loss
- multiple horizons
- closing-soon lens
- sample funnel
- reproducibility

## Cross-surface

- Signal Lab versus Market Detail
- Opportunity Board qualification
- alert eligibility
- Replay historical rule consistency
- identifier routing

## Collectors

- idempotency
- retries
- stale detection
- status reporting
- cohort freeze
- forward observations
- resolution updates

---

# 22. Manual acceptance

Run the product locally and test:

## Signal Lab

- useful ranked current signals
- directional filter
- observational filter
- every sorting option
- collapsed and expanded detail
- market links
- consistency with Market Detail
- confidence explanation
- missing-component explanation
- data freshness
- no duplicate complements

## Replay

- default last-week view
- each cut-off
- each closing-soon lens
- prospective data
- reconstructed data
- synthetic separated or hidden
- top five to ten selection
- confidence at cut-off
- strength at cut-off
- Research Priority at cut-off
- forward moves
- resolution outcomes
- baselines
- sample funnel
- data-status panel
- stable refresh
- correct market links

## Failure states

- collector stopped
- no historical data
- all pending
- upstream error
- invalid market
- stale data

Create:

`docs/DAYYAN_SIGNAL_REPLAY_ACCEPTANCE.md`

No locally testable item may remain Fail.

---

# 23. Iterative review loop

After the first implementation:

1. Run Agent A and Agent B.
2. Give their reports to Agent C, Agent D and Agent E.
3. Have implementation fix confirmed issues.
4. Run Agent F adversarial review.
5. Fix confirmed issues.
6. Run full tests.
7. Run Agent G final QA without showing it the implementation summary first.
8. Fix any final confirmed defects.
9. Run Dayyan acceptance.
10. Run Opus final inspection.

Repeat until:

- Dayyan reviewer accepts functionality
- quant reviewer accepts statistical honesty
- provenance reviewer accepts point-in-time integrity
- Replay trust reviewer accepts usefulness
- adversarial reviewer has no unresolved critical or major issue
- all tests pass
- documentation matches code

---

# 24. Credit and context fail-safe

If usage limits or context limits approach:

1. Stop launching new agents.
2. Finish the smallest safe work unit.
3. Run relevant tests.
4. Commit verified work.
5. Push the branch.
6. Update `CHECKPOINT.md` with:
   - completed sections
   - current section
   - files changed
   - tests run
   - failures
   - unresolved reviewer findings
   - exact next task
   - exact next command
7. Update `TASKS.md`.
8. Update `DECISIONS.md`.
9. Do not mark the task complete.
10. Exit cleanly.

A future session should be able to resume by reading the prompt and checkpoint without repeating completed work.

---

# 25. Completion gate

Do not claim completion until:

- Signal Lab meets the functional definition above
- Replay meets the trust-system definition above
- synthetic handling has a deliberate documented decision
- no synthetic data enters real performance
- point-in-time integrity is verified
- baselines are implemented or explicitly unavailable
- confidence is timestamp-correct
- current and historical logic is consistent
- collectors grow the prospective sample automatically
- tests pass
- Dayyan acceptance passes
- quant review passes
- adversarial review has no critical or major open findings
- Git is clean
- branch is pushed

Do not begin unrelated aesthetics work.

Do not begin external deployment unless the user explicitly asked for deployment in the current session.

---

# 26. Final report

Report:

1. branch
2. final commit
3. push status
4. Signal Lab baseline versus final
5. Replay baseline versus final
6. exact signal classifications
7. directional coverage
8. confidence distribution
9. evidence-family distribution
10. component availability
11. current top signals
12. cut-offs evaluated
13. market universe sizes
14. selected sample sizes
15. forward repricing results
16. resolution results
17. baseline comparisons
18. whether any edge is supported
19. prospective cohort count
20. reconstructed cohort count
21. synthetic decision
22. collector status
23. point-in-time limitations
24. performance results
25. backend tests
26. frontend tests
27. reviewer results
28. Dayyan acceptance
29. remaining research limitations
30. external blockers, if any

Use precise language.

Do not say Arepo is profitable, proven or edge-producing unless the evidence genuinely supports that claim.

Start now and continue autonomously.
