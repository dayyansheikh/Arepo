# Arepo Complete Short-Horizon Universe, Continuous Signals and Prospective Replay

You are the Opus lead product, quantitative research, backend, data-engineering, frontend and QA manager for Arepo.

Work autonomously through implementation, real-data verification, browser testing, documentation, commit and push.

Use Sonnet subagents for independent market-discovery, data-pipeline, quantitative-review, frontend and browser-QA work where useful. Opus remains responsible for architecture, correctness, integration and final verification.

Use natural British English.

Do not use em dashes in user-facing text.

Do not deploy.

Do not merge to `main`.

Do not ask routine implementation questions.

## Starting point

Repository:

`/Users/DayyanSheikh/Projects/astrolabe`

Expected starting branch:

`arepo-prospective-replay-refinement`

Expected starting commit:

`740e6cf`

Before changing anything:

1. Read `CHECKPOINT.md`, `TASKS.md`, `DECISIONS.md`, `FINAL_STATUS.md` and all current market-discovery, collector, signal, Replay, research, scheduler and deployment documentation.
2. Inspect the current branch, Git state, database schema, market-discovery clients, API pagination, token mapping, scoring pipeline, ranking logic, research CLI, Replay endpoints, frontend and tests.
3. Confirm that `backend/astrolabe.db` exists.
4. Preserve every existing cohort, entry, forward observation, signal snapshot, resolution row and audit record.
5. Create a timestamped database backup.
6. Create the safety tag:

   `arepo-before-complete-short-horizon-universe`

7. Create and work only on:

   `arepo-complete-short-horizon-universe`

Do not delete, reset, recreate or replace the database.

Do not destructively migrate populated tables.

## Core correction

The system must not scan only ten markets.

The system must not scan only the first API page.

The system must not scan only the first 60 markets returned.

The number ten is a display and ranking limit for the public interface only.

For every scan and every future cohort freeze, Arepo must:

1. discover the complete eligible active market universe available through the supported public Polymarket discovery endpoints
2. traverse every page or cursor until the upstream API explicitly indicates completion
3. deduplicate and validate the full result
4. identify every active market closing within 30 days
5. calculate the existing signal model for every eligible market in that 30-day universe
6. store every eligible market and every directional signal needed for research
7. rank the complete eligible universe
8. show only the top ten in each public view, while preserving the full underlying sample

If 350 markets close within six hours, Arepo must analyse all 350, not ten.

The public screen may show the top ten, but Replay and research aggregates must retain and evaluate all 350 eligible markets and all directional calls.

Do not use an arbitrary cap that silently leaves markets unscanned.

A high emergency loop-protection cap may exist only to prevent an infinite pagination loop. It must fail loudly and mark the scan incomplete rather than returning a misleading partial universe.

## Non-negotiable research constraints

Do not change the current:

- directional model formula
- signal thresholds
- confidence calculation
- Research Priority calculation
- evidence-family formulas
- baseline definitions
- ablation logic
- walk-forward logic
- edge criteria
- historical frozen values
- existing prospective outcomes

This pass may change:

- complete market discovery and pagination
- future public-market eligibility
- short-horizon universe construction
- live signal refresh scheduling
- append-only signal-history storage
- future cohort composition
- Replay evaluation and presentation
- Signal Lab information hierarchy

Do not tune thresholds after looking at outcomes.

Do not describe signal strength as probability.

Do not describe a strengthening signal as proof that an outcome is becoming more likely.

Do not alter the existing historical 60-market cohort.

## 1. Audit exactly why the existing cohort contains 60 markets

Create:

`docs/complete-universe-discovery-audit.md`

Trace the complete path from upstream market discovery to the stored 60-market cohort.

Determine exactly whether 60 came from:

- an upstream page size
- a hard-coded `limit`
- a slice such as `[:60]`
- a fixture or demo assumption leaking into production
- an early pagination stop
- an eligibility rule
- token-resolution failures
- missing close times
- quality or liquidity exclusions
- category restrictions
- deduplication
- another explicit reason

Do not assume that 60 was complete.

Inspect all relevant:

- Gamma API calls
- CLOB API calls
- Data API calls
- cursor handling
- offset handling
- page-size parameters
- `limit`, `first`, `top`, `take` and slicing operations
- active and closed filters
- date filters
- event and market mapping
- complementary outcomes
- multi-outcome events
- negative-risk markets
- token mapping
- retries
- partial failures
- exclusion logging
- tests and fixtures

