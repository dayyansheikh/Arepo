# AREPO MASTER FINAL REFINEMENT PROMPT

## Role

Act as the Opus lead product, design, data and engineering manager for the final Arepo refinement.

Use Sonnet subagents for independent workstreams, including:

- interface audit
- chart diagnosis and repair
- brand asset integration
- typography matching
- navigation redesign
- category and sports metadata
- Signal Lab simplification
- Methodology refinement
- weekly signal cohort design
- database migrations
- forward outcome tracking
- Replay redesign
- testing
- accessibility
- visual QA
- documentation
- defect repair

Opus remains responsible for:

- architecture
- delegation
- integration
- truthfulness
- final design decisions
- testing
- code review
- completion judgement

Do not trust a subagent report without reading the changed files and running the relevant tests yourself.

Do not pause after planning.

---

# 1. Starting point and safety

The current Arepo build is functional and should be treated as the stable baseline.

Before changing anything:

1. confirm the current Git branch
2. confirm the working tree status
3. create a clean checkpoint commit
4. create a tag called `arepo-ui-v1`
5. record the current backend test result
6. record the current frontend lint, type-check and production build result
7. preserve all verified quantitative calculations
8. preserve Live, Cached and Replay behaviour
9. do not rewrite Git history
10. do not delete the current working version
11. do not fabricate historical data
12. do not fabricate backtest performance
13. do not fabricate closed-market outcomes
14. do not claim deployment success unless verified

If a database migration is required, preserve existing local data where practical and document the migration.

---

# 2. Product identity

The product name is **Arepo**.

Use natural British English throughout.

Never use em dashes.

Avoid:

- generic AI-style phrasing
- marketing filler
- unexplained jargon
- dense walls of text
- repetitive disclaimers
- overly small text
- unexplained technical abbreviations
- technical implementation language on ordinary user-facing pages

The interface should feel:

- professional
- calm
- direct
- modern
- readable
- quantitative
- understandable to someone new to prediction markets

---

# 3. Brand assets

Use the supplied assets:

- `design-assets/brand/AREPO logo (no word).png`
- `design-assets/brand/AREPO Typeface (word).png`

Use them as the basis of the public Arepo brand treatment.

Integrate them appropriately into:

- main navigation
- favicon exploration
- loading states
- empty states
- README
- report cover
- screenshots

Do not replace the supplied logo design unless there is a clear technical reason.

If the raster files are too soft at small sizes, create faithful optimised derivatives or SVG reconstructions while preserving the exact design.

Document all brand decisions in:

`docs/brand-system.md`

---

# 4. Typography system

## Interface font

Use a modernist sans-serif for the general interface.

Preferred:

- Geist Sans through `next/font`
- otherwise Inter through `next/font`

Use it for:

- body text
- navigation labels
- cards
- forms
- tooltips
- tables
- explanatory text
- metrics
- filters
- status labels

Use tabular numerals for data.

Use monospace only for:

- raw identifiers
- API values
- code
- highly technical tables

## Display heading font

The written wordmark in:

`design-assets/brand/AREPO Typeface (word).png`

defines the visual style required for major headings.

Inspect it carefully.

Identify its:

- width
- weight
- spacing
- geometry
- letter shapes
- casing
- overall tone

Check whether an exact matching licensed font file exists in the supplied assets or project.

If an exact font exists, load it correctly using `next/font/local`.

If no exact font exists:

1. choose the closest suitable licensed web font
2. reproduce the style using weight, tracking, line-height and casing
3. state clearly in `docs/brand-system.md` that it is an approximation

Do not claim an exact match unless verified.

Use the display heading font only for:

- major page titles
- hero headings
- major section introductions
- report-cover headings

Do not use the PNG wordmark as a substitute for normal text headings.

Create separate typography tokens for:

- display headings
- interface text
- data and numerical values

Increase the overall body text size slightly.

Increase heading weight and contrast.

Make titles clearly bold in:

- Signal Lab
- Why this fired
- Methodology
- Replay
- Market detail
- section headers

---

# 5. Navigation

Increase the navigation bar height and visual presence slightly.

Make the logo and Arepo name easier to read.

Improve:

- spacing
- active states
- hover states
- mobile behaviour
- visual hierarchy

Use the supplied Arepo logo and wordmark appropriately.

The navigation should remain restrained and professional.

Recommended pages:

- Overview
- Markets
- Signal Lab
- Replay
- How It Works
- Methodology

---

# 6. Overview information panel

The current pale red information panel looks like an error message.

Replace it with a calm neutral information panel.

It should:

- explain that Arepo is a research tool
- avoid warning or failure styling
- use neutral greys or a very restrained accent
- remain visually separate from genuine errors
- include a concise Methodology link

Reserve Arepo red for:

- selected controls
- important signals
- intentional emphasis
- navigation accents

Do not use red as the default colour for general information.

---

# 7. Charts and price history

Investigate why chart lines are hard or impossible to see.

Fix both data and presentation issues.

## Presentation requirements

- visible line strokes
- sufficient contrast
- clearly distinguishable outcomes
- visible points when few observations exist
- readable axes
- sensible time labels
- reduced grid noise
- useful hover values
- accurate legends
- accessible colour choices

## Data requirements

Verify:

- frontend price-history keys
- outcome ID mapping
- outcome label mapping
- timestamp parsing
- timestamp ordering
- requested historical interval
- duplicate handling
- missing data handling
- live and replay schema consistency
- whether all values are collapsing to one timestamp
- whether sufficient historical data is requested

If only one or two observations exist:

- show visible points
- show a note saying:

> Only limited history is available for this market in the selected view.

Do not leave a chart that appears blank or broken.

Add regression tests for the root cause.

---

# 8. Unknown metadata and unclear labels

Investigate all places showing:

- Unknown
- Parent for derivative
- missing category labels
- missing status labels
- placeholder hierarchy terms
- internal model terminology

Determine whether the issue comes from:

- Gamma API normalisation
- event hierarchy
- market hierarchy
- tag mapping
- missing source fields
- fallback logic
- frontend display logic

Where correct metadata exists, map it properly.

Where metadata is genuinely unavailable:

- hide it if it adds no value, or
- use a clearer phrase such as `Category unavailable`

Do not show internal phrases such as:

- Parent for derivative
- Unknown

unless they are genuinely useful and clearly explained.

---

# 9. API, live feed and freshness labels

The labels `REST`, `WS` and `age` are too technical.

Replace them with:

- `API`
- `Live feed`
- `Updated`

Add accessible tooltips or a compact popover.

Explain:

- API: whether Arepo can retrieve current market data
- Live feed: whether real-time updates are connected
- Updated: how long ago data last refreshed

Use clear states such as:

- Connected
- Updating
- Delayed
- Offline
- Not available in this mode

Do not expose raw technical abbreviations on the surface.

---

# 10. Markets filters and categories

Populate the Markets filters from real metadata.

The Category dropdown must contain useful values.

Requirements:

1. include all reliable broad categories found in current data
2. expose Sports clearly when sports markets exist
3. expose useful sports groupings where data supports them
4. add competition or event grouping where reliable
5. retain Status
6. retain Signal strength
7. retain Probability
8. retain Time to close
9. retain Sort by
10. retain keyword search as a secondary advanced option
11. provide clear empty states
12. explain when no markets match
13. do not invent metadata

Build options dynamically from normalised backend metadata where practical.

Add tests for:

- category extraction
- sports mapping
- competition mapping
- filter behaviour

Soften selected and focus styling if it feels too aggressive.

---

# 11. Market detail page

Keep the current structure but improve readability.

Use:

- slightly larger body text
- clearer headings
- more breathing room
- fewer decimal places
- visible chart series
- consistent rounded cards
- stronger visual hierarchy
- progressive disclosure

Default outcome values should be limited to:

- implied probability
- best bid
- best ask
- spread
- recent movement

Move advanced metrics behind:

`Show advanced market data`

Every specialist metric must have:

- a plain-English tooltip
- a short interpretation
- a link to the correct Methodology section

---

# 12. Signal Lab

Keep the `Why this fired` concept.

Improve the language and hierarchy.

## Surface terminology

Do not show:

- LIMITED
- window 145 obs
- raw implementation identifiers
- unexplained technical component names

Prefer:

- `Data coverage: Limited`
- `Lookback: 145 observations`

Add tooltips explaining them.

## Composite Anomaly

Use a simpler surface label such as:

**Unusual market activity**

The technical term:

`Composite anomaly score`

may appear only in expanded detail and Methodology.

Explain:

- what was unusual
- which factors contributed
- why the score increased
- what a score such as 93 means
- how signal strength differs from confidence
- why it is not proof of insider information
- what limited data coverage means
- what the lookback period means

## Section hierarchy

Make these headings clearly bold:

- Why this fired
- How it is measured
- Why it may matter
- Data quality
- Limitations
- Components

Show the short plain-English explanation first.

Put equations and detailed component tables behind:

`Show technical detail`

Use user-facing component names:

- Unusual price move
- Faster trading activity
- Order-book imbalance
- Spread change
- Available depth change

