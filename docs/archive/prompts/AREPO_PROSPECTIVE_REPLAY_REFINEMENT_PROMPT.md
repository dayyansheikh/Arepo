# Arepo Prospective Replay Results and Short-Horizon Refinement

You are the Opus lead product, quantitative research, backend, frontend and QA manager for Arepo.

Work autonomously and complete the implementation, testing, documentation, commit and push.

Use Sonnet subagents for independent backend, frontend, quantitative-review and browser-QA work where useful. Opus remains responsible for final decisions and verification.

Use natural British English.

Do not use em dashes in user-facing text.

Do not deploy.

Do not ask routine implementation questions.

## Starting point

Repository:

`/Users/DayyanSheikh/Projects/astrolabe`

Expected starting branch:

`arepo-final-runtime-acceptance-fix`

Expected starting commit:

`6c8d2e6`

Before changing anything:

1. Read `CHECKPOINT.md`, `TASKS.md`, `DECISIONS.md`, `FINAL_STATUS.md` and all relevant Replay, prospective research, evaluation and deployment documentation.
2. Inspect the current branch, Git state, database schema, API routes, Replay frontend, research CLI, evaluation engine and automated tests.
3. Confirm that `backend/astrolabe.db` exists.
4. Preserve every existing cohort, entry, forward observation and resolution row.
5. Create a database backup.
6. Create a safety tag:

   `arepo-before-prospective-replay-refinement`

7. Create and work only on:

   `arepo-prospective-replay-refinement`

Do not delete, reset, recreate or replace the database.

Do not destructively migrate populated tables.

## Non-negotiable research constraints

Do not change:

- directional model logic
- signal thresholds
- confidence calculation
- Research Priority calculation
- cohort eligibility
- evidence-family calculations
- baseline definitions
- ablation logic
- walk-forward logic
- edge criteria
- frozen historical values
- existing prospective results

This is a product, evaluation-display and Replay refinement pass.

It is not model tuning.

Do not fabricate results.

Do not describe a correct midpoint move as proof of profit or edge.

Do not alter the frozen cohort after observing outcomes.

## Authoritative real cohort context

A genuine prospective six-hour cohort exists in the local database.

It contains:

- universe size: 60
- public selections: 10
- shadow directional: 9
- observations: 9
- abstention controls: 32
- total directional calls: 19

The actual evaluation origin is the actual freeze time, not the scheduled bucket time.

The current real results include one-hour and six-hour forward observations.

The six-hour directional result currently contains:

### Public selections

- 2 moved as expected
- 2 moved against the call
- 6 did not change

### Shadow directional

- 2 moved as expected
- 2 moved against the call
- 5 did not change

### Combined

- 4 moved as expected
- 4 moved against
- 11 did not change

These values must come from the database at runtime. Do not hard-code them into the product.

## 1. Make Replay prospective-only

Remove the following from the public Replay interface:

- Reconstructed analysis
- Synthetic demonstration
- any reconstructed or synthetic tabs
- any default or query-string route that presents reconstructed or synthetic data as a user-facing Replay mode

Replay should now mean:

> Real predictions genuinely frozen before later prices became known.

Synthetic fixtures may remain internally where required for automated tests.

Do not delete synthetic test infrastructure merely to remove the public tab.

Reconstructed data may remain internally where other code genuinely needs it, but it must not appear in the public Replay product.

Remove obsolete public navigation, labels, explanatory text and empty states relating to reconstructed or synthetic Replay.

Legacy Replay query parameters should redirect or normalise safely to the prospective Replay page rather than displaying removed modes.

## 2. Redesign Replay around real cohort selection

The page must let the user choose a real frozen cohort.

Provide clear selectors for:

### Cohort cadence

- Six-hourly
- Daily
- Weekly

Only show cadences for which real prospective cohorts exist.

A weekly cohort should be described as a cohort frozen by the weekly scheduled job.

A manually created six-hour cohort must not be described as a weekly cohort.

### Freeze

Within the selected cadence, allow the user to choose the actual cohort using:

- scheduled cut-off time
- actual freeze time
- lateness where relevant

Default to the newest real prospective cohort.

Outcomes must always be evaluated from `evaluation_origin_at` or actual freeze time.

## 3. Add evaluation-horizon selection

Allow the user to select:

- 1 hour
- 6 hours
- 24 hours
- 7 days
- Final resolution

Only mark a horizon evaluable when the stored observation exists.

Show pending clearly when a horizon is not yet due or has not yet been collected.

Keep short-term repricing and final resolution conceptually separate.

For 1h, 6h, 24h and 7d, the question is:

> Did the selected outcome’s market price move in Arepo’s stored direction?

For final resolution, the question is:

> What did the market finally resolve to?

Do not treat a favourable short-term move as a correct final-outcome forecast.

## 4. Add frozen time-to-close filters

Replay should focus on shorter-term, relevant markets.

Add a filter based on the time remaining at the moment the cohort was frozen.

