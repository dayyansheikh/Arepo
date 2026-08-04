# Arepo Edge-Research Infrastructure
## Autonomous Implementation Prompt

## Read this first: what this pass is actually doing

This pass is not being asked to make the current Replay result look positive.

It is being asked to turn Arepo into a system that can genuinely discover, measure and eventually prove whether it has a predictive edge.

At present, Arepo can display signals and reconstruct a very small historical sample, but it cannot yet make a credible edge claim because:

- there are no real prospective cohorts
- only a tiny reconstructed sample exists
- cohorts are weekly-only
- not every directional signal is frozen
- six-hour outcomes are missing
- depth and slippage are not fully modelled
- feature ablation does not exist
- walk-forward evaluation does not exist
- Arepo has not shown that it adds value beyond simple momentum

The purpose of this implementation is therefore to build the research and measurement engine that records predictions before outcomes happen, tracks what happens afterwards, compares Arepo with simple baselines, and determines which parts of the model genuinely add value.

The end result of this pass should be:

1. Arepo automatically freezes real predictions every six hours, daily and weekly.
2. Every valid directional signal is recorded internally, not only the visible top ten.
3. Outcomes are measured at one hour, six hours, 24 hours, seven days and final resolution.
4. Performance is measured both before and after spread, depth, slippage and fees.
5. Arepo is compared fairly with momentum, price-only and other baselines.
6. Feature ablation can identify which evidence families add value.
7. Walk-forward evaluation prevents overfitting.
8. Synthetic data is isolated from real evidence.
9. The backend can be deployed and begin accumulating real prospective evidence automatically.
10. The product can state clearly whether edge criteria are met.

This pass does not guarantee that Arepo will become positive.

It may show that:

- the current model has no edge
- only some evidence families add value
- Arepo works only for certain categories or horizons
- Arepo predicts short-term repricing but not final resolution
- momentum explains most of the apparent signal
- the model needs a later research iteration

That is acceptable.

What is not acceptable is manufacturing a positive result by changing thresholds, samples, cut-offs or eligibility rules after seeing outcomes.

A truthful negative or inconclusive result is more valuable than a misleading positive one.

---

# Mission

You are the Opus lead quantitative research, data-engineering, backend, product and QA manager for Arepo.

The user will not be available for routine decisions.

Continue autonomously.

Create a new branch:

`arepo-edge-research-infrastructure`

Preserve all fixes from commit `14729d7`.

Do not begin another broad audit.

The read-only audit is complete and should be treated as the implementation backlog.

Do not spend time on aesthetics, branding, colours, typography or general redesign.

Only make interface changes required to expose real research status, failure states or evaluation results.

Use natural British English.

Do not use em dashes in user-facing copy.

Do not pause after planning.

---

# 1. Safe starting procedure

Before changing anything:

1. Read:
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
   - `FINAL_STATUS.md`
   - `docs/DAYYAN_FINAL_LOCAL_ACCEPTANCE.md`
   - `docs/signal-replay-functional-baseline.md`
   - `docs/signal-replay-quant-review.md`
   - `docs/replay-point-in-time-data-matrix.md`
   - `docs/signal-system-implementation-review.md`
   - `docs/replay-trust-review.md`
   - `docs/signal-replay-adversarial-review.md`
   - `docs/signal-replay-final-qa.md`
   - the latest edge-research audit
   - current evaluation models
   - current evaluation engine
   - current replay statistics
   - current cohort CLI
   - current collectors
   - `render.yaml`
   - recent Git history

2. Confirm:
   - current branch
   - latest commit
   - Git status
   - current database schema
   - existing cohorts
   - provenance classes
   - current scheduled jobs
   - current backend tests
   - current frontend tests and build

3. Create a safety tag:

`arepo-before-edge-research-infrastructure`

4. Create the branch:

`arepo-edge-research-infrastructure`

5. Record the current state before schema or model changes in:

`docs/edge-research-infrastructure-baseline.md`

Include:

