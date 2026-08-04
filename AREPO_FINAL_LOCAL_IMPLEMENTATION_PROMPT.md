# Arepo Final Local Implementation, Replay Credibility and Routing Acceptance

## Role

You are the Opus lead product, quantitative research, frontend, backend and QA manager.

This is the final local implementation and acceptance pass before public deployment.

Do not begin Vercel, Render, Supabase or Resend deployment until every locally testable requirement below is implemented, tested and manually verified.

Use independent reviewers:

1. A Dayyan acceptance reviewer who checks every request literally against the running product.
2. A Replay user-trust reviewer who focuses on whether Replay gives a real user confidence in Arepo's current signals.
3. A prediction-market quant reviewer who focuses on causality, look-ahead bias, confidence calibration, historical selection and edge claims.
4. An implementation expert who resolves the product and engineering problems identified by the other reviewers.

If Claude Code cannot launch multiple Opus instances, use the strongest independent subagents available and disclose that limitation. Do not silently claim multiple Opus reviewers ran if they did not.

Take autonomy.

Do not wait for repeated prompting.

Fix confirmed issues that make Arepo confusing, misleading, statistically weak, visually broken or unsuitable for scrutiny by prediction-market professionals.

Do not manipulate thresholds, samples, time windows or eligibility rules to make Arepo look more successful.

Use natural British English.

Do not use em dashes in user-facing copy.

Do not pause after planning.

---

# 1. Safe starting procedure

Before changing anything:

1. Read completely:
   - `AREPO_FINAL_GAP_CLOSURE_PROMPT.md`
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
   - `FINAL_STATUS.md`
   - `docs/DAYYAN_ACCEPTANCE.md`
   - `docs/quant-final-review.md`
   - `docs/replay-regression-investigation.md`
   - `docs/component-availability-audit.md`
   - `docs/final-production-architecture.md`
   - recent completion reports
   - recent Git history

2. Confirm:
   - current branch
   - working tree
   - latest pushed commit
   - local database state
   - collector state
   - frontend and backend test status

3. Create a continuation branch:

`arepo-final-local-implementation`

4. Tag the current state:

`arepo-before-final-local-implementation`

5. Record a baseline before changing logic:
   - Replay output for every cut-off
   - live directional coverage
   - confidence distribution
   - component availability
   - current route failures
   - current market-search failures
   - current browser tab titles
   - current navigation behaviour at multiple zoom levels
   - current screenshots of all affected routes

6. Save the baseline evidence in:

`docs/final-local-implementation-baseline.md`

Do not change thresholds or model behaviour before the baseline is recorded.

---

# 2. Resolve the previous final-report inconsistencies

Complete these before broader UX work.

## 2.1 Baselines

The original specification requested:

- no-change
- current implied probability
- price-only
- momentum
- order-book-only where historical data genuinely exists

The previous final report listed:

- no-change
- momentum
- always-up
- always-down

Explain the difference.

Implement every causally valid requested baseline that is still missing.

If a requested baseline cannot be implemented, document:

- the exact historical input that is unavailable
- why it is unavailable
- whether it can be collected prospectively
- whether a partial version would be misleading

Do not silently substitute a different baseline.

## 2.2 Replay-result reconciliation

The previous report contained:

- 1/2 at minus 7 days
- 0/1 at minus 14 days
- Arepo 3/5 in the Top-5 comparison

Create one canonical table for every tested cut-off showing:

- exact cut-off timestamp
- market universe size
- markets with historical data
- eligible count
- directional count
- selected count
- evaluation horizon
- correct
- incorrect
- flat or inconclusive
- pending
- hit rate
- confidence interval

Explain why apparently different figures are not contradictory.

## 2.3 Component availability

Replace vague statements such as:

`0/40 to approximately 12/16`

Report separately:

- markets inspected
- faster-trading-activity available
- spread-change available
- depth-change available
- snapshots required
- snapshot interval
- time needed before calculation
- stale-data threshold
- current signals affected by each component

