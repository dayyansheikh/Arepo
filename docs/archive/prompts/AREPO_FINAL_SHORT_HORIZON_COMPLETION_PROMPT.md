# Arepo Final Completion Pass: Exhaustive Short-Horizon Discovery, Fully Wired Replay and Product Simplification

## Role

You are the Opus lead product, quantitative research, backend, data-engineering, frontend, infrastructure and QA manager for Arepo.

This is a completion pass. It is not an audit-only pass, foundation pass, design proposal, synthetic demonstration or documentation-only pass.

Work autonomously through diagnosis, implementation, additive migration, real-data collection, real-browser verification, full regression testing, documentation, commit and push.

Use Sonnet subagents for bounded parallel work where useful. Opus owns architecture, integration, code review, real-data verification and the final completion decision.

Use natural British English. Do not use em dashes in user-facing copy.

Do not deploy. Do not merge to `main`. Do not ask routine questions. Do not stop after planning.

## Starting point

Repository:

`/Users/DayyanSheikh/Projects/astrolabe`

Expected branch:

`arepo-complete-short-horizon-universe`

Expected commit:

`51564b1`

Before changes:

1. Read `CHECKPOINT.md`, `TASKS.md`, `DECISIONS.md`, `FINAL_STATUS.md`.
2. Read all market-discovery, Signal Lab, Opportunities, Replay, scheduler, API and deployment documentation.
3. Inspect every change in `740e6cf..51564b1`.
4. Inspect the backend, frontend, migrations, tests and `render.yaml`.
5. Confirm `backend/astrolabe.db` exists.
6. Record row counts for every research and discovery table.
7. Create a timestamped database backup.
8. Create safety tag:

   `arepo-before-final-short-horizon-completion`

9. Create and work only on:

   `arepo-final-short-horizon-completion`

Preserve all historical prospective data. Do not delete, reset, recreate or replace the database. Use additive, idempotent migrations only.

## Completion doctrine

The previous pass left required work described as “forward-looking”, “foundation-built”, “documented but not wired” or “designed but not implemented”. That is not completion.

A requirement counts as complete only when every applicable layer exists:

1. production backend code
2. additive database migration
3. typed backend API
4. scheduler or CLI path
5. user-facing frontend
6. automated tests
7. real local runtime acceptance
8. exact final evidence

Documentation alone is not completion. A test fixture alone is not completion. A mocked response is not completion. A synthetic public demonstration is not completion. A stable branch is not completion. A narrower substitute is not completion.

The final report must not use these phrases to excuse unfinished requested work:

- forward-looking
- future work
- foundation only
- designed but not wired
- documented but not implemented
- deferred
- left for a later pass
- out of scope
- safe despite being incomplete

If an external API genuinely blocks one real-time outcome after every required strategy below has been attempted, implement all production handling, provide exact evidence and state the blocker. Do not fake completion.

## Truthfulness

Do not fabricate markets, scans, cursors, close times, signal snapshots, cohorts, forward prices, pre-close prices, closures, resolutions, executable returns or edge.

Internal deterministic fixtures may be used for automated boundary tests only.

Synthetic or fixture data must never appear in public Signal Lab, Opportunities, Replay, real scan counts, real cohort counts or real acceptance evidence.

Do not change the current directional model formula, signal thresholds, confidence calculation, Research Priority calculation, evidence-family formulas, baseline definitions, ablation logic, walk-forward logic, edge criteria, historical frozen values or existing prospective outcomes.

Future public selection may change from top 10 to top 20 as a new versioned product-selection policy. Do not rewrite old cohorts.

## Product rules

1. Arepo is a short-horizon product.
2. Public Opportunities and Signal Lab include only active tradable markets closing within 30 days.
3. Every eligible market in that bounded universe is analysed.
4. Ten or twenty is a display and selection count, never a discovery or analysis cap.
5. Opportunities is the public shortlist.
6. Signal Lab is the complete directional signal surface.
7. Replay evaluates real frozen predictions only.
8. Price movement, signal evolution, final resolution and estimated executable performance remain separate.
9. Technical backend diagnostics do not dominate the public interface.
10. Cached fallback is automatic infrastructure, not a public mode.