Use the frozen `research_entries.time_remaining_hours` or equivalent point-in-time field.

Never calculate this filter using the market’s current time-to-close.

Provide these options:

- Closing within 6 hours
- Closing within 24 hours
- Closing within 7 days
- Closing within 30 days
- All closing times

Use clear labels such as:

> Closing within 6 hours at the time of the freeze

Do not imply that closing sooner means the signal is stronger.

## 5. Show the top ten for each selected set

For each combination of:

- cohort
- evaluation horizon
- time-to-close filter

show up to ten highest-ranked directional signals.

The default should be:

> Top directional signals

Use frozen rank and frozen Research Priority only.

Do not recalculate signal scores using later information.

Do not alter the stored rank.

Where filtering creates a subset, display the highest frozen-ranked entries within that subset.

Do not force ten when fewer than ten qualify.

Show:

> Showing 7 qualifying directional signals

rather than filling the list with weaker, observational or abstention rows.

Provide a scope control where useful:

- Top public selections
- Top directional signals, including shadow signals

Default to the clearest product interpretation after independent review.

Do not mix observation or abstention-control rows into the main directional result table.

Their counts may remain visible in the cohort methodology summary.

## 6. Add an intuitive cohort-results section

The page currently shows coverage but does not clearly answer:

> Were Arepo’s directional calls right?

Add a prominent section directly below the cohort and horizon controls.

Use a title such as:

> Did the market move as expected?

For the selected horizon, show a concise sentence such as:

> Of 19 directional calls, 4 moved as expected, 4 moved against the call and 11 did not change.

Do not lead with a misleading hit rate that excludes flat results.

Where a hit rate among moving markets is shown, label it explicitly:

> Hit rate among markets that moved: 50% (4 of 8)

Also show:

- total directional calls
- moved as expected
- moved against
- no change
- pending
- unavailable
- movement coverage
- public-selection result
- shadow-directional result

Do not claim public selections outperform shadow signals unless the stored evidence supports it.

## 7. Add a market-by-market result table

For each displayed signal, show:

- frozen rank
- market question
- selected outcome
- role
- Arepo direction
- frozen midpoint
- selected-horizon midpoint
- movement in percentage points
- time remaining at freeze
- result label

Use intuitive result labels:

- Moved as expected
- Moved against the call
- No price change
- Pending
- Unavailable
- Invalid

Include a short tooltip or explanation:

> Moved as expected means the selected outcome’s midpoint moved in Arepo’s stored direction over the selected horizon. It does not mean the market finally resolved correctly or that a trade would have been profitable.

Do not use colour alone to convey the result.

Allow rows to link to the relevant market detail page.

Keep the table readable on mobile and narrow desktop widths.

## 8. Show midpoint movement separately from executable performance

Where the backend already supports estimated executable performance, display it separately from midpoint movement.

Use distinct labels:

- Midpoint movement
- Estimated result after spread and costs

Do not silently calculate profit using midpoint prices.

If executable data is unavailable, show:

> Executable result unavailable for this observation.

Do not replace missing bid, ask, spread, depth or cost inputs with invented values.

## 9. Correct stale and misleading text

Remove or replace text stating:

> Prospective cohorts are real signals frozen at the weekly cut-off.

Replace it with dynamic wording such as:

> Prospective cohorts contain real signals permanently recorded at a six-hourly, daily or weekly cut-off. Outcomes are measured from the actual freeze time.

The exact copy should match the selected cohort cadence.

Remove:

> Prospective tracking has not started yet.

Replace it with a data-driven state.

When cohorts exist, say that tracking has started and show the first and latest freeze.

When none exist, show a genuine empty state.

Also fix any statement implying that the browser itself collects results.

Use accurate wording such as:

> Replay grows when scheduled backend jobs freeze cohorts and collect later prices. Leaving this page open does not collect additional evidence.

Locally, do not claim collection is automatic merely because the site is open.

In production, scheduled jobs may be described as automatic only if the deployment configuration genuinely contains them.

## 10. Clarify scheduled versus actual freeze

Keep the current timing banner but simplify it.

Show:

- Scheduled cut-off
- Actually frozen
- Lateness
- Evaluation starts from

Use plain language.

For example:

> Scheduled for 01:00. Actually frozen at 02:24, 84 minutes late. All later price measurements start from 02:24.

Do not overemphasise lateness where it does not invalidate the cohort.

Continue excluding only cohorts that breach the existing excessive-lateness rule.

Do not change that rule.

## 11. API and backend work

Inspect the current research API.

Implement or extend typed endpoints as needed to provide:

- available real prospective cohorts
- cohort cadence
- scheduled cut-off
- actual freeze time
- evaluation origin
- lateness
- role counts
- directional entries
- frozen ranking fields
- frozen time-to-close
- forward observations by horizon
- per-entry result state
- aggregate result counts
- movement coverage
- midpoint movement
- executable result where genuinely available
- final resolution separately

