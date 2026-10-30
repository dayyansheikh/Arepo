# Arepo Final Gap-Closure, Replay Validation and Production Deployment

## Role

You are the Opus lead product, quantitative research, data, UX and deployment manager.

This is not a new redesign from scratch. It is a strict gap-closure pass against the user's original requirements and the issues found during manual testing.

Use Sonnet subagents for independent implementation, diagnosis, review and testing. Opus must personally inspect every substantial change, run the relevant tests itself and reject incomplete work.

Do not pause after planning.

Do not claim completion until every requirement below has either:

1. passed with evidence, or
2. been blocked by a genuine external dependency with exact setup steps.

Use natural British English.

Do not use em dashes in user-facing copy.

---

# 1. Safe starting procedure

Before changing anything:

1. Read:
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
   - `FINAL_STATUS.md`
   - all recent completion reports
   - the current implementation
   - Git history for the last three refinement branches
   - current deployment documentation
   - current authentication and email documentation

2. Confirm:
   - current branch
   - Git status
   - latest pushed commit
   - current test status
   - current local database state
   - current account and email architecture

3. Create a new branch:

`arepo-final-gap-closure`

4. Tag the current working state:

`arepo-before-final-gap-closure`

5. Run and record the current baseline:
   - backend tests
   - Python lint
   - frontend lint
   - TypeScript checks
   - frontend tests
   - production build
   - browser smoke test
   - Replay output for each available historical cut-off
   - directional-view coverage
   - confidence distribution
   - component-availability distribution

6. Save the baseline results in:

`docs/final-gap-baseline.md`

Do not change thresholds or logic before this baseline is recorded.

---

# 2. Independent review structure

Create three independent reviewers before implementation.

## Reviewer A: Dayyan acceptance reviewer

This agent must act as Dayyan, the person who wrote the requirements and manually tested the product.

The reviewer should assume:

- Dayyan wants Arepo to give genuinely useful directional insight
- Dayyan is willing to do final research himself
- Arepo should do most of the filtering, statistical analysis and hypothesis formation
- unexplained scores, empty components and generic abstentions are not acceptable
- a visually polished feature does not count as complete if it is not useful
- historical Replay must help build confidence in whether Arepo's current top opportunities have worked previously
- every original requirement must be checked literally

This reviewer must inspect the running application manually, route by route, and create:

`docs/DAYYAN_ACCEPTANCE.md`

For every requirement in this prompt, record:

- requirement number
- route or feature tested
- exact evidence
- screenshot path where useful
- Pass
- Fail
- Blocked
- required fix

This reviewer must not implement the features and must not accept developer claims without testing.

## Reviewer B: prediction-market quant

This reviewer must independently inspect:

- causal validity
- look-ahead bias
- survivorship bias
- sample selection
- Replay reconstruction
- confidence calibration
- signal sensitivity and specificity
- threshold tuning
- component availability
- baseline comparisons
- edge claims
- whether any metric is misleading

Create:

`docs/quant-final-review.md`

## Reviewer C: capable beginner

This reviewer should use Arepo as a numerate but non-expert user trying to decide what deserves further research.

Inspect:

- whether the current model view is useful
- whether the Opportunity Board provides a clear next step
- whether Signal Lab makes sense
- whether Replay builds confidence
- whether How It Works explains the product
- whether sign-in and alert value are clear

Create:

`docs/beginner-final-review.md`

Opus must synthesise all three reviews before implementation.

---

# 3. Remove the broken Full definition interaction

The current `Full definition` interaction leads to an irrelevant or poorly matched section.

Remove it from the interface.

Do not replace it with another navigation link unless the destination is exact and meaningful.

For tags and metrics, use:

- a concise hover and keyboard-focus explanation
- click or tap support
- a compact popover where useful
- an exact Methodology link only when the linked anchor directly explains that item

Test every remaining contextual-help link.

No tag or metric may link to an irrelevant section.

---

# 4. Current model view must provide selective directional insight

The current model view is visually strong and should remain.

The problem is that too many markets display:

> Arepo does not currently have enough independent evidence to favour a direction in this market.