# A. Exhaustive bounded market discovery

## A1. Query the target date range directly

Do not fetch the first 2,100 records from an unbounded global active universe and then filter by close date.

At scan start define one immutable UTC `scan_origin_at`.

Define:

- `end_date_min = scan_origin_at`
- `end_date_max = scan_origin_at + 30 days`

Query upstream using these bounds so the returned universe is already the short-horizon target universe.

The target is every active open market with a known end date after the scan origin and no later than 30 days after it.

## A2. Implement Gamma keyset correctly

Use current official endpoints:

- `GET /markets/keyset`
- `GET /events/keyset`

Use the cursor contract exactly:

1. first request without `after_cursor`
2. read `next_cursor`
3. send that value as `after_cursor`
4. continue until `next_cursor` is absent

Do not send `offset` to keyset endpoints. Do not guess parameter names.

Use supported filters where available:

- `active=true`
- `closed=false`
- `end_date_min`
- `end_date_max`
- `limit`
- deterministic ordering where valid

Create:

`docs/gamma-keyset-runtime-investigation.md`

Record real redacted evidence:

- exact request path and parameters
- response top-level keys
- first item count
- first `next_cursor`
- second request with `after_cursor`
- whether IDs advanced
- whether cursor advanced
- termination behaviour
- status and concise response for failures

Determine exactly why the previous keyset implementation did not advance. Check response parsing, wrapper shape, parameter name, ordering and endpoint use.

## A3. Use two official discovery paths

Implement both bounded paths:

### Primary
`/markets/keyset`

### Independent verification
`/events/keyset`, extracting nested markets

Reconcile with canonical IDs:

- market ID
- condition ID
- token ID
- event ID

Report:

- primary unique markets
- verification unique markets
- overlap
- only-primary
- only-verification
- deterministic union
- identity conflicts

Use the safe deterministic union. Do not silently discard a market returned by one official path.

## A4. Exhaustive fallback windows

If keyset still fails after correct implementation, use this hierarchy:

1. bounded `/events/keyset`
2. bounded `/markets/keyset`
3. bounded legacy `/events`, ordered by ascending end date
4. bounded legacy `/markets`, ordered by ascending end date
5. split the 30-day range into non-overlapping UTC windows and scan each independently

Initial windows:

- 0 to 6 hours
- 6 to 24 hours
- 1 to 3 days
- 3 to 7 days
- 7 to 14 days
- 14 to 21 days
- 21 to 30 days

Use half-open intervals `[start, end)`.

If one window still hits an upstream pagination cap, recursively bisect that window until it can be exhausted or a documented minimum duration is reached.

Deduplicate the final union.

This is the correct implementation of “scan the next pages”. Do not repeat the same first 21 pages. Do not vary unstable sorting as a substitute for pagination.

## A5. Completeness proof

Set `complete=true` only when:

- every required window terminated normally
- every cursor terminated normally
- no cursor repeated
- no offset failed before exhaustion
- no retry exhausted
- no window remains unscanned
- both official discovery paths were reconciled or a complete authoritative fallback finished
- every returned market was deduplicated or explicitly rejected
- no emergency guard fired

Store:

- scan origin
- target date bounds
- methods
- windows
- pages and cursors
- raw records
- unique markets
- reconciliation
- exclusions
- completeness
- exact failure reason

An incomplete scan must not update public current Opportunities or Signal Lab, create a normal prospective cohort, or claim a bucket contains zero markets. It may retain internal diagnostics.

## A6. Analyse every eligible market

After complete discovery:

1. validate active/open status
2. validate close time
3. resolve tradable outcomes
4. apply existing quality rules
5. apply existing liquidity/spread rules
6. assign time bucket
7. calculate the existing signal for every eligible market
8. store append-only snapshots
9. preserve directional, observation and abstention states
10. rank the complete directional set

Remove all remaining 60-item caps, slices and early stops in production paths.

Do not cap enrichment, scoring, storage or evaluation at 10, 20, 60 or 2,100.