The audit must produce a full discovery funnel:

- raw pages fetched
- raw records returned
- unique events
- unique markets
- duplicates removed
- inactive markets removed
- closed markets removed
- missing close-time markets
- invalid close-time markets
- markets closing within 6 hours
- markets closing from 6 to 24 hours
- markets closing from 1 to 7 days
- markets closing from 7 to 30 days
- markets closing after 30 days
- token-data exclusions
- data-quality exclusions
- liquidity exclusions
- total analysed markets
- directional markets
- public top-ten candidates

## 2. Implement complete, verifiable pagination

Every production market-discovery path used by Opportunities, Signal Lab, prospective cohort creation and Replay must fetch the complete upstream result set.

Requirements:

- follow every cursor until no next cursor exists
- follow every offset page until the returned page is genuinely exhausted
- deduplicate by canonical market or condition identifier
- retain deterministic ordering
- record page count
- record raw item count
- record unique market count
- record cursor or offset progression
- detect repeated cursors
- detect non-progressing offsets
- use bounded retries
- record partial failures
- fail loudly when the scan is incomplete
- never convert an incomplete scan into a valid-looking cohort
- prevent infinite loops
- make repeated complete scans idempotent
- preserve explicit exclusion reasons

Add tests for:

- one page
- multiple pages
- exactly 60 items on page one with further pages remaining
- 500 or more synthetic discovery results
- duplicates across pages
- repeated cursor
- missing cursor termination
- partial upstream failure
- retry success
- retry exhaustion
- abnormal early termination
- deterministic deduplication

The acceptance test must prove that the scanner does not stop merely because the first page contains 60 or 100 records.

## 3. Define the complete public short-horizon universe

For future public Opportunities, Signal Lab analysis and future public prospective cohorts:

A market is eligible only when all of the following are true at the scan or freeze timestamp:

- it is active
- it is not already closed
- it has a valid known close time
- it has more than zero time remaining
- it has no more than 30 days remaining
- its tradable outcome token can be resolved
- it passes the existing data-quality requirements
- it passes the existing liquidity and spread requirements where those rules already apply

Markets closing more than 30 days away must not enter:

- public Opportunities
- public Signal Lab
- public top-ten rankings
- future public-selection cohorts

The scanner may retain longer-dated metadata internally where already required, but it must clearly separate:

- complete active universe discovered
- eligible public 30-day universe
- longer-dated research-only or excluded markets

This must be a backend eligibility rule before scoring and public ranking.

It must not be implemented only as a frontend filter.

Do not change the existing historical cohort.

## 4. Build complete short-horizon universes

At each scan and each future freeze, assign every eligible market to exactly one non-overlapping primary bucket using the close time known at that timestamp:

- `closing_0_6h`: more than 0 hours and up to 6 hours
- `closing_6_24h`: more than 6 hours and up to 24 hours
- `closing_1_7d`: more than 24 hours and up to 7 days
- `closing_7_30d`: more than 7 days and up to 30 days

Also support:

- `all_0_30d`: all eligible markets closing within 30 days

Plain-English labels:

- Closing in the next 6 hours
- Closing later today
- Closing this week
- Closing this month
- All markets closing within 30 days

Also support cumulative API queries where useful:

- within 6 hours
- within 24 hours
- within 7 days
- within 30 days

Historical bucket membership must never be recalculated from the present time.

Store the bucket and exact `time_remaining_hours` in each snapshot and frozen entry.

## 5. Analyse every eligible market in every universe

For every complete refresh:

1. discover the full active market universe
2. validate that pagination completed
3. apply the 30-day public eligibility rule
4. resolve all valid tradable outcomes
5. calculate the existing signal features for every eligible market
6. assign every eligible market to its short-horizon bucket
7. store the analysis result for every eligible market
8. preserve every directional call
9. preserve observation and abstention states needed for research
10. calculate independent rankings within each bucket
11. calculate an overall ranking across `all_0_30d`

Do not calculate a global ranking first and then merely filter the displayed top ten.

Each bucket must have its own ranking based on all eligible markets in that bucket.

For example:

- if 350 markets close within 6 hours, analyse all 350
- rank all 350
- store all 350 analysis rows
- preserve every directional signal among them
- show only the top ten publicly

The top-ten limit must never reduce:

- universe size
- number analysed
- number frozen for research
- number evaluated in Replay
- shadow-signal coverage
- aggregate denominators

Do not pad to ten when fewer than ten directional signals qualify.

## 6. Separate public top ten from full research coverage

For each short-horizon universe, maintain at least these scopes:

### Full eligible universe

Every eligible market in the bucket, including directional, observation and abstention states.

### All directional signals

Every eligible market for which Arepo made a directional call.

### Public top ten

Up to ten highest-ranked directional signals in that bucket.

### Shadow directional

Directional signals not included in the public top ten.

Replay must be able to evaluate:

- public top ten
- shadow directional
- all directional signals
- full eligible universe where research controls require it

The default public display may show the top ten.

The research database must preserve the complete underlying universe.

## 7. Add continuous live signal refresh

Signal Lab must not represent one isolated scan.

Implement one idempotent, scheduler-compatible complete refresh command.

Target cadence:

- every 5 minutes

Before fixing the cadence:

1. run a complete real scan
2. measure total scan duration
3. inspect API rate-limit handling
4. confirm token resolution and scoring complete reliably
5. ensure scans cannot overlap

If a complete scan cannot reliably finish within five minutes, use ten minutes and document the measured reason.

Do not use a slower cadence without evidence.

Do not use a faster cadence without evidence.

Requirements:

- append-only refresh records
- overlap lock or lease
- stale-lock recovery
- bounded retries
- partial-failure status
- incomplete-scan status
- last successful scan
- scan duration
- page count
- raw discovered count
- eligible 30-day count
- analysed count
- directional count
- top-ten counts per bucket
- last failure
- next scheduled scan
- browser independence

The browser may poll stored results.

The browser must never perform the market scan itself.

## 8. Store immutable signal snapshots

Create or extend an append-only schema for every analysed market snapshot.

Store, where available:

- scan ID
- canonical market ID
- condition ID
- event ID
- token ID
- market question
- selected outcome
- snapshot timestamp
- close time known at snapshot
- time remaining
- short-horizon bucket
- active state
- eligibility state
- exclusion reason where ineligible
- direction
- signal classification
- signal strength
- confidence
- Research Priority
- rank within bucket
- overall 30-day rank
- public top-ten flag
- shadow-directional flag
- evidence-family count
- evidence families
- component scores
- component availability
- data quality
- midpoint
- best bid
- best ask
- spread
- depth
- liquidity
- volume
- data age
- model version
- calculation version
- provenance
- source timestamps

A later refresh must never overwrite an earlier snapshot.

Add uniqueness and idempotency rules appropriate to scan ID, market ID and token ID.

Preserve existing rows through additive migration.

## 9. Define signal trajectory carefully

Using stored snapshots, calculate:

- change since previous scan
- change over approximately 15 minutes
- change over approximately 1 hour
- change over approximately 6 hours
- first detected
- last updated
- consecutive scans with the same direction
- rank change
- Research Priority change
- evidence-family changes
- direction reversal

Use labels:

- New signal
- Strengthening
- Weakening
- Stable
- Direction reversed
- Temporarily unavailable
- Stale

A strengthening signal means only:

> The stored signal-strength score increased over the selected comparison period.

It must not mean:

- the outcome became more likely
- accuracy increased
- expected profit increased
- final resolution became more certain

Always show the numeric change.

Choose a predeclared stability threshold based on score precision and numerical jitter.

Do not tune it using realised outcomes.

Document and test the threshold.

## 10. Redesign Signal Lab so signals come first

The current Signal Lab opens with a large explanation block before the actual signals.

Change the page hierarchy.

At the top show:

- `Signal Lab`
- one concise sentence
- current short-horizon universe
- last successful complete scan
- raw markets discovered
- eligible markets analysed
- directional signals found
- actual signal cards or table

Move the long explanatory content into a disclosure titled:

> How Signal Lab works

Requirements:

- collapsed by default
- keyboard accessible
- screen-reader accessible
- remembers no misleading state across navigation
- does not push the actual signals below the first useful viewport

Keep methodology links available but visually secondary.

Add controls for:

- closing universe
- public top ten versus all directional signals
- ranking or sort view where useful
- last updated status

## 11. Show live trajectory on signal cards

Each signal card or row should show:

- bucket rank
- overall 30-day rank where useful
- market
- selected outcome
- current direction
- current strength
- strength change
- trajectory label
- first detected
- last updated
- consecutive same-direction scans
- close time
- time remaining
- evidence summary
- compact strength-history sparkline where practical
- market-detail link
- methodology link