Arepo should not force a view on every market, but it must produce meaningful views often enough to be useful.

## Required work

1. Diagnose why directional views are still rare using real data.

2. Measure:
   - total markets screened
   - markets with sufficient price history
   - markets with sufficient trade-flow history
   - markets with sufficient microstructure history
   - markets with at least one evidence family
   - markets with at least two evidence families
   - markets receiving a directional view
   - abstention rate
   - directional coverage by category and time horizon

3. Determine whether the problem is:
   - missing data
   - collectors not running
   - live wiring incomplete
   - thresholds too strict
   - direction resolution logic
   - component weighting
   - confidence gating
   - inconsistent gates between Board, Market Detail and Signal Lab

4. Do not simply lower thresholds until more markets pass.

5. Calibrate selectivity using held-out historical cut-offs where possible.

6. Add and preserve a clear Opportunity Board filter:
   - Directional views only
   - All screened markets

7. Make `Directional views only` the useful default if it produces a meaningful set.

8. Show a transparent coverage line:

> Arepo screened N markets. M currently meet the requirements for a directional view.

9. Use the same evidence rules across:
   - Opportunity Board
   - Market Detail
   - Signal Lab
   - alerts
   - Replay reconstruction

10. Keep third-person wording such as:
   - Arepo currently favours...
   - Arepo currently sees...
   - Arepo does not yet have enough evidence...

11. Do not produce a directional claim when the evidence is genuinely insufficient.

12. At completion, report before-and-after directional coverage and abstention rates.

---

# 5. Replay regression investigation

Replay previously showed approximately 50 percent directional success over four reconstructed signals.

The current version appears to show one fewer market and all signals wrong.

Do not assume the older or newer result is correct.

Investigate the regression.

## Mandatory comparison

1. Identify the exact commits or logic changes between the earlier Replay result and the current result.

2. Re-run both versions against:
   - the same historical cut-off
   - the same market universe
   - the same eligibility rules
   - the same entry-price definition
   - the same evaluation horizon

3. Explain exactly why:
   - the sample changed
   - one market disappeared
   - directional outcomes changed
   - success changed from approximately 50 percent to zero

4. Determine whether this came from:
   - a bug fix
   - stricter causal selection
   - changed thresholds
   - changed universe
   - changed direction logic
   - missing historical data
   - an actual regression
   - unstable upstream data

5. Add regression tests that lock the intended behaviour.

6. Do not restore the old result merely because it looked better.

7. Keep the result that is causally correct and document why.

Create:

`docs/replay-regression-investigation.md`

---

# 6. Replay must answer the user's real question

Replay should answer:

> If I had opened Arepo at this historical cut-off and followed its top five directional opportunities, what happened afterwards?

## Top-five historical reconstruction

For each available historical cut-off, show up to the top five qualifying opportunities using the same ranking and selection rules used by the live Opportunity Board at that time.

For every selected opportunity, show:

- rank
- market
- selected outcome
- directional hypothesis at the time
- Research Priority at the time
- signal strength at the time
- confidence at the time
- evidence families available at the time
- entry price
- one-hour move where available
- 24-hour move
- seven-day move where available
- final resolution where available
- expected direction
- actual direction
- correct
- incorrect
- flat or inconclusive
- pending
- reconstruction provenance

Do not show current confidence as though it were historical confidence.

## More markets and larger timeframes

1. Scan more than one historical cut-off.

2. Support multiple windows where data permits:
   - 24 hours ago
   - 3 days ago
   - 7 days ago
   - 14 days ago
   - 30 days ago
   - selectable past weeks

3. Expand the market universe as far as causally valid data allows.

4. Add pagination or summarisation if needed.

5. If fewer than five qualify, explain exactly why.

6. Explicitly explain why Signal Lab can show many signals now while historical Replay may reconstruct fewer:
   - live order books may not exist historically
   - wallet or trade-flow history may be incomplete
   - price-history requirements may fail
   - current metadata cannot be used retrospectively
   - some markets may not have existed at the cut-off

7. Show the funnel:

> N markets existed at the cut-off.  
> M had enough historical price data.  
> K passed eligibility.  
> J received a directional view.  
> Top five shown.

## Baselines and evidence of edge

Compare Arepo against simple, causally valid baselines:

- no-change
- current implied probability
- price-only
- momentum
- order-book-only only where historical order-book data genuinely exists

Report:

- sample size
- number correct
- number incorrect
- number flat or inconclusive
- pending count
- hit rate
- confidence interval
- average forward move
- median forward move
- Brier score where appropriate
- log loss where appropriate
- baseline results
- Arepo minus baseline difference

Do not claim an edge unless the sample and held-out comparison justify it.

A 50 percent result on four markets must be labelled inconclusive.

A zero percent result on three markets must also be labelled inconclusive.

The interface should build trust through transparency, not by presenting a tiny sample as evidence.

---

# 7. Explain Replay modes clearly

Replay must clearly distinguish:

## Prospective

Signals genuinely recorded and frozen at the time.

## Reconstructed

Signals rebuilt later using only data that was genuinely available at the historical cut-off.

## Synthetic

Demonstration data used only for testing or education.

Add a concise explanation above the results and a more detailed expandable section.

Never mix these datasets in one headline metric.

Use clear badges and provenance labels.

---

# 8. Confidence must be investigated and calibrated

The user observed that many confidence ratings appeared to be 100 percent.

Audit the complete confidence pipeline.

## Required checks

1. Produce a confidence distribution over current live signals.

2. Report:
   - minimum
   - median
   - mean
   - 90th percentile
   - maximum
   - percentage equal to 100 percent
   - percentage above 90 percent
   - distribution by evidence-family count

3. Confirm confidence is not:
   - copied from data quality
   - unintentionally saturated
   - rounded too aggressively
   - using current data for historical Replay
   - identical to signal strength
   - inflated when components are missing

4. Confidence should represent estimated reliability, not signal magnitude.

5. Confidence must decrease with:
   - missing components
   - stale data
   - poor liquidity
   - wide spread
   - short history
   - only one evidence family
   - incomplete trade-flow or microstructure history

6. Add calibration or reliability analysis where enough outcomes exist.

7. Show historical confidence at signal time in Replay.

8. Add tests for:
   - monotonicity
   - missing-data penalties
   - single-family caps
   - saturation
   - rounding
   - historical timestamp correctness

9. If 100 percent remains possible, explain the exact conditions and ensure it is rare.

---

# 9. Missing components must be completed or honestly explained

The following components are still repeatedly missing:

- Faster trading activity
- Spread change
- Available depth change

This must be resolved.

## Required work

1. Trace each component end to end:
   - source endpoint
   - collector
   - persistence
   - timestamp
   - calculation
   - API response
   - live model
   - Opportunity Board
   - Market Detail
   - Signal Lab
   - Replay availability

2. Confirm whether volume history is still hardcoded as empty anywhere.

3. Confirm microstructure collectors actually run locally and in production.

4. Persist enough snapshots to calculate changes.

5. Wire persisted changes into live signal generation.

6. Ensure:
   - one snapshot cannot produce a change
   - missing remains missing
   - missing never becomes zero
   - stale snapshots are rejected
   - repeated collection is idempotent
   - spread and depth use comparable timestamps

7. Add a component-availability diagnostic route or internal report.

8. Show an honest reason in expanded technical detail when a component is unavailable, for example:
   - Not enough volume history yet
   - Requires at least two order-book snapshots
   - Historical order-book series unavailable for this cut-off

9. Do not show unexplained dashes.

10. Add tests proving every retained component can influence the composite when valid data is present.

11. If a component cannot be supported reliably in production, remove it from the displayed model and methodology rather than pretending it is active.

Create:

`docs/component-availability-audit.md`

---

# 10. Filter state must persist

Filters must survive:

- opening a market card
- opening Signal Lab
- pressing Back
- pressing Forward
- refreshing
- copying and opening the URL
- signing in and returning

Persist:

- Opportunity Board view
- horizon
- directional-only setting
- category
- status
- signal-strength filter
- probability filter
- time-to-close filter
- sort
- keyword search
- closed-market inclusion where present