Verify that valid values influence:

- Opportunity Board
- Market Detail
- Signal Lab
- confidence
- Research Priority

## 2.4 Edge wording

Confirm that no page, alert, methodology section, README, portfolio report or status document says or implies that Arepo has demonstrated predictive edge.

The current defensible conclusion is:

- the sample is small
- historical results are inconclusive
- Arepo has not yet outperformed the tested baselines
- the prospective evaluation framework is intended to gather stronger evidence over time

---

# 3. Critical market-search and data-mode routing bug

When searching for certain markets and opening a result, the market page displays:

> Market not found. This market does not exist in the current mode.

The reproduced case occurred while Replay mode was selected. Search returned a market from another universe, but the detail route attempted to resolve it only inside the current Replay dataset.

This is a critical navigation and data-contract bug.

## Required behaviour

1. Search results must record the source and mode in which each market was found.

2. Opening a search result must always open the corresponding real market successfully when it is available from any supported Arepo data source.

3. A user must not need to manually change Live, Cached or Replay mode before opening a search result.

4. Choose the strongest product behaviour:

   - automatically switch to the market's valid source mode, or
   - route with explicit source context such as `?mode=live`, or
   - resolve the canonical market independently of the selected interface mode and load the appropriate data.

5. Live market search results should normally open the live market-detail page even when Replay was previously selected.

6. Replay mode must not override the source attached to a search result.

7. Cached results must open against the correct cached record.

8. Historical Replay rows must open a historical analysis view at the relevant cut-off rather than being treated as current live markets.

9. Use a stable canonical identifier across:
   - search results
   - Opportunity Board
   - Signal Lab
   - market-detail routes
   - Replay rows
   - saved markets
   - alerts

10. Audit whether the route currently mixes:
   - Gamma market IDs
   - event IDs
   - condition IDs
   - token IDs
   - internal database IDs
   - slugs

11. Create an explicit canonical-market mapping layer if identifiers are currently mixed.

12. Do not silently return `Market not found` when the market exists in another supported source.

13. If automatic resolution genuinely fails, show:
   - searched market
   - requested mode
   - whether it exists in another mode
   - direct button to open the available mode
   - retry
   - return to search

14. The error state must not create a large mostly blank page.

15. The footer must follow the error card naturally without excessive whitespace.

## Required investigation

Test the reproduced IDs:

- `2694364`
- `2822017`

Determine whether each failure is caused by:

- invalid ID
- stale search result
- identifier mismatch
- route-parameter mismatch
- data-mode resolution failure
- missing cached record
- Replay-only routing

Create:

`docs/market-routing-investigation.md`

## Required browser tests

Add browser tests for:

- search in Live and open result
- search in Cached and open result
- search while Replay is selected and open a live result
- direct market URL refresh
- opening a result and pressing Back
- filter restoration after Back
- opening a shared result URL in a new tab
- invalid market ID
- valid market found in another mode
- canonical identifier resolution
- historical Replay row opening the correct historical context

Do not mark local acceptance complete until searching for and opening specific markets works regardless of the previously selected mode.

---

# 4. Fix blank market and signal routes

A market route can display a large blank body with only the footer visible.

Diagnose the real cause. Check:

- failed or empty API responses
- route-parameter mismatch
- missing-market handling
- stale cached market IDs
- loading-state height
- client hydration errors
- swallowed fetch exceptions
- `min-height`, `height`, `overflow`, flex and footer CSS
- data-mode mismatch
- invalid route handling

Implement:

1. No empty white page.
2. Proper loading skeleton.
3. Clear not-found state.
4. Clear API-error state with retry.
5. Correct rendering for valid markets.
6. Footer directly after meaningful content when the page is short.
7. Browser tests for valid, invalid, loading and failed routes.

---

# 5. Fix excessive bottom scrolling

When entering a signal or market, the page can continue scrolling far beyond the final content.

Fix the root layout.

Requirements:

- no meaningless scrollable whitespace below the footer
- no artificial document height
- no duplicate shell height
- no oversized `min-height` on route containers
- footer follows content naturally
- long pages still scroll normally
- short pages end cleanly
- correct behaviour at 80%, 90%, 100%, 110%, 125% and 150% browser zoom

Do not hide the issue using a fixed viewport height if the page can legitimately grow.

Add a browser acceptance test confirming the document ends close to the footer rather than thousands of pixels below it.

---

# 6. Signal Lab simplification

Signal Lab is too text-heavy.

The first layer must show the signal, not the full explanation.

## Default collapsed card

Show:

- market
- selected outcome
- direction
- signal strength
- confidence
- evidence-family count
- whether it qualifies for a directional view
- concise one-sentence reason
- freshness
- primary action to open the market

## Expandable detail

Move behind a clear expandable control:

- full explanation
- component breakdown
- data coverage
- lookback details
- confirmation conditions
- invalidation conditions
- methodology detail
- reconstruction availability
- technical limitations

The collapsed state must remain useful.

## Sort and filter controls

Add:

### Directional status

- All signals
- Directional views only
- Observational or inconclusive only

### Sort

- Signal strength, highest to lowest
- Signal strength, lowest to highest
- Confidence, highest to lowest
- Confidence, lowest to highest
- Most recent
- Research Priority where relevant

Do not make fixed thresholds such as `40+` and `70+` the primary organisation system.

Existing threshold filters may be removed or demoted if they add clutter.

Persist all controls in the URL.

Add tests for sorting, filtering, collapse state and browser Back restoration.

---

# 7. Clarify signal direction visually

The current red bars and up or down arrows can be misread.

Ensure:

- direction is labelled with words
- upward and downward direction is not presented as good or bad
- signal strength is visually separate from direction
- confidence is visually separate from strength
- colour is not the only differentiator
- tooltips explain direction, strength and confidence
- a score such as `28 Up` or `33 Down` cannot be mistaken for probability

---

# 8. Responsive navigation

When the browser is zoomed out, the navigation compresses into the middle and leaves excessive unused space.

Fix the application shell so that:

- header uses the available viewport width
- page gutters remain sensible
- logo stays left
- main navigation uses available centre space
- API, mode and account controls stay right
- controls do not bunch in the centre
- no horizontal scrollbar appears
- mobile behaviour remains deliberate

Test at:

- 80%
- 90%
- 100%
- 110%
- 125%
- 150%

Do not stretch individual text links unnaturally.

---

# 9. Browser tab title

Set the browser tab title to exactly:

`Arepo`

Use this title on every route.

Do not display route-specific titles.

Keep the correct Arepo favicon.

---

# 10. How It Works and Methodology side menus

Both pages must use the same shared menu component.

Use the current Methodology visual structure as the base, but adopt the hidden-scrollbar behaviour from How It Works.

Requirements:

- identical width
- identical typography
- identical section grouping
- identical spacing
- identical active state
- dark readable text
- sticky positioning
- independent vertical scrolling
- no visible scrollbar track or thumb
- mouse-wheel and trackpad scrolling still work
- scrolling over the menu scrolls the menu
- scrolling over the document scrolls the page
- keyboard accessibility
- mobile fallback
- reliable active-section tracking

Remove the visible grey scrollbar currently shown on Methodology.

---

# 11. Authentication-page refinement

The sign-in page should fit within one normal desktop viewport without scrolling.

Current direction:

- brand on the left
- form on the right
- main symbol approximately three times larger
- tighter spacing
- no large empty vertical gaps
- no unnecessary footer-induced scroll
- clear responsive hierarchy

Do not use the uploaded wordmark PNG if it renders with an unwanted black background.

Instead use the same clean AREPO wordmark treatment used in the top-left navigation.

Use:

- a very large main Arepo symbol
- the clean navigation-style AREPO wordmark
- the Arepo brand story
- the form as a secondary but clear element

Apply consistently to:

