# Arepo Opportunity Intelligence and Alerting Refinement

## Role

You are the Opus lead product, quantitative research, data and engineering manager.

Use Sonnet subagents for independent implementation, research, testing, review and repair work.

Opus has authority to make final product and interface decisions where the specification leaves room for judgement.

Do not follow the existing page structure blindly.

You may:

- redesign the Markets page
- merge or separate Markets and Signal Lab
- create an Opportunity Board
- change navigation labels
- reorganise information
- remove low-value elements
- introduce better interaction patterns

Choose the structure that makes Arepo feel like a focused market-intelligence tool rather than a generic Polymarket browser.

Preserve simplicity.

Do not make the interface more crowded.

Every substantial design decision must be documented briefly in `DECISIONS.md`.

Do not pause after planning.

---

# 1. Starting point

Before implementation:

1. Read:
   - `CHECKPOINT.md`
   - `TASKS.md`
   - `DECISIONS.md`
   - `AREPO_MASTER_FINAL_PROMPT.md`
   - current signal-refinement code
   - current tests
   - current official Polymarket documentation

2. Confirm:
   - current branch
   - Git status
   - previous work is committed
   - previous branch is pushed

3. Create a new branch:

`arepo-opportunity-alerts`

4. Do not modify the previously pushed branch directly.

---

# 2. Product objective

Arepo should identify the most important market situations worth investigating.

It should not feel like a wrapper around every Polymarket market.

The default experience should answer:

- Which markets deserve attention today?
- Why are they interesting?
- Which signals support that view?
- What may happen next?
- What should the user examine before acting?

Keep the interface simple and selective.

---

# 3. Product and interface autonomy

Opus should assess the current Markets page, Signal Lab and navigation together.

Choose the strongest information architecture.

Possible approaches include:

## Option A

Opportunity Board as the main page, with Signal Lab as deeper analysis.

## Option B

Merge high-confidence markets and signals into one focused research page.

## Option C

Keep Markets and Signal Lab separate, but make Markets selective and Signal Lab market-linked.

Opus may choose another approach if it is clearly better.

Requirements:

- do not overwhelm the user
- do not show every market equally
- do not duplicate the same information across pages
- every signal must link to a real market
- every market card must explain why it appears
- retain a separate Explore All Markets view for broad browsing
- document the chosen structure and rationale

---

# 4. Market-surveillance indicators

Audit the current signal system first.

Add defensible indicators using public read-only data where available.

Candidate indicators include:

## Consensus-opposing flow

Detect unusually large aggressive trading into a low-probability outcome or against recent price direction.

Normalise by:

- liquidity
- recent volume
- typical trade size
- spread
- available depth

## Large relative trade

Detect trades that are unusually large relative to that market's own trade-size history.

Prefer robust statistics such as:

- percentile rank
- median
- median absolute deviation
- winsorised baselines

## Late large trade

Detect a materially large trade close to the market's close time.

Consider:

- time remaining
- trade size relative to baseline
- price impact
- liquidity
- spread
- reliability of the close time

## Concentrated flow

Measure whether recent volume is dominated by a small number of public wallets.

Possible measures:

- top-wallet share
- top-five-wallet share
- Herfindahl-style concentration
- distinct-wallet count

## Limited public activity history

Where public wallet activity supports it, identify material flow from wallets with little visible Polymarket history.

Use neutral labels such as:

- Limited public activity history
- Single-market activity concentration

Do not call wallets disposable, fake or insider wallets.

## One-sided order book

Retain order-book imbalance, but do not let it drive a strong signal alone.

## Rapid repricing

Detect price movement that is unusual relative to the market's own recent behaviour.

## Spread or depth deterioration

Detect meaningful liquidity weakening alongside price or flow changes.

## Clustered trades

Detect multiple large same-direction trades arriving in a short period.

## Cross-market divergence

Where markets are genuinely related, identify inconsistent pricing.

Do not impose invalid relationships.

---

# 5. Statistical quality

Avoid overfitting.

Requirements:

1. Use market-relative normalisation.
2. Prefer robust statistics.
3. Require minimum sample sizes.
4. Separate independent evidence families:
   - price
   - trade flow
   - order book and liquidity
   - wallet concentration
   - timing
   - cross-market consistency
5. A high-priority alert should normally require at least two independent evidence families.
6. Reduce confidence when:
   - history is short
   - trade data is incomplete
   - wallet coverage is incomplete
   - spread is wide
   - liquidity is poor
   - data is stale
7. Use held-out evaluation where history permits.
8. Do not tune thresholds on the same outcomes used to report results.
9. Document formulas, weights, caps and limitations.
10. Preserve existing causal-selection and book-only safeguards.

---

# 6. Tags

Add concise tags where evidence is sufficient.

Examples:

- Contrarian flow
- Large relative trade
- Late large trade
- Concentrated flow
- Limited activity history
- One-sided book
- Rapid repricing
- Liquidity weakening
- Clustered trades
- Cross-market divergence
- Thin market
- Limited data

Every tag must include:

- tooltip
- plain-English explanation
- methodology link
- timestamp
- data-quality indication

Do not use definitive labels such as suspicious, insider or manipulated.

---

# 7. Search repair

The current keyword search must search the full available market universe, not just the markets already loaded on screen.

Searching for terms such as:

- Microsoft
- MSFT