Use URL state where appropriate.

Add browser tests for restoration and navigation history.

---

# 11. How It Works page fixes

The How It Works page still requires the originally requested visual changes.

Implement:

1. Add a left-side section menu similar to Methodology.

2. Use meaningful anchored sections.

3. Make the left menu sticky.

4. If the menu is longer than the viewport, make it independently scrollable.

5. Scrolling over the menu should scroll the menu.

6. Scrolling over the main content should scroll the page.

7. Apply the same independent-scroll behaviour to the Methodology menu.

8. Make menu text darker and easier to read.

9. Improve active-section highlighting.

10. Reduce the height and padding of oversized How It Works cards.

11. Preserve comfortable spacing without making every section feel like a large empty box.

12. Test laptop, tablet and mobile behaviour.

13. Keep the beginner explanation layer and exact Methodology links.

---

# 12. Move Why Arepo to the sign-in and sign-up experience

Remove the Why Arepo brand paragraph from the bottom of How It Works and any other unsuitable technical page.

Move the brand story into the sign-in and sign-up experience.

## Sign-in page requirements

1. Make the Arepo brand the visual focus.

2. Use a large main Arepo symbol.

3. Use the supplied asset:

`design-assets/brand/AREPO Typeface (word).png`

4. The supplied wordmark with the red mark beneath the A must appear clearly beneath or beside the main symbol.

5. Do not recreate the wordmark with an approximate font when the supplied asset is appropriate.

6. Include the Arepo meaning and brand paragraph.

7. Keep the sign-in form visually clear but secondary to the brand introduction.

8. Preserve accessibility and responsive behaviour.

9. Apply the same brand treatment consistently to sign-up and password-reset pages.

10. Keep the footer credit:
   - Designed and created by Dayyan Sheikh
   - dayyansheikh.work@gmail.com

This is the primary brand showcase page.

---

# 13. Signal Lab consistency

Signal Lab currently contains many live signals while Market Detail may abstain and Replay may reconstruct very few.

Make this relationship explicit and logically consistent.

Each signal must show:

- market
- outcome
- current direction
- current signal strength
- current confidence
- evidence-family count
- whether it qualifies for a directional model view
- why it does or does not qualify
- whether it is eligible for Opportunity Board inclusion
- whether it could be reconstructed historically

Do not imply every anomaly is a directional opportunity.

Consolidate complementary Yes and No signals where appropriate.

---

# 14. Data consistency checks

Add checks for contradictions such as:

- market title end year versus displayed end date
- closed market shown as active
- stale source labelled live
- confidence 100 percent with one evidence family
- a directional view without a resolved direction
- Replay entry after the historical cut-off
- current market metadata used in historical eligibility
- Signal Lab and Market Detail using different gates

Surface important inconsistencies as internal warnings and test failures.

Do not silently display contradictory data.

---

# 15. Production architecture must be singular and explicit

The project has referenced native FastAPI authentication, Supabase, Render, Vercel and Resend.

Inspect the actual code and choose one final production architecture.

Do not leave two competing authentication systems partly configured.

Document:

- frontend host
- backend host
- production database
- authentication implementation
- email provider
- scheduler
- persistent storage
- environment variables
- cookie strategy
- CORS
- redirects
- verification links
- password-reset links

A valid final architecture may be:

- Vercel for Next.js frontend
- Render for FastAPI backend and scheduled jobs
- Supabase Postgres as the production database
- native FastAPI Users authentication stored in Postgres
- Resend for verification, reset and research-alert emails

Alternatively, Opus may choose a better coherent architecture.

Do not use both Supabase Auth and native FastAPI Users unless there is a clearly justified integration.

Delete or disable dead configuration.

Create:

`docs/final-production-architecture.md`

---

# 16. Deployment and production verification

Prepare and complete actual deployment as far as account authentication allows.

## Frontend

- deploy the correct branch to Vercel
- configure production environment variables
- point the frontend to the production API
- verify all routes
- verify authentication redirects
- verify no localhost references remain in production