## A7. Time buckets

Assign exactly one primary bucket:

- `closing_0_6h`
- `closing_6_24h`
- `closing_1_7d`
- `closing_7_30d`

Also support cumulative views within 6h, 24h, 7d and 30d.

Store close time, exact time remaining, primary bucket and cumulative memberships at scan/freeze time. Never recalculate historical membership using present time.

# B. Opportunities and Signal Lab

## B1. Opportunities is the public top 20

Opportunities is the clean public shortlist.

For the selected closing window, show up to the strongest 20 directional signals from the complete eligible set.

Default:

- all markets closing within 30 days
- top 20 by existing ranking and Research Priority

Filters:

- Next 6 hours
- Later today
- This week
- This month
- All within 30 days

Show:

> 20 opportunities shown from 83 directional signals across 181 eligible markets.

Do not pad with observations or abstentions.

Do not show HTTP errors, cursor failures or pagination jargon in the primary public view.

When live refresh is delayed, automatically use the latest complete scan and say:

> Live refresh is delayed. Showing the most recent complete update from 15:30.

Technical detail belongs in logs, docs or a collapsed admin diagnostics panel.

## B2. Version the top-20 policy

Store:

- `selection_policy_version`
- `public_selection_limit`
- rank within bucket
- overall 30-day rank
- public membership per supported universe

Use:

`short-horizon-public-20-v1`

Do not rewrite old top-10 cohorts. Replay shows the policy used by each cohort.

## B3. Signal Lab is all directional signals

Signal Lab defaults to all directional signals, not public top ten.

Remove dominant `PUBLIC TOP TEN` badges. A small secondary marker may say:

`Also shown in Opportunities`

Filters:

- closing window
- direction
- strength
- Research Priority
- evidence family
- category/league
- freshness
- trajectory
- Opportunity membership

Do not cap the full dataset. Use server pagination, incremental rendering or virtualisation. The page may render 20 or 30 at a time but must expose the entire directional set and total count.

## B4. Simplify Signal Lab

Top of page:

- Signal Lab
- one sentence:
  > Directional signals across active markets closing within 30 days.
- last updated
- closing-window selector
- useful filters
- actual signal list

Move the long explanation into collapsed `How Signal Lab works`.

Remove primary public text such as:

- HTTP 422
- pagination cap
- keyset
- backend scan
- cursor failure
- internal exception

## B5. Intuitive signal cards

Lead with:

- market question
- selected outcome
- direction
- close time/time remaining
- horizontal strength bar 0–100
- numeric strength
- numeric change over selected period
- plain trajectory
- Research Priority
- concise evidence summary
- market link

Example:

> Direction: Down  
> Strength: 68 / 100  
> +6 over the last hour  
> Strengthening  
> Closes in 4 days

Comparison period:

- Previous refresh
- 15 minutes
- 1 hour
- 6 hours

Strength change is not probability change.

## B6. Replace “Stale”

Audit freshness logic.

Configurable definitions:

- Fresh: updated within 2 refresh intervals
- Refresh delayed: older than 2 intervals but within 6
- Out of date: older than 6 intervals

Normally show:

`Updated 3 minutes ago`

Only show warnings when thresholds are crossed.

Tooltip:

> This describes how recently Arepo received a complete market update. It does not describe signal quality.

Never publish partial-scan results as fresh.

## B7. Signal trajectory

Calculate from immutable complete-scan snapshots:

- previous scan
- ~15m
- ~1h
- ~6h
- first detected
- last updated
- consecutive scans same direction
- direction reversal
- bucket-rank change
- Research Priority change
- evidence changes

Labels:

- New
- Strengthening
- Weakening
- Stable
- Direction reversed
- Refresh delayed
- Out of date
- Temporarily unavailable

Always pair labels with numbers or reasons.

## B8. Market detail history UI

Finish the user-facing market-history section.

Show:

- current signal
- strength history
- price history on same axis
- direction history
- rank history
- Research Priority history
- evidence changes
- first detected
- last updated
- missing intervals
- freshness

Include an accessible table alternative.