Prefer server-side calculation of evaluation truth.

The frontend must not derive important result states from loose client assumptions.

Use the repository’s existing evaluation functions and result-state definitions where available.

If equivalent result logic is duplicated, consolidate it safely.

Make API behaviour deterministic and fully tested.

## 12. Weekly operation

Inspect `render.yaml` and deployment documentation.

Confirm that real scheduled cohort jobs exist for:

- six-hourly
- daily
- weekly

Do not deploy them.

Do not change schedules merely because this local cohort was manually frozen.

If the weekly freeze job is missing or incorrectly configured, fix repository-side configuration and documentation.

If it is already correct, record that fact without unnecessary modification.

Document that the local browser does not perform these jobs.

## 13. Handle existing localhost processes safely

Before starting development servers, inspect ports 3000 and 8000.

Do not start duplicate frontend or backend instances.

Identify any server processes left running by the previous automated runtime test.

Reuse healthy development servers where safe, or stop only the exact identified development PIDs before starting clean replacements.

Do not use broad `pkill` commands that could terminate unrelated Node or Python work.

At the end, stop any temporary servers started solely by this task unless the existing project convention says to leave them running.

Document what was found.

## 14. User-interface quality

Keep the current Arepo branding and layout.

Do not perform a broad redesign.

Make the Replay flow simple:

1. Choose cohort cadence and freeze.
2. Choose market closing window.
3. Choose evaluation horizon.
4. See the concise result.
5. Inspect the top signals.

Avoid overwhelming the page with methodology text.

Move extended definitions into tooltips or a concise expandable explanation.

Ensure:

- no horizontal overflow
- no clipped popovers
- no cramped controls
- readable tables
- keyboard accessibility
- screen-reader labels
- clear loading, disconnected and empty states

## 15. Required tests

Add backend tests for:

- real prospective cohorts only
- cadence filtering
- newest-cohort default
- frozen time-to-close filtering
- 6h, 24h, 7d and 30d buckets
- top ten ranking within each filtered set
- fewer than ten results
- public-only versus all-directional scope
- correct result state
- incorrect result state
- flat result state
- pending
- unavailable
- final resolution kept separate
- actual freeze used as evaluation origin
- no synthetic or reconstructed rows entering public prospective results
- no mutation of frozen entries
- idempotent API reads

Add frontend unit tests for:

- removed reconstructed and synthetic tabs
- cohort selectors
- closing-window filters
- horizon selector
- concise result sentence
- market-by-market labels
- pending horizons
- correct dynamic cadence copy
- removal of “tracking has not started” when data exists
- no misleading generic weekly-cut-off text
- no implication that the open browser collects data

Add real Playwright tests using Chromium for:

- default prospective Replay page
- real local cohort
- switching between 1h and 6h
- changing time-to-close filters
- top ten ordering
- fewer-than-ten state
- per-market result labels
- narrow viewports
- no horizontal overflow
- no reconstructed tab
- no synthetic tab
- direct navigation and refresh
- disconnected API state and recovery

Use the real backend and preserved local database for final runtime acceptance.

Do not rely only on mocked unit tests.

## 16. Verification gate

Run:

### Backend

- full `pytest` suite
- `ruff check`

### Frontend

- TypeScript check
- lint
- full unit tests
- production build
- Playwright browser suite

Manually verify the current real six-hour cohort displays the stored results correctly.

Verify that:

- public selections show 2 expected, 2 against and 6 flat
- shadow directional shows 2 expected, 2 against and 5 flat
- combined shows 4 expected, 4 against and 11 flat

These are acceptance checks against the current database, not values to hard-code.

Confirm that the existing one-hour and six-hour rows remain intact.

Confirm that no database row was lost or rewritten.

## 17. Documentation

Update:

- `CHECKPOINT.md`
- `TASKS.md`
- `DECISIONS.md`
- `FINAL_STATUS.md`
- relevant Replay methodology
- local usage instructions
- deployment checklist
- scheduler documentation

Explain:

- what prospective Replay now means
- how cohort cadence differs from evaluation horizon
- how time-to-close filtering works
- what “moved as expected” means
- why flat markets remain part of the denominator
- why a high hit rate among only moving markets can be misleading
- why one cohort cannot demonstrate edge
- how local and production collection differ

## 18. Commit and push

Commit all verified work.

Push the new branch.

Do not merge to `main`.

Do not deploy.

## 19. Final report

Report:

1. branch
2. final commit
3. push status
4. database preservation status
5. localhost processes discovered
6. removed public Replay modes
7. new cohort selectors
8. new closing-window filters
9. ranking behaviour
10. result labels
11. API changes
12. scheduler findings
13. backend test count
14. frontend test count
15. Playwright test count
16. production-build result
17. exact local verification commands
18. remaining limitations
19. whether the branch is safe for manual review before deployment

Do not claim completion until the real browser, real API and real local cohort all pass.