Technical identifiers may appear only in expanded technical views.

---

# 13. Methodology

Keep the technical depth but improve readability.

Requirements:

- larger text
- clearer headings
- more spacing
- properly rendered fractions
- correct superscripts
- correct subscripts
- correct Greek symbols
- well-spaced formula cards
- plain-English summary before each formula
- variable legend
- worked example
- interpretation
- limitations
- anchored links from product pages

Do not expose mathematical notation by default on ordinary product pages.

---

# 14. Replay and prospective evaluation

The long-term evaluation system must be prospective and free from hindsight selection.

Do not retrospectively choose only markets that later closed or performed well.

## Core principle

Arepo must record the signals it genuinely would have selected at the time, freeze them, then evaluate them later.

## Weekly provisional top ten

During each calendar week:

1. evaluate every eligible current signal
2. require valid market status
3. require sufficient data quality
4. require a valid entry price
5. require documented minimum thresholds
6. rank signals using only information available at the calculation timestamp
7. maintain a provisional weekly top ten
8. allow a stronger eligible signal to replace the current lowest-ranked entry
9. record every provisional change in an audit trail

Do not allow the same market and outcome to occupy multiple weekly slots unless the methodology explicitly permits distinct signal events and prevents concentration.

Document tie-breaking rules.

## Weekly freeze

At a fixed cut-off, preferably Sunday at 23:59 UTC:

1. freeze the final entries
2. assign permanent weekly ranks
3. never replace them afterwards
4. never remove losing entries
5. never remove unresolved entries
6. never change original scores
7. never change original prices
8. never use later information to alter the cohort

If fewer than ten signals qualify, freeze the actual qualifying number and explain why.

## Selection snapshot

For every frozen entry store:

- cohort week
- rank
- market ID
- event ID where available
- condition ID
- token or asset ID
- market question
- selected outcome
- signal direction
- signal timestamp
- freeze timestamp
- signal strength
- confidence
- data-quality level
- entry price
- best bid
- best ask
- midpoint
- spread
- volume
- near-mid depth
- lookback size
- component scores
- calculation version
- source timestamp
- immutable snapshot reference
- expected close time

## Forward tracking

After freezing, record where available:

- price after one hour
- price after 24 hours
- price after seven days
- price at market close
- final resolution
- resolution timestamp
- whether the signalled direction was correct
- raw probability movement
- hypothetical position value
- spread assumptions
- fee assumptions
- pending status

Do not treat fixed-horizon movement and final resolution as the same evaluation.

## Two evaluation views

### Price movement

Evaluate movement after:

- one hour
- 24 hours
- seven days

### Final resolution

For resolved markets, evaluate whether the selected outcome ultimately resolved true.

Keep unresolved markets visible as pending.

## Hypothetical portfolio

Add a clearly labelled simulation using a fixed stake per signal.

Show:

- stake per signal
- total allocated
- realised value
- unrealised value
- completed return
- pending value
- spread assumptions
- fee assumptions
- completed positions
- pending positions

This is a simulation.

Do not present it as real trading or evidence of future profitability.

Define exactly how a position is entered and valued.

Do not use an entry price that was unavailable at the signal timestamp.

## Replay interface

The page should answer this first:

> If Arepo had selected these signals at the time, what happened afterwards?

Allow users to:

- choose a week
- inspect selected markets
- see why each signal qualified
- see entry price
- see later prices
- see final resolution
- distinguish correct, incorrect and pending
- switch between price movement and final resolution
- inspect portfolio assumptions
- expand technical methodology

Show the actual markets used.

Use a plain summary such as:

> Arepo selected eight qualifying signals this week. Four later moved in the expected direction, two moved against it and two remain pending.

Do not show a hit rate without:

- denominator
- pending count
- evaluation horizon

## Historical limitations

Use real historical data only where it can be reconstructed accurately from timestamped public records.

Do not invent earlier cohorts.

If historical snapshots do not exist, begin prospective tracking from the first verified run.

Clearly separate:

- prospective real cohorts
- honestly reconstructed historical examples
- synthetic demonstration data

Synthetic data must never be mixed into real performance statistics.

---

# 15. Scheduling and automation

Provide idempotent commands for:

- updating provisional rankings
- freezing the weekly cohort
- collecting forward prices
- checking resolutions

Provide:

- local manual commands
- scheduler-compatible commands
- deployment scheduler documentation

The workflow must not require the browser to remain open.

Assess whether to use:

- hosting-provider scheduler
- GitHub Actions
- another reliable cron service

Do not activate a paid or public external service without user approval.