- real prospective cohort count
- reconstructed cohort count
- synthetic cohort count
- cohort cadence
- frozen fields
- outcome horizons
- baseline coverage
- execution-cost assumptions
- ablation availability
- walk-forward availability
- calibration availability
- collector status
- test counts

Do not change model thresholds before recording this baseline.

---

# 2. Prospective shadow evaluation

The public product may continue to show only the strongest five to ten opportunities.

The internal research system must freeze and evaluate every valid directional signal.

For every cut-off, store:

- every directional signal
- every selected top opportunity
- lower-ranked directional signals
- observational signals where useful
- abstained markets as labelled controls where useful

Each row must have an explicit role such as:

- public selection
- shadow directional
- observation
- abstention control

Do not allow the visible top-ten product threshold to restrict the research sample.

The research sample must be large enough to test whether:

- ranking adds value
- confidence adds value
- Research Priority adds value
- stricter selection adds value
- abstention improves performance

---

# 3. Multiple immutable cohort cadences

Implement real frozen cohorts for:

- every six hours
- daily
- weekly

Each cadence must have:

- a stable cadence identifier
- an immutable cut-off timestamp
- an immutable model version
- an immutable calculation version
- a unique cohort key
- an idempotent creation path
- protection against duplicate freezing

Do not confuse:

- ranking jobs
- resolution jobs
- forward-price jobs
- cohort-freeze jobs

A six-hour resolution job is not a six-hour cohort freeze.

Update:

- database schema
- repository layer
- services
- CLI
- tests
- `render.yaml`
- deployment documentation

---

# 4. Complete cut-off snapshot

For every frozen cohort store:

- model version
- calculation version
- exact screened universe
- universe size
- canonical market ID
- condition ID
- event ID where relevant
- token ID
- market title
- selected outcome
- direction
- signal classification
- signal strength
- confidence
- Research Priority
- rank
- evidence families
- every component value
- component availability
- missing-component indicators
- data-quality state
- entry midpoint
- bid
- ask
- spread
- available near-mid depth
- liquidity
- volume where valid
- data freshness
- market close date known at the cut-off
- time remaining
- intended evaluation horizons
- provenance class
- public-selection flag
- shadow-evaluation flag

The full screened universe must be stored, not only selected entries.

Once frozen, the cohort must never be rewritten after later prices or outcomes become known.

If corrections are required, create a revision record rather than silently mutating the original.

---

# 5. Outcome horizons

Collect and store outcomes at:

- one hour
- six hours
- 24 hours
- seven days
- final resolution

For forward repricing, store:

- midpoint
- best bid
- best ask
- spread
- available depth
- data timestamp
- whether the observation was exact or nearest available
- observation delay
- unavailable reason

For final resolution, store:

- resolved outcome
- resolution timestamp
- source
- pending status
- invalid or cancelled status where relevant

Use distinct result states:

- correct
- incorrect
- flat
- pending
- unavailable
- invalid

Do not combine forward repricing with final resolution.

A signal may correctly anticipate short-term repricing and still fail on final resolution.

---

# 6. Executable performance

Current midpoint-only movement is not enough to prove a usable edge.

Build a transparent execution model using:

- bid and ask
- spread
- available near-mid depth
- standard evaluation stake
- estimated market impact
- estimated slippage
- fees
- partial-fill handling where relevant

Report both:

## Midpoint performance

What the market midpoint did.

## Estimated executable performance

What a realistic entry and exit might have produced after estimated costs.

Do not count a favourable midpoint move as practical edge when it is smaller than estimated execution costs.

Document:

- standard stake
- spread-crossing assumption
- fee assumption
- depth consumption
- slippage formula
- partial-fill behaviour
- unavailable-data behaviour

Keep missing depth as missing.

Do not assume infinite liquidity.

---

# 7. Separate prediction objectives

Maintain two different research questions.

## A. Short-term repricing

Question:

Will the market move in Arepo's direction over the next one hour, six hours, 24 hours or seven days?

Measure:

- directional accuracy
- flat rate
- signed midpoint movement
- signed executable movement
- mean
- median
- uncertainty interval
- rank correlation
- performance by strength
- performance by confidence
- performance by Research Priority

## B. Final resolution

Question:

Does Arepo improve the probability estimate of the market's final outcome?

Do not use a directional call as though it were a calibrated probability.

Only compute:

- Brier score
- log loss
- calibration curves

when Arepo has a genuine probability forecast.

Keep repricing and final-resolution results separate everywhere.

---

# 8. Prospective baselines

Implement fair baselines on the exact same frozen observations.

Required:

- no-change
- always-up
- always-down
- recent momentum
- price z-score only
- price-feature model
- current implied probability
- order-book-only
- trade-flow-only
- full Arepo
- full Arepo excluding recent momentum

Where valid, also support:

- wallet-concentration-only
- timing-and-clustering-only

For every baseline document:

- inputs
- formula
- horizon
- required data
- missing-data behaviour
- sample size
- output type
- whether it is directional or probabilistic

Do not silently substitute a different baseline.

Historical reconstructed Replay may legitimately lack order-book-only or trade-flow-only baselines when those point-in-time inputs were never stored.

Prospective cohorts must support them because the data can now be frozen at the cut-off.

---

# 9. Feature-ablation framework

Build deterministic feature-ablation infrastructure.

Support:

- full model
- full model without price features
- full model without momentum
- full model without order-book evidence
- full model without trade-flow evidence
- full model without wallet-concentration evidence
- full model without timing-and-clustering evidence
- each evidence family alone
- price-only
- momentum-only
- order-book-only
- trade-flow-only

For every ablation, preserve:

- same cohort
- same cut-off
- same universe
- same outcome horizon
- same execution assumptions

Report:

- sample size
- correct
- incorrect
- flat
- signed movement
- executable movement
- uncertainty
- difference versus full model
- difference versus momentum
- stability across cadences and time windows

Do not claim a feature adds value merely because one tiny sample is positive.

The framework must be complete now.

The conclusions may remain unavailable until enough real prospective outcomes exist.

---

# 10. Walk-forward evaluation

Create explicit data partitions for:

- development
- threshold selection
- held-out evaluation
- prospective live evaluation

Prevent observations from being used in both threshold selection and reported evaluation.

Implement:

- partition metadata
- immutable partition assignment
- walk-forward windows
- minimum sample rules
- no-retuning guardrails
- tests proving separation

Do not choose thresholds on the same outcomes used to report performance.

Because the real sample is currently empty, the framework must be ready but the live conclusion should remain unavailable or inconclusive until enough data exists.

---

# 11. Calibration

Do not fabricate probability metrics.

Brier score and log loss are only valid when Arepo outputs a genuine probability forecast.

Build the infrastructure to support either:

- predicted probability of favourable repricing, or
- calibrated mapping from confidence to realised directional frequency

Define:

- minimum resolved sample
- calibration window
- held-out calibration evaluation
- recalibration frequency
- versioning
- fallback when the sample is insufficient

Until that minimum is met, display:

Calibration unavailable. Arepo does not yet have enough real resolved predictions to estimate calibrated probabilities.

Do not present confidence as probability unless calibration has validated that interpretation.

---

# 12. Synthetic data

Synthetic data is not part of the real edge record.

Retain synthetic data only for:

- deterministic automated tests
- rare-case simulations
- a separately labelled developer Demo mode where genuinely useful

Synthetic data must never enter:

- prospective cohort counts
- reconstructed cohort counts
- headline Replay performance
- baseline comparisons
- execution performance
- feature-ablation conclusions
- walk-forward conclusions
- calibration
- edge assessment
- portfolio claims

The default Replay experience must never show synthetic data as though it were real evidence.

---

# 13. Research-status API and product surface

Extend the existing research-status API and Replay status section.

Show real stored values for:

- model version
- calculation version
- cohort counts by cadence
- total frozen markets
- total directional signals
- total public selections
- total shadow signals
- total abstentions
- pending outcomes by horizon
- evaluable outcomes by horizon
- flat outcomes by horizon
- oldest cohort
- newest cohort
- last successful freeze
- last successful forward-price collection
- last successful resolution update
- next scheduled run
- latest collector failure
- sample by category
- sample by confidence band
- sample by strength band
- sample by evidence-family count
- baseline results
- midpoint performance
- executable performance
- whether edge criteria are met

The status section must make the current state obvious.

For example:

Arepo has not yet accumulated enough prospective evidence to determine whether it has an edge. The system is collecting frozen predictions automatically.

Do not hide an empty sample behind synthetic or reconstructed numbers.

---

# 14. Edge acceptance criteria

Arepo may claim predictive edge only when all of the following are true:

1. Predictions were frozen before outcomes were known.
2. The prospective sample meets the predeclared minimum.
3. Performance is positive after estimated spread, slippage and fees.
4. Uncertainty intervals support a positive result.
5. Arepo beats momentum, price-only and current-implied-probability baselines on the same observations.
6. Results remain stable across multiple walk-forward windows.
7. Results are not dominated by one category or a handful of extreme markets.
8. Feature ablation shows that additional Arepo evidence adds value beyond momentum.
9. Thresholds were not changed after seeing held-out or prospective outcomes.
10. The result passes independent adversarial review.

Until all criteria are met, use:

Current results are inconclusive. Arepo has not yet demonstrated predictive advantage over the tested baselines.

A temporarily positive hit rate is not enough.

A small positive sample is not enough.

Positive midpoint movement before costs is not enough.

---

# 15. Tests

Add tests for:

- six-hourly cohort creation
- daily cohort creation
- weekly cohort creation
- idempotent freezing
- duplicate prevention
- full-universe persistence
- every-directional-signal shadow inclusion
- public-selection versus shadow labels
- Research Priority persistence
- model-version persistence
- calculation-version persistence
- frozen immutability
- revision handling
- one-hour outcomes
- six-hour outcomes
- 24-hour outcomes
- seven-day outcomes
- final resolution
- flat classification
- pending handling
- invalid-market handling
- nearest-observation tolerance
- depth-aware slippage
- fees
- partial fills
- executable returns
- order-book-only baseline
- trade-flow-only baseline
- full-model-without-momentum baseline
- feature-ablation determinism
- walk-forward partition separation
- synthetic exclusion
- calibration minimum-sample guard
- research-status reporting
- scheduler idempotency
- collector retry
- collector failure recovery
- no look-ahead

Run:

- full backend tests
- ruff
- migrations
- bootstrap tests
- frontend TypeScript
- frontend lint
- Vitest
- production build

---

# 16. Independent review

Deploy independent reviewers for:

## Quantitative validity

Check whether the evaluation genuinely tests predictive value.

## Prospective-data provenance

Check that every frozen input existed at the cut-off.

## Execution modelling

Check spread, depth, slippage, fees and fill assumptions.

## Feature ablation

Check whether the framework can determine value beyond momentum.

## Walk-forward design

Check that development and evaluation remain separated.

## Adversarial review

Try to identify:

- leakage
- survivorship bias
- overfitting
- cherry-picked samples
- mutable cohorts
- synthetic contamination
- inconsistent denominators
- execution-cost understatement
- duplicated markets
- baseline mismatch

## Dayyan functional acceptance

Check that the running product makes it clear:

- what is currently known
- what is still unknown
- how many real predictions exist
- whether edge criteria are met
- what data is being collected next

Fix every confirmed critical or major issue.

Do not claim multiple Opus reviewers ran unless they genuinely did.

Use the strongest independent subagents available and disclose the actual reviewer structure.

---

# 17. Deployment readiness

This implementation is not useful if it remains local indefinitely.

After all local implementation and tests pass, produce the exact deployment handoff needed to start continuous collection.

The deployment handoff must include:

- database migration order
- required environment variables
- web-service command
- six-hourly freeze command and schedule
- daily freeze command and schedule
- weekly freeze command and schedule
- forward-price commands and schedules
- resolution-update command and schedule
- collector commands and schedules
- expected cron count
- idempotency checks
- health checks
- first manual run order
- first production acceptance test
- rollback procedure
- monitoring procedure

Do not perform paid or irreversible deployment actions without user approval.

But do complete everything locally required so deployment can begin immediately.

---


# 17A. Architecture validation and requirement traceability

Before implementation is considered complete, perform a full architecture review proving that every requirement in this prompt is supported end to end.

Create:

`docs/edge-research-architecture-review.md`

and:

`docs/edge-research-requirement-traceability.md`

## Architecture review

Review the complete path from live Polymarket input to stored prospective evidence and final Replay output.

Trace:

1. upstream market discovery
2. canonical identifier resolution
3. price collection
4. trade-flow collection
5. order-book collection
6. wallet or participant evidence where available
7. feature calculation
8. direction assignment
9. confidence calculation
10. Research Priority
11. public ranking
12. shadow-evaluation inclusion
13. cohort creation
14. cohort freezing
15. database persistence
16. forward observation
17. final resolution
18. baseline calculation
19. feature ablation
20. walk-forward assignment
21. execution-cost calculation
22. research-status API
23. Replay display
24. monitoring and failure recovery

For each stage document:

- owning module
- database table
- input contract
- output contract
- timestamp semantics
- provenance
- retry behaviour
- idempotency behaviour
- failure state
- test coverage
- production job responsible
- required environment variables
- operational dependency

Identify and fix:

- missing stages
- duplicate responsibilities
- circular dependencies
- incompatible identifiers
- mutable historical state
- race conditions
- jobs that can run in the wrong order
- jobs that rely on browser activity
- locally available state that will not exist in production
- SQLite assumptions that fail on PostgreSQL
- transaction-pooler incompatibilities
- prepared-statement problems
- timezone inconsistencies
- schema bootstrap or migration risks
- secrets exposed to the frontend
- frontend dependence on unavailable backend routes
- silent collector failures
- unbounded API calls
- rate-limit risks
- duplicate cohort creation
- duplicate forward observations
- duplicate resolution records

## Requirement traceability matrix

Create one row for every numbered requirement and every substantive bullet in this prompt.

Each row must contain:

- requirement
- implementation status
- exact code location
- exact schema location
- exact API or CLI route
- exact production job
- exact automated test
- exact manual acceptance step
- deployment dependency
- remaining limitation

Allowed statuses:

- Implemented and verified
- Implemented but awaiting real data
- Blocked by external setup
- Not implemented

No requirement may be marked complete based only on documentation or a placeholder interface.

No requirement may be marked complete if:

- the code path is not called
- the database field is never populated
- the cron is not defined
- the test uses only mocked behaviour that differs from production
- the production environment lacks the required dependency
- the output is synthetic when the requirement calls for real prospective data

The final completion claim must be based on this traceability matrix.

---

# 17B. Production-equivalent local dry run

Before handing off for deployment, run a production-equivalent end-to-end dry run locally.

Use the production database path where feasible, or a PostgreSQL test environment matching production behaviour.

The dry run must prove the following sequence works without the browser being open:

1. discover markets
2. collect current prices
3. collect order-book data
4. collect trade-flow data
5. calculate signals
6. rank opportunities
7. freeze a six-hour cohort
8. freeze a daily cohort
9. freeze a weekly cohort
10. persist the full screened universe
11. persist public and shadow signals
12. collect a one-hour outcome using controlled test time or fixtures
13. collect a six-hour outcome using controlled test time or fixtures
14. collect a 24-hour outcome using controlled test time or fixtures
15. collect a seven-day outcome using controlled test time or fixtures
16. record a final resolution using controlled fixtures
17. calculate midpoint results
18. calculate executable results
19. calculate baselines
20. run ablation
21. assign walk-forward partitions
22. update the research-status API
23. display the resulting real or controlled prospective cohort in Replay

