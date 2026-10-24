# Arepo Directional Evidence, Replay and Production Deployment

## Role

Act as the Opus lead product, quantitative research, data, security and deployment manager.

Use Sonnet subagents for independent product review, paper review, signal calibration, missing-data diagnosis, replay evaluation, frontend work, security review, deployment and QA. Opus makes the final decisions and personally verifies important work.

Do not preserve weak behaviour merely because it already exists. Do not force directional predictions when the evidence is genuinely insufficient. The aim is a model that is selective enough to be credible and useful enough to surface real directional views.

Do not pause after planning.

## 1. Safety and starting point

Before changing anything:

1. Read CHECKPOINT.md, TASKS.md, DECISIONS.md, all current documentation, backend, frontend, tests and every file in research-references/.
2. Confirm the current branch, Git status, test status and build status.
3. Create a checkpoint commit and tag.
4. Create a new branch called arepo-directional-evidence-deployment.
5. Work only on that branch.
6. Update CHECKPOINT.md, TASKS.md and DECISIONS.md after every major phase.

## 2. Deep research paper

A research paper will be placed inside research-references/.

Opus and an independent quantitative Sonnet reviewer must read it fully before changing the signal model.

Create docs/research-paper-evidence-audit.md covering:

- title and authors
- data and market setting
- proposed metrics
- assumptions
- validation method
- limitations
- features relevant to Arepo
- features that cannot be used
- look-ahead, survivorship and overfitting risks
- implementation priority

Only adopt a paper-derived metric if the required data is genuinely available, it can be computed causally, it has a clear interpretation and it can be tested. Record the paper page or section for each adopted feature.

## 3. Directional views

The current model view usually says Arepo lacks enough evidence to favour a direction. Diagnose why before changing thresholds.

Audit:

- signal thresholds
- evidence-family rules
- complementary Yes and No handling
- outcome mapping
- missing features
- sign aggregation
- freshness
- liquidity and spread gates
- confidence logic
- Research Priority logic
- data windows
- live versus historical schema differences

Create a written diagnosis.

Do not lower thresholds arbitrarily.

## 4. Selective product behaviour

Keep abstention for genuinely weak markets, but do not make neutral markets dominate the Opportunity Board.

Design the clearest behaviour. A strong default is:

- Opportunities shows only markets with a usable directional view and adequate quality.
- Explore shows all markets, including neutral ones.
- Filters include Directional only, Strongest views, Inconclusive included and All markets.

Show how selective Arepo is, for example:

Arepo screened 620 active markets. Twelve currently meet the evidence and quality requirements for a directional view.

The Opportunity Board should normally contain only directional views.

## 5. Recalibrate selectivity

Rebalance sensitivity, specificity and coverage using held-out or prospective evidence.

Measure:

- directional coverage
- abstention rate
- directional accuracy
- precision by confidence band
- accuracy by strength band
- false-positive rate
- false discovery rate
- Brier score or log loss where appropriate
- average and median forward move
- simulated performance after spread and fees
- sample size and confidence interval
- performance by category, liquidity, time-to-close and horizon

Do not tune and report on the same sample without clearly labelling it.

Choose and document a defensible operating point.

## 6. Confidence

Audit why confidence frequently displays 100%.

Confidence must not simply represent observation count or data completeness.

Redesign it to reflect estimated reliability using evidence such as:

- data coverage
- independent evidence families
- agreement between families
- historical calibration of similar signals
- liquidity
- spread
- freshness
- sample size
- missing features
- category-specific reliability

Requirements:

- calculate confidence at the signal timestamp
- Replay shows confidence known at that time
- never use future outcomes
- produce meaningful variation
- test confidence bands empirically
- explain whether confidence is a reliability estimate or a relative quality score
- add calibration tables or plots to internal documentation
- test saturation, missing data and monotonicity

Explain the difference between signal strength, confidence, Research Priority and any forecast probability.

## 7. Missing components

