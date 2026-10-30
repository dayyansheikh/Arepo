# Arepo Product Simplification, Accounts and Decision-Support Refinement

## Role

You are the Opus lead product, quantitative research, data and engineering manager.

Use Sonnet subagents for independent research, implementation, testing, review and repair work.

Opus has authority to redesign the product where needed.

Do not follow the current interface blindly.

The goal is not to preserve every existing feature on the surface.

The goal is to create a simple, reliable market-intelligence platform that:

- makes sense to someone relatively new to prediction markets
- remains credible to a quantitative prediction-market user
- surfaces a clear statistical hypothesis
- explains why that hypothesis exists
- shows what would confirm or invalidate it
- lets users inspect deeper evidence only when they choose
- supports free accounts and email alerts

Do not make the interface busier.

Prefer fewer, more useful surfaces over a larger number of pages and metrics.

Do not pause after planning.

---

# 1. Starting point

Before implementation:

1. Read:
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
   - existing architecture and methodology documentation
   - current frontend and backend
   - current Opportunity Board, Explore Markets, Signal Lab and Replay implementations
   - current official Polymarket documentation
   - current official documentation for any authentication platform being considered

2. Confirm:
   - current branch
   - Git status
   - previous work is committed and pushed
   - current tests and builds

3. Create a new branch:

`arepo-product-simplification`

4. Do not modify the previously pushed branch directly.

5. Create a checkpoint commit and update `CHECKPOINT.md`.

---

# 2. Product review before implementation

Run two independent product reviews before choosing the final design.

## Reviewer A: capable beginner

Assign a Sonnet reviewer to behave like a numerate user who:

- is new to prediction markets
- wants to identify potential opportunities
- is willing to conduct their own follow-up research
- expects Arepo to do most of the initial filtering and analysis
- does not understand unexplained scores, badges or quantitative shorthand

The reviewer must inspect the current product and report:

- what each page appears to be for
- what is confusing
- which numbers have no obvious use
- where the interface provides data without a conclusion
- what a user would need to know before investigating a market
- which elements should be removed, renamed or hidden

## Reviewer B: prediction-market quant

Assign a different Sonnet reviewer to behave like a quantitative prediction-market researcher.

The reviewer must assess:

- statistical usefulness
- evidence quality
- signal interpretation
- data provenance
- risk of overfitting
- causal validity
- whether Research Priority and confidence are defensible
- whether the product supports forming and testing a market hypothesis
- what professional users need without creating unnecessary complexity

## Opus synthesis

Opus must combine both reviews.

Choose the simplest product structure that genuinely works for both audiences.

Document the chosen architecture and rejected alternatives in `DECISIONS.md`.

---

# 3. Core product purpose

Arepo should help a user answer:

1. Which markets deserve attention?
2. What is Arepo's current statistical hypothesis?
3. Which outcome or direction does the evidence currently favour?
4. Why does the model favour it?
5. How strong and reliable is the evidence?
6. What would confirm the hypothesis?
7. What would invalidate it?
8. What should the user investigate independently?
9. What happened when similar or earlier signals were tested?

Every important screen should answer one or more of these questions.

Do not show a score without explaining how it should affect the user's next step.

---

# 4. Simplify the information architecture

Opus may redesign, merge, rename or remove pages.

The current structure must not be preserved merely because it already exists.

Keep these capabilities in some form:

- a simple Opportunity Board
- Explore Markets
- Signal Lab
- Replay and evaluation
- How It Works
- Methodology
- account and alert settings

A strong default structure may be:

- **Opportunities**: a selective list of markets with clear hypotheses
- **Explore**: the complete searchable market universe
- **Signal Lab**: deeper investigation of signals and evidence
- **Replay**: real historical and prospective evaluation
- **Learn**: How It Works and Methodology
- **Account**: alerts and preferences

Opus may choose a better structure.

Requirements:

- no duplicated information across pages
- no page should open with a wall of unexplained metrics
- advanced evidence should use progressive disclosure
- retain a clean route to inspect all markets
- retain Signal Lab and Replay as meaningful tools
- remove low-value surface information