## Backend

- deploy FastAPI to the selected production host
- configure health checks
- configure production database
- configure migrations or idempotent bootstrap
- configure secure cookies
- configure allowed frontend origin
- configure logs
- configure scheduler jobs
- confirm persistent data survives restart

## Authentication

Production must support:

- sign-up
- email verification
- sign-in
- sign-out
- current-user session
- password reset
- preferences
- saved markets
- account deletion
- expired-session handling

## Email

Production must support:

- verification email
- password-reset email
- research alert email
- unsubscribe or disable flow
- provider failure logging
- deduplication
- cooldown

## Scheduler

Verify:

- microstructure snapshots
- Opportunity Board snapshots
- provisional cohort ranking
- weekly cohort freeze
- forward-price observations
- market resolutions
- user alerts

## End-to-end production test

Run and record:

1. create a new production test account
2. receive verification email
3. verify account
4. sign in
5. change alert preferences
6. save a market
7. sign out and back in
8. trigger a test alert
9. verify data persistence
10. delete the test account
11. confirm protected data is inaccessible afterwards

Do not declare deployment complete until actual live URLs pass.

---

# 17. External account setup boundary

If external user action is required, finish all local work first.

Then provide one exact setup checklist containing:

- service
- account or project to create
- plan required
- region
- environment-variable names
- where each value belongs
- which values are public
- which values are secret
- dashboard settings
- redirect URLs
- CORS origins
- sender-domain verification
- scheduler configuration

Do not ask for passwords or secrets in chat.

Do not commit secrets.

Stop only at the exact unavoidable login or billing step.

---

# 18. Dayyan acceptance gate

After implementation, the Dayyan acceptance reviewer must retest every requirement.

The reviewer must specifically verify:

- broken Full definition interaction removed
- directional views exist on a useful subset
- coverage is disclosed
- abstentions remain only where justified
- filter state persists
- confidence is not universally 100 percent
- confidence is historical in Replay
- missing components are wired or honestly removed
- Replay regression is explained
- Replay shows top-five historical opportunities
- more historical cut-offs are supported where data permits
- the small sample is not presented as proof
- Replay modes are explained
- How It Works has the left menu
- menus independently scroll
- menu text is darker
- cards are smaller
- Why Arepo moved to sign-in and sign-up
- large logo and supplied wordmark are used
- Signal Lab, Market Detail and Replay are logically consistent
- production login works
- production emails work
- production schedules work
- Vercel frontend is live
- backend is live
- no localhost-only assumptions remain

Opus may not declare completion while any Dayyan requirement is marked Fail.

A genuine external blocker may be marked Blocked only with exact next steps.

---

# 19. Quality process

Work in phases.

After every phase:

1. run relevant tests
2. use an independent reviewer
3. fix confirmed defects
4. have Opus inspect the implementation
5. update:
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
6. commit a stable milestone
7. push the branch

Before final completion, run:

- full backend tests
- Python lint
- migration tests
- frontend lint
- TypeScript checks
- frontend tests
- production build
- browser tests
- URL-state tests
- component-availability tests
- Replay regression tests
- baseline comparison tests
- confidence tests
- authentication integration tests
- email dry-run and live-provider tests
- scheduler idempotency tests
- accessibility checks
- responsive checks
- production end-to-end checks

Do not rely on agent summaries alone.

---

# 20. Final report

At completion, provide:

1. branch
2. final commit hash
3. push result
4. live frontend URL
5. live backend URL
6. production architecture
7. exact directional coverage before and after
8. confidence distribution before and after
9. Replay regression explanation
10. historical cut-offs tested
11. total markets considered
12. total qualifying signals
13. top-five Replay results
14. baseline comparisons
15. whether any edge is supported
16. component availability before and after
17. filter persistence result
18. How It Works changes
19. sign-in branding changes
20. account test result
21. email test result
22. scheduler test result
23. backend tests
24. frontend tests
25. build result
26. Dayyan acceptance table
27. remaining limitations
28. external blockers, if any

Do not use vague language such as mostly complete.

Start now and continue autonomously.