Use wording such as:

> Strength 72, up 6 points over the last hour.

> Direction unchanged for 9 consecutive scans.

Do not use wording such as:

> Prediction is 6 points more likely.

Do not use colour alone.

## 12. Add signal history to market details

For every eligible market, add a concise signal-history section showing:

- current signal state
- recent strength history
- direction history
- rank history within the relevant bucket
- Research Priority history
- material evidence-family changes
- price history on the same time axis where available
- last successful scan
- stale or missing intervals

Keep the signal model unchanged.

This is a history and interpretation layer.

## 13. Build future prospective cohorts from the complete eligible universe

Future cohorts must not freeze only the public top ten.

At each scheduled freeze, preserve the complete eligible 30-day universe discovered at that time.

For each primary bucket, store:

- every eligible market
- every directional signal
- public top-ten membership
- shadow-directional membership
- observation state
- abstention-control state where required
- frozen rank within the bucket
- frozen overall 30-day rank
- frozen Research Priority
- exact time remaining
- close time known at freeze
- original price and order-book state
- evidence components
- model version
- calculation version
- scheduled cut-off
- actual freeze time
- evaluation origin
- lateness

The public top ten is a subset of the complete frozen universe.

The full directional universe is required to test whether ranking adds value.

Do not modify or recreate the existing historical 60-market cohort.

## 14. Ensure Replay works independently for every short-horizon universe

Replay must treat each closing-time universe as a complete prospective evaluation set.

Allow selection of:

### Cohort cadence

- Six-hourly
- Daily
- Weekly

### Specific cohort

- scheduled cut-off
- actual freeze
- lateness where relevant

### Frozen closing-time universe

- Closing in the next 6 hours
- Closing later that day
- Closing within 7 days
- Closing within 30 days
- All eligible markets closing within 30 days

### Signal scope

- Public top ten
- Shadow directional
- All directional signals
- Full eligible universe where research controls require it

### Evaluation

- 1-hour repricing
- 6-hour repricing
- 24-hour repricing
- 7-day repricing
- Freeze-to-close repricing
- Final resolution
- Estimated executable result where genuinely available

The selected closing-time universe must use the membership frozen at the cohort timestamp.

It must not be generated by filtering the current market universe.

## 15. Add freeze-to-close evaluation

For short-horizon markets, add a distinct evaluation:

> Price movement from freeze to the final valid pre-close observation.

For each entry, store where available:

- first valid post-freeze observation
- 1-hour observation
- 6-hour observation
- 24-hour observation
- 7-day observation
- final valid pre-close midpoint
- final valid pre-close bid
- final valid pre-close ask
- pre-close source timestamp
- actual market close timestamp
- resolution state
- resolved outcome
- resolution timestamp
- invalid state
- cancelled state
- unavailable reason

A market closing within six hours may not resolve within six hours.

Show:

> Closed, awaiting resolution

until a genuine resolution is stored.

Do not infer final resolution from the last price.

## 16. Keep four evaluation questions separate

Replay must never collapse these into one result:

### A. Short-term price direction

Did the selected outcome’s midpoint move in Arepo’s stored direction over 1h, 6h, 24h or 7d?

### B. Freeze-to-close price direction

Did the selected outcome’s price move in Arepo’s stored direction between the freeze and the last valid pre-close observation?

### C. Final resolution

Did the selected outcome finally resolve successfully?

### D. Estimated executable result

Would a realistic entry and exit have been positive after spread, fees, depth and slippage assumptions?

A signal may be correct for A and wrong for C.

A signal may be correct for A but unprofitable for D.

Report them separately.

## 17. Show later signal evolution separately from outcome

For each frozen signal, Replay must separately show what happened to the signal after freeze.

At the nearest valid snapshot after each evaluation horizon, show:

- later signal strength
- strength change from freeze
- later direction
- unchanged or reversed direction
- Research Priority change
- rank change within the same frozen bucket
- evidence-family changes
- strengthening, weakening, stable or reversed

These later signal states are diagnostic only.

They must never rewrite:

- the frozen direction
- the frozen strength
- the frozen rank
- the original evaluation

Use wording such as:

> Frozen strength: 68  
> Six-hour strength: 74  
> Signal strengthened by 6 points and kept the same direction.

Do not say:

> The prediction became 6 points more likely.

## 18. Report complete and honest Replay denominators

For every selected cohort, universe, scope and evaluation, show:

- total frozen observations
- unique markets
- unique events where identifiers permit
- repeated markets across cohorts
- directional calls
- public selections
- shadow signals
- moved as expected
- moved against
- no price change
- pending
- unavailable
- invalid
- closed awaiting resolution
- final-resolution correct
- final-resolution incorrect
- movement coverage
- signal strengthened
- signal weakened
- signal stable
- direction reversed

Do not count repeated five-minute snapshots as separate predictions.

A market may appear in several scheduled cohorts, but Replay must expose:

- observation count
- unique-market count
- unique-event count
- repeated-market count

Preserve grouping identifiers for:

- complementary contracts
- overlapping date markets
- outcomes within the same event
- semantically related markets where reliable grouping exists

Do not present related rows as fully independent evidence.

## 19. Server-side API requirements

Implement or extend typed endpoints for:

- complete scan status
- pagination completeness
- discovery funnel
- raw discovered count
- eligible 30-day count
- counts by primary bucket
- current top ten per bucket
- all current directional signals
- full eligible universe where authorised for research views
- signal history for one market
- trajectory metrics
- current rank history
- available prospective cohorts
- frozen bucket membership
- public, shadow and all-directional scopes
- price outcomes by horizon
- freeze-to-close outcomes
- final resolutions
- executable results
- later signal evolution

Important evaluation truth must be computed on the server.

The frontend must not infer:

- correctness
- bucket membership
- resolution
- pagination completeness
- trajectory state
- historical rank
- unique-market denominators

from loose client state.

Make reads deterministic and idempotent.

## 20. Scheduler and operations

Inspect `render.yaml` and all scheduler documentation.

Ensure repository-side configuration includes:

- complete live signal refresh at the measured safe cadence
- six-hour cohort freeze
- daily cohort freeze
- weekly cohort freeze
- forward-price collection
- freeze-to-close collection
- resolution updates

Do not deploy.

Prevent overlapping scans.

Document:

- local manual commands
- production schedules
- expected duration
- pagination status
- stale-job detection
- incomplete-scan handling
- retry behaviour
- lock behaviour
- recovery steps
- rerun safety

A cohort freeze must refuse to proceed or mark itself degraded when the underlying universe scan is incomplete.

## 21. Required backend tests

Add tests for:

- complete pagination
- exactly 60 records on page one with further pages available
- 500 or more discovered records
- duplicate records across pages
- repeated cursor
- non-progressing offset
- partial failure
- loud incomplete-scan state
- deterministic deduplication
- 30-day eligibility
- unknown close-time exclusion
- expired-market exclusion
- exactly 6-hour boundary
- exactly 24-hour boundary
- exactly 7-day boundary
- exactly 30-day boundary
- more-than-30-day exclusion
- non-overlapping bucket membership
- cumulative time filters
- every eligible market analysed
- independent bucket rankings
- overall 30-day ranking
- public top-ten subset
- full directional preservation
- shadow preservation
- fewer than ten qualifying signals
- append-only snapshots
- refresh idempotency
- overlap prevention
- trajectory calculations
- stability threshold
- direction reversal
- stale state
- future cohort uses complete eligible universe
- incomplete scan cannot create a normal-looking cohort
- historical 60-market cohort unchanged
- 1h, 6h, 24h and 7d evaluation
- freeze-to-close evaluation
- final resolution remains pending until genuine
- closed-awaiting-resolution state
- executable result kept separate
- later signal evolution does not rewrite frozen prediction
- unique market and event denominators
- server-side evaluation truth

## 22. Required frontend and browser tests

Add tests for:

- Signal Lab explanation collapsed by default
- actual signals visible in the first useful viewport
- complete-scan status
- eligible-market count
- raw discovered-market count
- closing-universe controls
- top ten display without implying only ten were analysed
- text such as `Top 10 shown from 327 eligible markets`
- public versus shadow versus all directional scope
- last updated
- trajectory labels
- numeric strength changes
- direction reversal
- accessible sparkline alternative
- market-detail history
- Replay cohort selection
- Replay frozen-universe selection
- Replay scope selection
- Replay evaluation selection
- freeze-to-close results
- closed-awaiting-resolution
- final-resolution separation
- price outcome separated from signal evolution
- full denominators
- unique market count
- no public market closing after 30 days
- narrow viewport
- no horizontal overflow
- keyboard accessibility
- screen-reader labels
- disconnected state and recovery