- sign in
- sign up
- password reset
- email verification states

Keep the footer credit.

Test common laptop viewports and confirm no page scroll is needed at standard zoom.

---

# 12. Replay product objective

Replay is a core trust feature, not a demonstration page.

The user has two moments:

## Current moment

The user sees five to ten current signals and is deciding whether they deserve further research.

## Trust-check moment

The user opens Replay and asks:

> If I had been in the same situation last week, which signals would Arepo have shown me, and what happened afterwards?

Replay must answer that directly.

---

# 13. Replay review loop

Use three independent roles.

## Reviewer A: reassurance-focused user

This reviewer checks whether Replay gives a real user peace of mind.

They want:

- a recognisable historical situation
- five to ten realistic candidate signals where available
- markets relevant at the time
- preference for markets closing relatively soon
- strength and confidence as they existed at the cut-off
- subsequent price movement
- clear indication of whether the move followed Arepo's view
- honest limitations

## Reviewer B: prediction-market quant

This reviewer checks:

- causality
- historical-universe accuracy
- look-ahead bias
- confidence-at-time correctness
- selection rules
- sample size
- baselines
- liquidity
- spread
- transaction-cost limitations
- whether any conclusion is justified

## Reviewer C: implementation expert

This reviewer implements the strongest technically defensible product satisfying both reviewers.

Have the reviewers iterate until Reviewer A and Reviewer B both accept the final Replay design.

Document:

`docs/replay-product-review.md`

Do not claim two Opus agents ran unless they genuinely ran.

---

# 14. Replay default experience

The main historical view should lead with:

## Last week's Arepo opportunities

Show the top five to ten directional opportunities Arepo would have displayed at a clearly stated historical cut-off.

Prioritise markets that:

- existed at the cut-off
- met the same evidence rules used live
- had valid point-in-time data
- had meaningful liquidity
- were closing within a useful near-term window where possible

Do not force ten if fewer qualify.

For each opportunity show:

- historical rank
- market
- selected outcome
- close date known at the cut-off
- time remaining at the cut-off
- direction
- signal strength at the cut-off
- confidence at the cut-off
- Research Priority at the cut-off
- entry probability
- one-hour move
- 24-hour move
- seven-day move where available
- final resolution where available
- correct, incorrect, flat, pending or unavailable
- reconstruction type

---

# 15. Replay summary and baselines

Show:

- selected count
- correct
- incorrect
- flat
- pending
- average movement in the signalled direction
- median movement
- confidence interval
- baseline comparison
- explicit conclusion such as `Inconclusive`

Compare against every causally valid requested baseline:

- no-change
- current implied probability
- price-only
- momentum
- order-book-only where historical point-in-time order-book data exists

If a baseline cannot be computed, explain why.

Synthetic results must never contribute to headline performance.

---

# 16. Replay closing-soon lens

Add a historical lens for:

- closing within 24 hours
- closing within 3 days
- closing within 7 days
- all horizons

Persist the selected lens in the URL.

Do not imply near-close markets are automatically better.

---

# 17. Explain the small sample

Replay must explain why it may show fewer signals than Signal Lab.

Valid reasons may include:

- historical order books were not stored
- historical wallet or trade-flow state is incomplete
- some markets did not exist at the cut-off
- some markets lacked enough price history
- current metadata cannot be used retrospectively
- live signals may be observational rather than directional
- current Signal Lab includes information unavailable historically

Show the funnel:

- markets that existed
- markets with historical data
- eligible markets
- directional markets
- selected top opportunities

If only three qualify, state that clearly.

Do not invent additional signals.

---

# 18. Does leaving the website open increase Replay sample size?

Answer this clearly in the interface and documentation.

Correct explanation:

- leaving the browser page open does not increase the sample
- backend collectors and scheduled jobs must run
- one day of collection may add snapshots and improve future component availability
- prospective evaluation requires freezing and storing selections at scheduled cut-offs
- a meaningful performance sample requires many days or weeks
- historical order books never stored cannot be recreated by running the app now