Investigate why Faster trading activity, Spread change and Available depth change are usually empty.

Determine whether data is not fetched, not stored, mapped incorrectly, unavailable historically or discarded.

For live prospective operation:

- persist timestamped trade, spread and depth observations
- compute volume acceleration from a real time series
- compute spread change from spread snapshots
- compute depth change from near-mid depth snapshots
- store timestamps and provenance
- make collection idempotent

For historical reconstruction:

- never use current order books to recreate past spread or depth
- label missing evidence
- reduce confidence
- do not silently convert missing to zero
- apply the documented missing-feature weight policy

If a feature cannot be made useful, remove the permanently empty surface row. Add tests proving each retained component can contribute.

## 8. Data consistency

Audit contradictions between the market question, event date, displayed end date, close state and resolution state.

Where sources disagree:

- preserve provenance
- show a clear warning
- avoid unreliable time-to-close calculations
- document the conflict

Do not silently display contradictory dates.

## 9. Filter persistence

Filters currently reset after opening a market and going back.

Persist state through URL query parameters, including:

- category
- status
- time-to-close
- strength
- confidence
- directional-only state
- sorting
- search
- page or cursor
- Opportunity Board mode

Browser Back, Forward, refresh and shared links must restore the exact state. Add browser tests.

## 10. Current model view

Keep the third-person Arepo voice.

The section should show:

- current directional view
- relevant outcome
- strength
- confidence
- Research Priority
- evaluation horizon
- concise reason
- confirming evidence
- invalidating evidence
- key risks
- what the user should verify independently

Examples:

Arepo currently sees moderate evidence favouring Yes over the next seven days.

Arepo currently sees weak downward pressure, but confidence is limited by thin liquidity.

Arepo does not currently have enough independent evidence to favour a direction.

Do not force a view in Explore. Opportunities should prioritise usable views.

## 11. Replay modes

Explain the modes clearly:

- Prospective: signals recorded and frozen at the time.
- Historical reconstruction: signals rebuilt only from information available at the historical cut-off.
- Synthetic: demonstration data only.

Never mix them.

## 12. Replay that mirrors real use

The default Replay question is:

Had I followed Arepo's top five qualifying views at the time, what happened next?

For each selected date or week, show:

- screened market count
- selected top five
- market and outcome
- signal timestamp
- entry probability
- strength
- confidence at the time
- Research Priority at the time
- evidence families
- 1-hour, 24-hour and 7-day moves
- resolution where available
- spread and fee assumptions
- directional correctness
- hypothetical return under clearly stated assumptions

Allow Top 10 and Top 15 for research, but keep Top 5 as the default user experience.

## 13. Larger replay samples and edge testing

Expand evaluation across multiple weeks and custom date ranges.

Add breakdowns by:

- horizon
- category
- liquidity
- confidence band
- strength band
- time-to-close

Compare Arepo against:

- random direction
- no-change
- simple momentum
- order-book-only
- price-only
- current implied probability for resolution tests

Report sample size, confidence intervals, average and median move, magnitude-weighted results, simulated return after spread and fees, and Brier score or log loss when suitable.

A 50% hit rate is not automatically good or bad. Demonstrate whether winning moves outweigh losing moves and whether Arepo beats simple baselines.

Do not claim an edge unless the evidence supports it. If no reliable edge exists, say so.

## 14. How It Works

Reduce oversized cards and excess empty space.

Add a left-side section menu similar to Methodology:

- sticky on desktop
- independently scrollable when hovered
- current section highlighted
- keyboard accessible
- mobile collapse
- darker text
- smaller content panels
- anchored links

Explain directional views, abstention, Research Priority, strength, confidence, evidence families, Replay modes, Top 5 evaluation, accounts and alerts.

## 15. Sign-in page and brand story

Remove Why Arepo from technical result pages.

Use sign-in and account entry as the main brand moment.

Create a refined page with:

- large Arepo symbol
- design-assets/brand/AREPO Typeface (word).png
- the brand paragraph
- concise account benefits
- sign-in and account creation
- restrained red, white and black styling

Preserve the red mark under the A in the uploaded wordmark.

## 16. Production architecture

Keep the existing native authentication unless there is a strong documented reason to replace it.

Preferred production structure:

- Vercel for Next.js
- Render for FastAPI, cron jobs and background work
- Supabase Postgres for persistent production data
- Resend for verification, reset and alert email

Opus may choose an equivalent structure if it is clearly simpler or more reliable.

## 17. Production authentication and database

Configure:

- strong AUTH_SECRET
- Postgres rather than SQLite
- verified-email login
- password reset
- secure cookies
- HTTPS
- correct CORS and trusted origins
- account deletion
- per-user isolation
- database indexes
- idempotent migrations
- separate development and production settings

Never expose server secrets to the browser.

If frontend and backend use different domains, configure cookies and cross-origin requests securely.

Use the appropriate Supabase Postgres connection mode for the backend runtime and document why.

## 18. Production email

Connect the provider-neutral email system to Resend.

Support:

- verification emails
- password resets
- immediate alerts
- daily digests
- unsubscribe
- deduplication
- idempotency
- retries
- failure logs
- plain-text fallback
- verified sender
- production-safe templates

Keep secrets out of Git.

A test sender may be used only within provider limits. Sending to arbitrary registered users requires a verified custom domain.

## 19. Scheduled collection

Create idempotent production jobs for:

- market refresh
- spread, depth and trade snapshots
- Opportunity Board ranking
- weekly cohort freeze
- forward-price collection
- resolution checks
- immediate alert evaluation
- daily digest
- cleanup

Use UTC schedules.

Do not depend on the browser or Dayyan's laptop remaining online.

## 20. Deployment

Prepare and test:

### Vercel frontend

- correct monorepo root
- production API URL
- Preview and Production variables
- no localhost references
- preview deployment
- production deployment
- loading and error states

### FastAPI backend

- production build and start commands
- health endpoint
- migration step
- environment variables
- CORS for Preview and Production
- structured logs
- graceful failures
- scheduled jobs

### End-to-end deployed tests

Verify outside localhost:

- public pages
- sign-up
- verification email
- sign-in
- password reset
- account preferences
- saved markets
- directional Opportunity Board
- market model view
- filter persistence
- Signal Lab
- Replay
- alert email
- mobile layout
- logout
- account deletion

Do not call deployment complete until these pass.

## 21. Quality process

After every phase:

- run relevant tests
- use an independent Sonnet reviewer
- fix confirmed issues
- have Opus inspect the result
- commit a milestone
- update CHECKPOINT.md, TASKS.md and DECISIONS.md

Before completion run:

- backend tests and lint
- migration tests
- authentication integration tests
- frontend lint, type checks, tests and build
- filter restoration tests
- confidence calibration tests
- no-look-ahead replay tests
- baseline comparisons
- email dry run
- deployed email test
- Vercel Preview smoke test
- Production smoke test
- accessibility and mobile checks

## 22. Documentation and final report

Update all relevant documentation, including:

- README.md
- docs/architecture.md
- docs/methodology.md
- docs/limitations.md
- docs/authentication.md
- docs/accounts-privacy.md
- docs/alert-configuration.md
- docs/deployment.md
- docs/performance.md
- docs/research-paper-evidence-audit.md
- FINAL_STATUS.md
- screenshots
- portfolio report
- submission package

Report:

- paper findings adopted
- why directional views were rare
- model and threshold changes
- directional coverage before and after
- confidence findings
- missing-component findings
- replay sample and results
- baseline comparisons
- whether evidence of an edge exists
- filter-state fix
- design changes
- production architecture
- migrations
- email status
- scheduler status
- Vercel URL
- backend URL
- deployed test results
- remaining limitations
- branch, commit and push result

Start now and continue autonomously.