Use real Chromium for final acceptance.

Use the preserved local database and live public APIs where safe.

Do not rely only on mocked fixtures.

## 23. Real-data acceptance run

Run one complete real discovery and analysis scan.

Report:

- pages or cursors fetched
- raw records returned
- unique active markets discovered
- markets with valid close times
- markets closing within 0 to 6 hours
- markets closing within 6 to 24 hours
- markets closing within 1 to 7 days
- markets closing within 7 to 30 days
- markets closing after 30 days
- invalid markets
- token-resolution failures
- data-quality exclusions
- liquidity exclusions
- total eligible 30-day markets
- total analysed markets
- directional signals per bucket
- public top ten per bucket
- shadow directional per bucket
- scan duration
- pagination completion state

Do not require the result to exceed 60.

Instead, prove that:

- every page was fetched
- no hard-coded 60-market cap remains
- no top-ten display limit affected analysis
- every eligible market was analysed or has an explicit exclusion reason

Then run a second complete refresh after the configured interval and prove:

- new immutable snapshots were added
- earlier snapshots were not overwritten
- trajectory calculations use both scans
- current cards update from stored history

## 24. Real Replay acceptance

For each frozen closing-time universe that has data, verify:

- complete frozen membership
- all directional signals preserved
- public top ten identified as a subset
- shadow directional preserved
- 1h results
- 6h results
- 24h results when due
- 7d results when due
- freeze-to-close results when closed
- final resolution only when genuinely resolved
- closed-awaiting-resolution when appropriate
- later signal evolution stored separately
- unique-market and unique-event denominators
- reproducible aggregates from the database

For new prospective cohorts, demonstrate that Replay is built from the complete eligible bucket universe, not only the displayed top ten.

## 25. Verification gate

Run:

### Backend

- full `pytest`
- `ruff check`

### Frontend

- TypeScript check
- lint
- full unit tests
- clean production build
- complete Playwright suite

Inspect database counts before and after.

Confirm that the existing historical cohort still contains:

- 60 entries
- 19 directional calls
- 10 public selections
- 9 shadow directional signals
- its existing forward observations

Do not claim completion until:

- complete pagination is proven
- the 30-day gate is backend-enforced
- all eligible markets are analysed
- top ten is display-only
- two append-only refreshes work
- short-horizon Replay universes work
- freeze-to-close and final resolution remain separate
- the real API and real browser pass

## 26. Documentation

Update:

- `CHECKPOINT.md`
- `TASKS.md`
- `DECISIONS.md`
- `FINAL_STATUS.md`
- market-discovery documentation
- Signal Lab methodology
- Replay methodology
- local usage guide
- scheduler guide
- deployment checklist
- API documentation

Explain clearly:

- how complete pagination is proved
- why top ten is a display limit only
- why all eligible markets are analysed
- why public analysis stops at 30 days
- how short-horizon universes are constructed
- how often signals refresh
- what strengthening and weakening mean
- why signal strength is not probability
- why later signal changes cannot rewrite a frozen prediction
- how price outcomes, freeze-to-close performance, final resolution and executable performance differ
- how repeated markets and related events affect denominators
- why one cohort cannot establish edge

## 27. Commit and push

Commit all verified work.

Push:

`arepo-complete-short-horizon-universe`

Do not merge to `main`.

Do not deploy.

## 28. Final report

Report:

1. branch
2. final commit
3. push status
4. database preservation
5. exact reason the old cohort contained 60 markets
6. whether previous discovery was complete or truncated
7. pagination implementation
8. real page or cursor count
9. complete discovery funnel
10. counts by short-horizon universe
11. total analysed markets
12. proof that top ten is display-only
13. full directional and shadow coverage
14. refresh cadence
15. measured scan duration
16. snapshot schema
17. trajectory definitions
18. Signal Lab layout changes
19. market-detail history
20. future cohort construction
21. Replay universe selection
22. freeze-to-close implementation
23. final-resolution handling
24. unique-market and event denominators
25. scheduler changes
26. backend test count
27. frontend test count
28. Playwright test count
29. production-build result
30. exact local verification commands
31. remaining limitations
32. whether the branch is safe for manual review before deployment

Do not claim that Arepo has an edge merely because complete scanning and Replay now work.