must:

1. call backend-supported market discovery
2. search active markets
3. optionally search closed markets
4. search:
   - questions
   - descriptions
   - events
   - tags
   - series
   - slugs
   - common company and ticker aliases
5. support pagination
6. include loading and empty states
7. show provenance

Create an alias layer for common companies and tickers, including Microsoft and MSFT.

If no prediction market exists, say so clearly.

Do not fabricate a market.

Do not display a stock quote as though it were a prediction market.

---

# 8. Opportunity Board

Create a focused default experience.

Show up to the top 30 markets for the day using a transparent Research Priority score.

The score may include:

- signal strength
- confidence
- number of independent evidence families
- data quality
- liquidity
- spread
- freshness
- time horizon
- valid market status

Do not call the score expected profit.

Each card should show:

- market question
- relevant outcome
- current probability
- Research Priority score
- confidence
- key tags
- a short explanation
- liquidity quality
- time remaining
- View analysis

Every card must link to the real market analysis page.

Retain an Explore All Markets view for users who want the full market universe.

---

# 9. Daily snapshot

Store a daily immutable snapshot of the top 30 markets.

Store:

- date
- rank
- market
- outcome
- score
- confidence
- tags
- price
- spread
- liquidity
- evidence families
- calculation version
- timestamp

Do not retrospectively rewrite earlier snapshots.

---

# 10. Research alerts

Build an opt-in email alert system.

The alerts may provide a practical directional interpretation, but they must remain honest and non-personalised.

Use wording such as:

> Strong signals suggest this market may be repricing upwards. Have a look yourself and review the evidence before acting.

or:

> Several independent indicators suggest downward pressure may be building. Have a look yourself and check whether the move is continuing.

The alert should then explain:

- what changed
- which indicators fired
- how strong the signal is
- confidence
- liquidity and spread
- what could invalidate the signal
- what the user may want to examine next

A suitable practical section may say:

## What this may suggest

- price pressure may continue if the flow persists
- the market may be slow to reflect new information
- related markets may offer confirmation or contradiction
- liquidity should be checked before drawing conclusions

End each alert with a short disclaimer:

> This is a research signal, not financial advice. Review the market and risks yourself before making any decision.

Do not promise profit.

Do not claim certainty.

Do not give personalised advice.

Do not say buy, sell or stake a specific amount.

---

# 11. Alert eligibility

An immediate email alert should normally require:

- configurable minimum signal strength
- configurable minimum confidence
- at least two independent evidence families
- adequate liquidity
- acceptable spread
- fresh data
- valid market status
- no unresolved data-quality failure

Support:

1. immediate exceptional alert
2. daily digest
3. optional weekly summary

---

# 12. Alert content

Include:

- market question
- relevant outcome
- current implied probability
- signal strength
- confidence
- Research Priority score
- triggered tags
- short directional interpretation
- why it may matter
- what caused the signal
- what may invalidate it
- practical things to inspect
- direct link to the Arepo analysis page
- timestamp
- data mode
- disclaimer

---

# 13. Email engineering

Build a provider-neutral interface.

Use a local development outbox or console sink by default.

External sending must remain disabled until configured.

Use environment variables for:

- provider credentials
- sender
- recipient
- thresholds
- alert enablement

Prepare the recipient variable for:

`dayyansheikh.work@gmail.com`

Do not hardcode credentials.

Add:

- deduplication
- per-market cooldown
- alert history
- retry handling
- failure logging
- disable control
- test mode

Only stop when external email-provider authentication is genuinely required.

---

# 14. Tests

Add tests for:

- consensus-opposing flow
- large relative trades
- late large trades
- wallet concentration
- limited public activity history
- clustered trades
- cross-market divergence
- evidence-family counting
- confidence degradation
- tag eligibility
- Microsoft and MSFT search
- honest no-result search behaviour
- top-30 ranking
- daily snapshot immutability
- alert eligibility
- alert wording
- alert deduplication
- cooldown
- provider failure
- disabled alerts
- no-secrets checks
- no look-ahead
- no mixing of prospective, reconstructed and synthetic data

---

# 15. Quality process

After each phase:

1. run relevant tests
2. use an independent Sonnet reviewer
3. fix confirmed issues
4. have Opus verify fixes
5. commit a stable milestone
6. update `CHECKPOINT.md`
7. update `TASKS.md`
8. update `DECISIONS.md`

At completion run:

- full backend tests
- Python lint
- migrations
- frontend lint
- TypeScript checks
- frontend tests
- production build
- browser smoke tests
- responsive checks
- search smoke tests
- alert dry-run tests
- daily board generation twice to prove idempotency

---

# 16. Documentation

Update:

- README
- architecture
- methodology
- API
- deployment
- limitations
- alert configuration
- data provenance
- privacy and interpretation limits
- portfolio report
- FINAL_STATUS.md

---

# 17. Final push

When verified:

1. commit all work
2. push the new branch to the configured GitHub origin
3. do not force-push
4. report branch, commit hash and push result

At completion report:

- chosen information architecture
- indicators implemented
- tags implemented
- search behaviour
- Microsoft and MSFT results
- Opportunity Board design
- top-30 methodology
- email alert wording
- email delivery status
- authentication still required
- test and build results
- data limitations
- files changed
- commit hash
- GitHub push result

Start now and continue autonomously.