# C. Fully wire cohorts and Replay

## C1. Cohort creation from complete scans

Finish scheduled/manual freeze integration.

Every future cohort references a specific complete discovery scan and stores:

- scan ID/completeness
- scan origin
- scheduled time
- actual freeze
- evaluation origin
- selection policy
- full eligible 30-day universe
- bucket membership
- every directional signal
- public top-20 membership
- shadow membership
- observations/abstentions needed for controls
- frozen price/book/signal fields
- close time/time remaining
- model/calculation versions

A normal cohort refuses an incomplete source scan.

Do not modify the old 60-market cohort.

## C2. Create a real acceptance cohort

After a complete real scan succeeds:

1. run a first complete scan
2. run a second complete scan after the configured interval
3. freeze a real prospective acceptance cohort from a complete scan

Use the next valid 6h scheduled bucket where practical, otherwise an explicitly labelled real manual acceptance cohort.

Do not use synthetic data. Do not backdate. Use actual freeze time as evaluation origin.

Verify the cohort contains the full eligible universe, not only 20 opportunities.

## C3. Fully wire outcome collection

Production collection for:

- 1h
- 6h
- 24h
- 7d
- final valid pre-close
- final resolution

Must be idempotent, timestamp-valid, measured from actual freeze, retry-safe and explicit about unavailable data.

Collect every horizon genuinely due during this session. Leave future real horizons pending.

## C4. Freeze-to-close

Implement:

- expected close time frozen with cohort
- quote collection during remaining lifetime
- valid post-freeze observations
- final valid quote at or before close
- midpoint/bid/ask/spread/depth
- source timestamp
- actual close detection
- unavailable reason
- rejection of quotes after close
- no resolution inference from price

Expose freeze price, pre-close price, movement, directional result and executable result where valid.

## C5. Lifecycle states

Implement/display:

- Open
- Closed, awaiting resolution
- Resolved
- Invalid
- Cancelled
- Resolution unavailable

Final resolution must come from genuine stored resolution data.

## C6. Replay controls

Allow:

### Cadence
- Six-hourly
- Daily
- Weekly
- Real manual acceptance where present

### Cohort
- scheduled cutoff
- actual freeze
- lateness
- selection policy

### Frozen closing universe
- Next 6 hours
- Later that day
- Within 7 days
- Within 30 days
- All eligible within 30 days

### Scope
- Public opportunities
- Shadow directional
- All directional
- Full eligible controls

### Evaluation
- 1h repricing
- 6h repricing
- 24h repricing
- 7d repricing
- Freeze to close
- Final resolution
- Estimated executable result

Show:

- observations
- unique markets
- unique events
- repeated-market count
- directional calls
- public opportunities
- shadow
- moved expected
- moved against
- no change
- pending
- unavailable
- invalid
- closed awaiting resolution
- final correct/incorrect
- movement coverage

Five-minute snapshots are history, not separate predictions.

## C7. Keep results separate

Separate panels:

1. Market movement
2. Freeze-to-close movement
3. Final resolution
4. Estimated executable result
5. Signal evolution

Do not combine into one success score.

## C8. Later signal evolution

At nearest complete scan after each horizon show:

- later strength/change
- later direction/reversal
- later Research Priority
- same-bucket rank change
- evidence changes
- trajectory

Never rewrite frozen fields.

# D. Navigation and layout

## D1. Remove global Live/Cached/Replay switch

Remove the public segmented control.

Keep:

- Replay as normal navigation page
- latest complete live scan used automatically
- cached data as automatic fallback
- small notice only when fallback is active
- concise connection indicator only where useful

Remove obsolete public mode state/query parameters.

Do not remove backend caching.

Do not show Replay both as navigation and mode.

## D2. Fix auth footer

Use:

- wrapper `min-height: 100dvh`
- flex column
- header
- main `flex: 1`
- footer after main

Footer reaches bottom on short auth pages and follows content on long pages.

Verify sign-in, sign-up, reset, desktop, mobile and zoom.

## D3. Accessibility/responsiveness

Ensure:

- no horizontal overflow
- signal bars have text equivalents
- no colour-only state
- keyboard filters/disclosures
- accessible charts
- readable mobile cards
- correct focus order
- technical diagnostics do not appear as unexplained public errors

# E. Scheduler and operations

## E1. Signal refresh

Measure complete bounded scan.

Use 5 minutes only if complete duration fits reliably and overlap protection works. Otherwise use 10 minutes with measured justification.

Implement lock/lease, stale-lock recovery, idempotency, completeness status, previous complete fallback, error logging and next scheduled scan.

Browser never performs discovery.

## E2. Cohort/outcome jobs

Fully wire and verify:

- signal refresh
- 6h freeze
- daily freeze
- weekly freeze
- forward collection
- pre-close collection
- resolution collection

Freeze requires complete scan.

Do not deploy.

# F. Tests

## F1. Backend

Test:

- correct `after_cursor`
- response wrapper
- cursor advance/termination/repetition
- markets and events keyset
- nested market extraction
- reconciliation
- bounded 30-day query
- half-open windows
- recursive bisection
- offset fallback
- no gaps/duplicates
- incomplete handling
- >2,100 synthetic records
- >500 eligible short-term records
- every eligible market analysed
- no 60/10/20 analysis cap
- top-20 policy version
- Signal Lab all directional
- old top-10 cohort preserved
- append-only complete-scan snapshots
- freshness/trajectory/reversal
- cohort consumes complete scan
- full universe frozen
- all scopes stored
- actual freeze origin
- 1h/6h/24h/7d
- pre-close quote
- post-close rejection
- lifecycle states
- genuine resolution
- executable separate
- signal evolution separate
- unique denominators
- idempotent reads/collectors

## F2. Frontend

Test:

- Opportunities top 20 with denominator
- Signal Lab all directional
- no dominant public-top-ten badge
- strength bar/delta/trajectory
- plain freshness
- no unexplained stale
- collapsed explanation
- no HTTP/pagination jargon in primary UI
- market history
- Replay controls/results
- global mode switch removed
- cached fallback only when active
- auth footer

## F3. Playwright

Real Chromium and real backend:

- Opportunities
- Signal Lab
- Replay
- navigation
- auth footer
- mobile and 574px
- keyboard
- disconnected/recovery

# G. Real acceptance

## G1. Real bounded discovery

Run production discovery and report:

- scan origin/bounds
- endpoints
- cursors/pages/windows
- raw markets/events
- nested markets
- primary/verification/overlap/union
- conflicts
- eligible counts by bucket
- analysed/directional/public/shadow
- exclusions
- duration
- completeness

Must not be based on first 2,100 global records.

## G2. Two real complete refreshes

Prove second adds immutable snapshots, first unchanged, trajectory uses real scans, and latest complete scan drives public state.

## G3. Real cohort

Create and display a real cohort from complete scan. Prove full universe, public top 20, all directional, shadow, buckets, policy and immutable freeze.

## G4. Outcomes

Collect due real horizons. Leave later states pending. Never synthesize.

# H. Verification and handoff

Run full pytest, ruff, TypeScript, lint, unit tests, clean build and Playwright.

Confirm historical cohort remains:

- 60 entries
- 19 directional
- 10 public
- 9 shadow
- 120 forward observations

Update all project, methodology, API, scheduler and deployment docs.

Commit and push branch:

`arepo-final-short-horizon-completion`

Do not merge. Do not deploy.

## Final report

Report:

1. branch/commit/push
2. database preservation
3. exact prior keyset failure
4. official endpoints and bounded discovery
5. reconciliation/fallback/completeness proof
6. real counts and all analysed
7. Opportunities top 20
8. Signal Lab all directional
9. freshness and card redesign
10. market-history UI
11. cohort wiring and real cohort
12. outcome/pre-close/resolution wiring
13. Replay completion
14. mode-switch removal/cached fallback
15. auth footer
16. scheduler
17. all test/build counts
18. exact verification commands
19. only genuinely unavoidable external limitations with evidence
20. whether every requested production layer is complete
21. safe for manual review before deployment

Do not claim Arepo has an edge.