Use controlled clocks or deterministic fixtures for future horizons during tests.

Do not fabricate production evidence.

The purpose is to prove the pipeline works, not to create a misleading historical performance record.

Create:

`docs/edge-research-end-to-end-dry-run.md`

Record:

- commands run
- database rows created
- job order
- timestamps
- outputs
- tests
- failures
- fixes
- screenshots or API evidence
- cleanup or isolation of test records

Test records must be clearly marked and excluded from real performance.

---

# 17C. Deployment architecture guarantee

The deployed architecture must begin collecting real prospective data automatically as soon as the required external services are configured and the jobs are enabled.

Verify that production includes:

## Persistent database

- PostgreSQL-compatible schema
- migrations or safe bootstrap
- connection-pool configuration
- transaction safety
- indexes for cohort, signal and outcome queries
- backups or recovery plan
- no dependency on local SQLite files

## Backend web service

- health endpoint
- readiness endpoint
- database connectivity check
- collector-status endpoint
- research-status endpoint
- CORS configuration
- authentication-secret validation
- structured logs
- error reporting
- no development-only startup assumptions

## Scheduled jobs

At minimum, define and verify jobs for:

- market and metadata refresh
- price and microstructure collection
- six-hour cohort freeze
- daily cohort freeze
- weekly cohort freeze
- one-hour forward observation
- six-hour forward observation
- 24-hour forward observation
- seven-day forward observation
- resolution update
- alert evaluation where retained
- stale-job or health monitoring

Jobs may be consolidated only when:

- ordering remains correct
- retries remain safe
- idempotency remains proven
- failure of one step does not silently prevent all later steps

For every production job specify:

- exact command
- exact UTC schedule
- expected runtime
- required variables
- dependency order
- idempotency key
- retry behaviour
- timeout
- success condition
- alert condition
- manual rerun procedure

## Frontend

- production API base configured
- no localhost dependency
- no direct database secret
- no server-only secret exposed
- empty prospective state handled honestly
- Replay begins showing real prospective records when available
- synthetic remains separate

## Monitoring

Implement or document:

- last successful run
- next scheduled run
- consecutive failures
- stale threshold
- row counts
- unexpected zero-signal cohorts
- unexpected empty universe
- duplicate cohort detection
- upstream rate-limit errors
- database write errors
- forward-observation backlog
- unresolved outcome backlog

The architecture review must answer:

> Once the user completes the deployment steps, will Arepo begin collecting real prospective evidence automatically without any browser being open?

The only acceptable answers are:

- Yes, verified
- No, with the exact missing requirement

Do not answer Yes based only on intended architecture.

Prove it through code, schedules, tests and the production-equivalent dry run.

---

# 17D. Goal tracking and anti-drift control

Create and maintain:

`docs/EDGE_RESEARCH_GOAL.md`

The document must begin with:

> The goal is to determine whether Arepo produces a genuine predictive advantage beyond simple momentum and price-only baselines using prospective, immutable, point-in-time evidence evaluated after realistic execution costs.

Maintain a live table containing:

- goal
- success criterion
- current implementation
- current evidence
- blocker
- next action
- owner
- status

At every major milestone, check whether the work directly advances the goal.

Reject or defer work that does not contribute to:

- collecting prospective evidence
- measuring outcomes
- comparing baselines
- isolating useful features
- preventing leakage or overfitting
- calculating executable performance
- making the evidence understandable

Do not drift into:

- general redesign
- cosmetic work
- unrelated features
- unsupported prediction claims
- polishing synthetic demonstrations
- changing thresholds to improve historical results

Update `CHECKPOINT.md`, `TASKS.md`, `DECISIONS.md` and `docs/EDGE_RESEARCH_GOAL.md` after each verified milestone.

---

# 17E. Exact post-completion user handoff

When the implementation is finished, provide the user with a complete ordered deployment and activation checklist.

Do not merely say to follow `docs/deployment.md`.

The final response must include exact steps for:

1. confirming the completed branch and commit
2. reviewing and merging into `main`
3. creating a production safety tag
4. applying database migrations
5. obtaining the production database connection string
6. creating required email or other service credentials
7. creating the backend service
8. entering every environment variable
9. creating every scheduled job
10. entering each exact UTC schedule
11. deploying the frontend
12. configuring the production API URL
13. connecting the custom domain
14. manually running the first collection sequence
15. verifying the first six-hour cohort
16. verifying the first daily cohort
17. verifying the first weekly cohort
18. verifying one-hour and six-hour observation jobs
19. verifying research-status reporting
20. confirming synthetic data is excluded
21. testing failure recovery
22. checking logs and alerts
23. confirming automatic operation without the browser
24. confirming the rollback plan
25. defining the next review date

For each step provide:

- exact page or service
- exact command where applicable
- exact value name
- whether the value is secret
- expected result
- failure symptom
- corrective action

Do not ask the user to paste secrets into chat.

Also provide:

## First 24 hours

What the user should expect to see.

## First 7 days

Which outcomes and cohorts should begin appearing.

## First 30 days

Which analyses may become possible.

## Evidence threshold

The minimum real sample required before the first meaningful edge assessment.

## Next research decision

The exact decision process if:

- Arepo beats momentum
- Arepo matches momentum
- Arepo underperforms momentum
- only one evidence family adds value
- executable performance is negative despite positive midpoint movement

The handoff must be understandable to a non-technical user and detailed enough to execute without guessing.


# 18. Completion gate

Do not claim completion until:

- every valid directional signal can be frozen internally
- six-hourly, daily and weekly cohorts work
- the full screened universe is frozen
- Research Priority and model version are frozen
- one-hour, six-hour, 24-hour, seven-day and resolution outcomes work
- executable performance includes depth-aware costs
- prospective baselines work
- feature-ablation infrastructure works
- walk-forward infrastructure works
- calibration is correctly guarded
- synthetic data is fully isolated
- research status uses real stored data
- independent reviewers have no unresolved critical or major findings
- automated tests pass
- Git is clean
- branch is pushed
- deployment handoff is complete

Do not claim that Arepo has an edge merely because the infrastructure is finished.

Infrastructure completion means:

Arepo is now capable of collecting the evidence required to determine whether an edge exists.

It does not mean:

Arepo has already proven an edge.

---

# 19. Credit and context fail-safe

If usage or context limits approach:

1. Stop launching new agents.
2. Finish the smallest safe implementation unit.
3. Run the relevant tests.
4. Commit verified work.
5. Push the branch.
6. Update `CHECKPOINT.md` with:
   - completed sections
   - current section
   - files changed
   - schema state
   - tests run
   - failures
   - reviewer findings
   - exact next task
   - exact next command
7. Update `TASKS.md`.
8. Update `DECISIONS.md`.
9. Do not mark the task complete.
10. Exit cleanly.

---

# 20. Final report

Report:

1. branch
2. final commit
3. push status
4. schema changes
5. cohort cadences
6. frozen universe fields
7. shadow-evaluation coverage
8. outcome horizons
9. execution model
10. baselines
11. ablation readiness
12. walk-forward readiness
13. calibration readiness
14. synthetic isolation
15. research-status output
16. collector and scheduler commands
17. backend tests
18. frontend tests
19. reviewer outcomes
20. deployment handoff
21. current real prospective sample
22. current reconstructed sample
23. whether any edge is supported
24. exact reason if it is not
25. minimum evidence still required before a meaningful edge assessment
26. architecture-review verdict
27. requirement-traceability result
28. production-equivalent dry-run result
29. whether deployment will automatically collect data without the browser
30. exact ordered post-completion deployment and activation steps

The final report must state clearly:

- what was built
- what will begin happening after deployment
- what evidence does not yet exist
- why a positive result cannot be guaranteed
- how Arepo will determine whether its extra complexity adds value beyond momentum

Start now and continue autonomously.