Move the Arepo origin and brand story out of technical result pages.

Place it in an appropriate About or Learn section.

---

# 5. Opportunity cards and Research Priority

The current Research Priority score is not self-explanatory.

Redesign its presentation.

## Purpose

Research Priority should answer:

> How urgently is this market worth investigating relative to other current markets?

It must not imply expected return or probability of profit.

## Required explanation

For every displayed Research Priority score:

- show a concise label
- provide an accessible tooltip
- explain the score on `How It Works`
- provide the full formula and assumptions in `Methodology`
- show the main factors raising or lowering the score
- explain what a low, medium or high range means
- explain how it differs from signal strength and confidence

## Card redesign

A default opportunity card should focus on:

- market question
- outcome or directional hypothesis
- current probability
- concise hypothesis
- Research Priority with interpretation
- confidence with interpretation
- two or three strongest evidence tags
- time to close
- liquidity quality
- `View analysis`

Do not display information that has no clear decision-support purpose.

Add a clear filter for:

- closing within 24 hours
- closing within 3 days
- closing within 7 days
- all time horizons

The user must be able to focus on short-term opportunities closing within one week.

---

# 6. Market analysis and statistical hypothesis

When a user opens a market, the page should lead with a clear, cautious statistical hypothesis.

Example structure:

## Current model view

> Arepo currently sees moderate evidence favouring the Yes outcome over the next seven days.

or:

> Arepo does not currently have enough independent evidence to favour either outcome.

Then show:

- directional view
- signal strength
- confidence
- Research Priority
- evaluation horizon
- concise reason
- key evidence
- key risks
- what would confirm it
- what would invalidate it
- what to investigate independently

This must be generated from actual computed evidence.

Do not create a directional view when the evidence is insufficient.

Do not imply certainty.

Do not personalise the recommendation.

Use a concise disclaimer:

> This is a statistical research hypothesis, not financial advice. Check the evidence, market rules and risks yourself before making any decision.

## Progressive disclosure

Default view:

- conclusion
- evidence summary
- risks
- next research steps

Expandable view:

- component values
- equations
- order-book detail
- trade-flow detail
- wallet concentration
- historical comparisons
- data provenance

Reuse the clean expandable presentation currently used for advanced market data.

---

# 7. Signal Lab redesign

Keep Signal Lab, but make its purpose obvious.

Signal Lab should answer:

> Which unusual market signals are active, which markets do they affect, and what hypothesis do they support?

Every signal must:

- name and link to the specific market
- identify the relevant outcome
- state the directional implication, if any
- state the time horizon
- show why it fired
- show evidence families
- distinguish signal strength from confidence
- explain whether the signal is actionable, observational or inconclusive
- show what would confirm or invalidate it

Do not show both Yes and No as unexplained Composite Anomalies.

Where both sides have related signals:

- explain the relationship
- identify whether they are mathematically complementary
- avoid displaying them as two independent opportunities
- consolidate them where that is clearer

Rename or reorganise Composite Anomaly if needed.

Use Opus product judgement.

---

# 8. Tags and contextual explanation

Current tags do not provide enough meaning.

Every tag must support:

- hover
- keyboard focus
- click or tap
- plain-English definition
- why it matters
- how it contributes to the model
- limitations
- exact Methodology link

Examples:

- Rapid repricing
- Large relative trade
- Contrarian flow
- Clustered trades
- One-sided book

When clicked, a tag may open:

- a compact popover
- a side panel
- the relevant Methodology section

Choose the least disruptive design.

Do not make users leave the market page merely to understand a tag.

Document each tag in Methodology with:

- definition
- formula
- threshold
- minimum data requirements
- evidence family
- weight or role
- false-positive risks
- worked example where useful

---

# 9. Accounts and authentication

Build a free account system.

Users should be able to:

- create an account
- confirm their email
- sign in
- sign out
- reset their password or use a secure passwordless flow
- manage alert preferences
- disable alerts
- delete their account
- view recent alerts
- save selected markets where useful

## Architecture choice

Opus must assess the existing Next.js and FastAPI architecture before choosing authentication.

A strong default is Supabase because it combines:

- email authentication
- Postgres
- account storage
- row-level security
- Next.js server-side session support

However, Opus may choose another mature solution if it clearly fits the architecture better.

Document the decision.

Do not build password storage or cryptography from scratch.

Do not store plaintext passwords.

Use email verification.

Use secure cookie-based sessions or another well-supported secure model.

Apply rate limiting to account endpoints.

Use CSRF, session, redirect and origin protections appropriate to the selected framework.

## Development fallback

The project must remain runnable before external authentication credentials are configured.

Provide:

- `.env.example`
- a documented local development mode
- clear disabled or setup-required states
- no committed credentials

Only stop for user involvement when creating or authenticating the external account is unavoidable.

---

# 10. User database and preferences

Create the required database schema and migrations.

Possible entities include:

- user profiles
- alert preferences
- saved markets
- alert subscriptions
- alert history
- account deletion records or audit events
- user consent timestamp
- authentication provider identifier

Each user must only be able to access their own data.

If using Supabase, use Row Level Security appropriately.

Do not expose service-role secrets to the browser.

Alert preferences should include:

- immediate exceptional alerts
- daily digest
- weekly summary
- minimum Research Priority
- minimum confidence
- preferred categories
- short-term only toggle
- maximum time to close
- email enabled
- alert pause
- unsubscribe

Keep the settings interface simple.

---

# 11. Account user experience

Add:

- Sign up
- Sign in
- Account
- Alert settings

Do not let account controls dominate navigation.

The public platform should remain browsable without an account.

Require an account only for personalised features such as:

- email alerts
- saved markets
- personal preferences
- alert history

The sign-up flow should explain the value simply:

> Create a free account to receive high-priority Arepo research alerts and manage the markets you follow.

Do not use aggressive conversion language.

---

# 12. Alerts and user-owned subscriptions

Connect the existing provider-neutral alert engine to user preferences.

Requirements:

- verified email only
- opt-in consent
- per-user thresholds
- per-user categories
- short-term opportunity preference
- deduplication
- cooldown
- unsubscribe
- account-level pause
- global emergency disable
- delivery history
- provider failure handling
- retry policy
- no secrets in source control

Alert copy may provide a directional statistical hypothesis.

Example:

> Strong independent signals currently favour further upward repricing in this market. Have a look yourself and review the supporting evidence before acting.

Then explain:

- market and outcome
- current probability
- hypothesis
- time horizon
- signal strength
- confidence
- Research Priority
- triggered evidence
- what changed
- what may confirm it
- what may invalidate it
- liquidity and spread
- direct link to the analysis

End with:

> This is a statistical research signal, not financial advice. Check the evidence, market rules and risks yourself before making any decision.

Do not promise profit.

Do not give personalised financial advice.

Do not tell the user how much money to use.

---

# 13. Performance and loading speed

The site currently feels slow.

Profile before optimising.

Measure:

- backend API latency
- Polymarket request count
- repeated requests
- frontend waterfall
- page rendering
- bundle size
- chart loading
- Opportunity Board generation
- Signal Lab requests
- database queries

Then improve the largest bottlenecks.

Consider:

- server-side caching
- stale-while-revalidate
- request deduplication
- batched Polymarket endpoints
- background data refresh
- database indexes
- pagination
- lazy-loaded advanced detail
- loading skeletons
- optimistic navigation only where safe
- reduced frontend bundle
- parallel independent requests
- cancellation of stale searches

Do not hide slow behaviour behind fake data.

Display meaningful loading and degraded states.

Set measurable performance targets and record before-and-after results.

---

# 14. Replay and historical evaluation

Keep Replay.

Investigate whether Polymarket historical prices can support retrospective evaluation over previous weeks.

Use current official price-history interfaces and actual timestamped data.

## Modes

Clearly separate:

### Prospective cohorts

Signals genuinely recorded and frozen at the time.

### Historical reconstruction

Signals reconstructed from historical data only when all required features were available at that historical timestamp.

### Synthetic demonstration

Development or educational examples.

Never mix these result sets.

## Historical weeks

Where data permits:

- allow selection of past weeks
- reconstruct candidates using only information available at the time
- show the selected markets
- show entry price
- show later price
- show resolution where available
- state which features could and could not be reconstructed
- lower confidence when order-book, wallet or trade-flow history is unavailable

Do not pretend a full historical signal can be reconstructed using present-day order books or wallet states.

Use price-only or partial reconstruction only when labelled accurately.

Keep the prospective system as the primary long-term performance record.

---

# 15. How It Works and Methodology

Update both layers for every new feature.

## How It Works

Explain simply:

- Opportunity Board
- statistical hypothesis
- directional view
- Research Priority
- signal strength
- confidence
- evidence families
- tags
- Replay modes
- alerts
- accounts and preferences

## Methodology

Explain technically:

- formulas
- weights
- thresholds
- minimum samples
- evidence-family rules
- causal safeguards
- overfitting controls
- Research Priority calculation
- directional hypothesis generation
- confidence calculation
- tag definitions
- backtest reconstruction limits
- alert eligibility

Every new metric or label must have:

- a plain explanation
- a technical explanation
- an anchored link

---

# 16. Testing

Add tests for:

## Authentication

- sign-up
- email verification state
- sign-in
- sign-out
- expired sessions
- invalid sessions
- password reset or passwordless flow
- route protection
- user-data isolation
- account deletion
- unauthenticated public access
- rate limiting

## Preferences

- saving preferences
- per-user isolation
- short-term-only setting
- category preferences
- alert pause
- unsubscribe
- defaults

## Product explanations

- Research Priority tooltip and links
- tag tooltips and Methodology anchors
- market hypothesis rendering
- insufficient-evidence state
- complementary Yes and No handling
- no unexplained score state

## Alerts

- only verified and opted-in users receive alerts
- per-user thresholds
- category filters
- time-to-close filters
- deduplication
- cooldown
- global disable
- unsubscribe
- no personalised advice
- correct disclaimer

## Performance

- caching
- request deduplication
- pagination
- no duplicate market fetches
- acceptable endpoint timing where deterministic tests permit

## Replay

- strict no-look-ahead
- historical cut-off handling
- partial reconstruction labelling
- separation of prospective, reconstructed and synthetic results

---

# 17. Quality and review process

Work in phases.

After every phase:

1. run relevant tests
2. use an independent Sonnet reviewer
3. fix confirmed defects
4. have Opus inspect the implementation
5. commit a stable milestone
6. update `CHECKPOINT.md`
7. update `TASKS.md`
8. update `DECISIONS.md`

Before completion, run:

- full backend tests
- Python lint
- migrations
- frontend lint
- TypeScript checks
- frontend tests
- production build
- authentication integration tests
- browser smoke tests
- mobile and responsive checks
- accessibility checks
- performance measurements
- alert dry runs
- replay checks

Repeat both user reviews after implementation:

- capable beginner
- prediction-market quant

Do not accept the redesign until both reviewers can explain:

- what the product does
- what the main hypothesis is
- what the important scores mean
- what the next research step is
- what the product cannot conclude

---

# 18. Documentation

Update:

- README
- architecture
- methodology
- API
- deployment
- limitations
- authentication setup
- account and privacy documentation
- alert configuration
- data provenance
- performance notes
- portfolio report
- FINAL_STATUS.md

Document external setup still required.

---

# 19. External setup boundaries

Do not create paid services or public deployments without approval.

If an external authentication or database project is needed:

1. complete all code that can be completed locally
2. provide exact setup steps
3. state which values are required
4. stop only at the point where the user must authenticate or create the project
5. never request passwords in chat
6. never commit service keys

---

# 20. Final push and report

When verified:

1. commit all work
2. push the branch to the configured GitHub origin
3. do not force-push

Report:

- chosen information architecture
- what was removed or simplified
- account architecture
- authentication status
- database migrations
- alert preference system
- market hypothesis design
- Research Priority explanation
- tag explanation system
- Signal Lab redesign
- Replay historical capability
- measured performance improvement
- actual test results
- build result
- external setup still required
- branch
- commit hash
- push result

Start now and continue autonomously.