Add a `Replay data status` section showing:

- collectors running or stopped
- last successful collection
- next scheduled collection
- stored snapshot count
- prospective cohort count
- oldest recorded cut-off
- newest recorded cut-off

Verify local collector and production cron commands perform these actions.

---

# 19. Synthetic cohort date

The default Replay page currently shows a stale synthetic cohort such as:

`2026-W28 (synthetic)`  
`Cut-off 12 Jul 2026`

while the actual date is 4 August 2026.

This is confusing.

Fix it by:

1. moving synthetic data into a clearly labelled Demo section, or
2. hiding synthetic cohorts from the default view, or
3. generating a current demonstration cohort and labelling it as generated

Preferred behaviour:

- default to real prospective data where available
- otherwise default to honest reconstructed analysis
- keep synthetic data separate and clearly labelled Demo
- never present stale synthetic data as the active current cohort

---

# 20. Prospective, reconstructed and synthetic definitions

Explain clearly:

## Prospective

Signals genuinely recorded and frozen at the time.

## Reconstructed

Signals rebuilt later using only information that existed at the historical cut-off.

## Synthetic

Demonstration data only.

Never combine these modes in one headline performance number.

---

# 21. Local manual acceptance

Before external setup, manually test:

## Market and signal routes

- valid market
- invalid market
- valid market found in another mode
- loading
- API failure
- bottom-scroll limit
- footer placement
- search result opening in all modes

## Signal Lab

- collapsed cards
- expansion
- all sort directions
- directional filter
- URL restoration
- card navigation
- Back and Forward

## Navigation

- all zoom levels
- narrow desktop
- tablet
- mobile
- no bunching
- no horizontal overflow
- title exactly `Arepo`

## Replay

- every cut-off
- every closing-soon lens
- prospective
- reconstructed
- synthetic separation
- top-five or top-ten view
- historical confidence
- funnel
- baselines
- collector status
- stale synthetic date removed from default
- historical row opens correct historical context

## Learn pages

- shared side-menu component
- hidden scrollbar
- independent scrolling
- active section
- mobile fallback

## Authentication

- one-viewport layout
- larger logo
- navigation wordmark
- no black-background wordmark
- sign-up
- sign-in
- reset
- verification

Record evidence in:

`docs/DAYYAN_FINAL_LOCAL_ACCEPTANCE.md`

No locally testable item may remain Fail.

---

# 22. Automated checks

Run:

- full backend tests
- ruff
- migration and bootstrap tests
- component collector tests
- Replay regression tests
- no-look-ahead tests
- confidence tests
- baseline tests
- frontend lint
- TypeScript
- Vitest
- production build
- lightweight browser tests for all affected routes

Add tests for:

- no excessive bottom scroll
- valid and invalid market route states
- valid market found in another mode
- canonical identifier resolution
- Signal Lab sorting
- Signal Lab collapse
- title exactly `Arepo`
- responsive navigation
- shared side-menu behaviour
- hidden scrollbar
- Replay synthetic separation
- historical confidence timestamp
- collector status
- filter restoration
- search-to-detail routing across modes

---

# 23. Completion gate

Do not begin public deployment until:

- every local acceptance item passes
- market search opens valid markets regardless of prior mode
- Replay user reviewer accepts the product
- quant reviewer accepts causal validity
- Dayyan reviewer accepts the UX
- tests pass
- build passes
- documentation matches implementation
- Git is clean
- branch is pushed

At completion report:

- branch
- commit
- push status
- files changed
- screenshots
- market-routing root cause
- canonical identifier decision
- Replay design
- cut-offs and samples
- baseline results
- confidence distribution
- component availability
- collector status
- Signal Lab changes
- navigation changes
- auth-page changes
- browser title
- local test results
- remaining statistical limitations
- exact external setup steps in correct order

Do not use vague claims such as `complete` while any local requirement remains unresolved.

Start now and continue autonomously.