---

# 16. Suggested database entities

Use an appropriate schema, potentially including:

- `signal_snapshots`
- `weekly_cohorts`
- `cohort_entries`
- `ranking_audit`
- `forward_price_observations`
- `market_resolutions`
- `evaluation_results`
- `calculation_versions`

Use migrations.

Enforce:

- uniqueness
- immutability
- idempotency
- provenance

where practical.

---

# 17. Required evaluation tests

Add tests proving:

- provisional rankings retain only the strongest qualifying entries
- a stronger signal replaces only the current lowest entry
- ties are deterministic
- frozen cohorts cannot be modified
- later data cannot change original ranking
- losing entries remain stored
- unresolved entries remain pending
- repeated scheduler runs are idempotent
- forward observations are not duplicated
- resolution updates do not overwrite entry data
- weekly summaries use correct denominators
- simulated returns use only available entry information
- prospective, reconstructed and synthetic datasets cannot be mixed silently

---

# 18. Database and API

Create the migrations and API endpoints required by the cohort system.

The frontend must not calculate evaluation truth from loose client state.

Expose typed backend responses for:

- available cohort weeks
- cohort summary
- cohort entries
- forward observations
- resolutions
- portfolio simulation
- methodology
- data provenance
- scheduler status where useful

---

# 19. Accessibility

Review:

- text size
- keyboard navigation
- focus states
- tooltip accessibility
- disclosure controls
- colour contrast
- chart alternatives
- table responsiveness
- status labels
- screen-reader labels
- mobile navigation
- reduced motion

Do not use colour alone for:

- success
- failure
- quality
- signal direction
- connectivity

---

# 20. Work phases

## Phase 1

- checkpoint
- audit current UI
- inspect brand assets
- inspect heading style
- inspect chart data flow
- design evaluation architecture

## Phase 2

- navigation
- typography
- display heading font
- logo integration
- neutral information panel
- status labels
- metadata fallbacks

## Phase 3

- charts
- market details
- categories
- sports filters
- market metadata

## Phase 4

- Signal Lab
- Methodology
- terminology simplification

## Phase 5

- weekly provisional ranking
- cohort freezing
- migrations
- storage
- idempotent commands

## Phase 6

- forward tracking
- resolution tracking
- portfolio simulation
- typed APIs

## Phase 7

- Replay redesign
- real cohort display
- provenance
- pending and resolved states

## Phase 8

- independent Sonnet review
- defect repair
- full QA
- documentation
- screenshots
- report
- packaging

After every phase:

1. run relevant tests
2. use an independent Sonnet reviewer
3. fix confirmed issues
4. have Opus verify the fixes
5. commit a stable milestone
6. update `CHECKPOINT.md`
7. update `TASKS.md`
8. update `DECISIONS.md`

---

# 21. Full quality checks

Run:

- all backend tests
- Python lint
- frontend lint
- TypeScript checks
- frontend tests
- production build
- migration tests
- browser smoke tests
- responsive checks
- Live mode checks
- Cached mode checks
- Replay mode checks
- cohort workflow commands
- repeated scheduler runs to prove idempotency

Manually inspect:

- chart visibility
- logo quality
- wordmark quality
- title font similarity
- navigation size
- text size
- Unknown labels
- category filters
- sports filters
- status explanations
- Signal Lab wording
- Methodology links
- Replay summaries
- actual markets shown
- pending states
- resolved states
- no em dashes in user-facing text

---

# 22. Documentation and final deliverables

Update:

- `README.md`
- `docs/architecture.md`
- `docs/methodology.md`
- `docs/API.md`
- `docs/deployment.md`
- `docs/limitations.md`
- `docs/brand-system.md`
- `docs/portfolio-report.md`
- `FINAL_STATUS.md`
- screenshots
- submission ZIP

Document:

- display heading font choice
- whether it is exact or approximate
- when prospective tracking begins
- weekly selection rules
- freeze time
- eligibility rules
- tie-breaking
- entry-price definition
- forward horizons
- resolution logic
- portfolio assumptions
- fee assumptions
- spread assumptions
- data provenance
- scheduler setup
- API limitations

At completion report:

1. files changed
2. migrations added
3. commands added
4. tests added
5. actual test results
6. build results
7. historical-data limitations
8. first prospective cohort date
9. scheduler status
10. manual browser checks still recommended
11. concise changelog grouped into:
   - Brand
   - Typography
   - Interface
   - Data quality
   - Signals
   - Replay
   - Accessibility
   - Technical quality

The final result must be clearer, more readable, more truthful and more useful while preserving the existing quantitative engine.
