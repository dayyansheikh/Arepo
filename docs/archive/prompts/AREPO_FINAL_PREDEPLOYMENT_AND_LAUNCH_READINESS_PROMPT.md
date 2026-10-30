# Arepo Final Pre-Deployment Repair and Launch Readiness
## Autonomous implementation prompt

## Purpose

You are the Opus lead backend, database, frontend, infrastructure, deployment and QA manager for Arepo.

The user will perform the external account and secret-entry steps. You must complete every repository-side repair, migration, deployment configuration, test and verification step required before that handoff.

This pass must leave Arepo in a state where the user can follow one exact checklist and launch it without guessing.

Start from the completed edge-research infrastructure:

- branch: `arepo-edge-research-infrastructure`
- verified commit: `5e2ce9f`

Create a new branch:

`arepo-final-predeployment-launch-readiness`

Create a safety tag:

`arepo-before-final-predeployment-launch-readiness`

Preserve all edge-research functionality from `5e2ce9f`.

Do not change:

- directional model logic
- signal thresholds
- confidence formula
- Research Priority formula
- cohort eligibility
- baseline definitions
- ablation logic
- walk-forward logic
- edge acceptance criteria

This pass is about correctness, migration, operational reliability, user-interface defects and deployment readiness. It is not model tuning and not a general redesign.

Do not pause after planning.

Do not ask the user routine implementation questions.

Stop only for an unavoidable secret, external login, payment approval or irreversible external action.

---

# 1. Read and record the current state

Read completely:

- `CHECKPOINT.md`
- `TASKS.md`
- `DECISIONS.md`
- `FINAL_STATUS.md`
- `docs/EDGE_RESEARCH_GOAL.md`
- `docs/edge-research-architecture-review.md`
- `docs/edge-research-requirement-traceability.md`
- `docs/edge-research-end-to-end-dry-run.md`
- `docs/edge-research-deployment-handoff.md`
- current `render.yaml`
- all deployment documentation
- current database/bootstrap code
- current ORM models
- current research CLI
- current collectors
- current Signal Lab components
- current tooltip/popover implementation
- current application shell and responsive CSS
- recent Git history

Record a baseline in:

`docs/final-predeployment-baseline.md`

Include:

- current branch and commit
- Git status
- backend test count
- frontend test count
- migration mechanism
- local database path and schema version
- existing research tables and columns
- existing cohort counts
- failed or incomplete cohort records
- current tooltip overflow behaviour
- current horizontal-overflow measurements
- current action-row spacing
- current hosting configuration
- current scheduled jobs
- current deployment blockers

---

# 2. Reproduce and fix the local schema failure

The exact reproduced command is:

```bash
python -m astrolabe.evaluation.research_cli research-freeze --cadence 6h
```

The exact blocking error is:

```text
sqlite3.OperationalError:
no such column: research_entries.momentum_direction
```

The ORM attempted to query current fields including:

- `momentum_direction`
- `orderbook_direction`
- `tradeflow_direction`

against an older existing SQLite `research_entries` table.

The preceding output also contained:

```text
live token data unavailable
```

## Required root-cause analysis

Confirm whether:

- `create_all()` created the table in an earlier schema
- later ORM changes added columns only in code
- `create_all()` did not alter the existing table
- the failed freeze created an incomplete cohort before entry insertion failed
- other ORM columns are also absent
- the same defect could affect PostgreSQL after deployment

Create:

`docs/schema-failure-investigation.md`

Do not solve this only by deleting the local database.

A local reset can exist as an explicitly documented last-resort development option because no real prospective evidence currently exists, but a proper migration path is mandatory.

---

# 3. Implement production-grade migrations

Use the repository's existing migration framework if one exists.

If none exists, add a conventional migration system suitable for SQLite development and PostgreSQL production. Prefer Alembic unless a repository-specific alternative is clearly stronger.

## Migration requirements

1. Create an additive migration from the previous research schema to the current schema.
2. Add every missing field expected by the current ORM.
3. Include at minimum all current per-family direction fields.
4. Compare the complete ORM metadata with an old-schema fixture.
5. Preserve existing rows.
6. Do not drop populated production tables.
7. Use honest nullable/default transitions for old rows.
8. Never invent historical evidence for old rows.
9. Support SQLite.
10. Support PostgreSQL.
11. Be safe to run once.
12. Be harmless to rerun.
13. Record a schema version.
14. Provide an explicit upgrade command.
15. Provide an explicit current-version check.
16. Add a startup/CLI preflight that detects an outdated schema.
17. Fail before cohort creation with an actionable migration message if automatic migration is not enabled.
18. Never allow a low-level missing-column failure halfway through a cohort.
19. Verify compatibility with the selected PostgreSQL connection mode and SQLAlchemy driver.
20. Document how migrations run during deployment.

Create:

- `docs/database-migration-guide.md`
- `docs/production-migration-runbook.md`

Add tests that:

- construct the exact prior SQLite schema
- insert representative data
- run the upgrade
- preserve prior rows
- expose every current ORM field
- rerun safely
- verify current-schema startup
- verify outdated-schema preflight failure
- exercise PostgreSQL-compatible migration SQL
- verify no fabricated historical values

---

# 4. Repair partial cohort behaviour

The failed freeze may have inserted a cohort row before all entries were written.

Audit the local database for:

- incomplete cohort rows
- zero-entry cohorts
- partially inserted entries
- duplicate `(cadence, cutoff_at)` records
- failed transaction boundaries
- status fields that incorrectly imply completion

## Required behaviour

A cohort freeze must be atomic:

- either the cohort and every required universe entry commit successfully
- or no completed cohort is visible

If a recoverable state machine is retained, it must clearly use states such as:

- creating
- frozen
- failed

and a failed record must never appear as valid prospective evidence.

Add:

- one transaction boundary for the freeze
- safe rollback
- idempotent retry
- incomplete-cohort detection
- repair or cleanup command
- duplicate protection
- concurrency protection
- tests injecting a failure midway through entry creation

Do not delete valid cohorts.

Repair or remove only records proven to be incomplete.

Document the exact local repair performed.

---

# 5. Diagnose and harden `live token data unavailable`

Find the exact source of this message.

Determine:

- which upstream endpoint failed
- which market or token failed
- whether the data was temporarily unavailable
- whether identifiers were invalid
- whether a retry is appropriate
- whether an alternate official identifier can resolve it
- whether the market should be excluded
- how the exclusion changes universe completeness

## Required behaviour

- one unavailable token must not crash a complete cohort
- temporary failures use bounded retries with backoff
- invalid markets are skipped with an explicit reason
- every excluded market remains represented in the universe funnel or exclusion record
- logs identify the affected market without exposing secrets
- a high exclusion rate triggers degradation or failure
- complete upstream failure must not create a misleading cohort
- research status exposes the latest degraded run
- actual collection timestamps are retained
- missing values remain missing, not zero

Add tests for:

- one unavailable token
- several unavailable tokens
- complete token endpoint failure
- retry success
- permanent invalid token
- minimum viable universe
- degraded but valid cohort
- rejected cohort due excessive exclusions

---

# 6. Fix Signal Lab tooltip and popover behaviour

The reproduced UI defect is that information popovers render partly outside the screen and force the user to scroll horizontally.

There is also a visible horizontal page scrollbar.

Implement one robust, reusable viewport-aware popover primitive for all information controls.

## Required behaviour

1. Render through a portal or equivalent layer not constrained by card overflow.
2. Anchor correctly to the trigger.
3. Flip horizontally near either edge.
4. Shift vertically near top or bottom.
5. Maintain a safe viewport margin.
6. Use a responsive maximum width.
7. Wrap long text.
8. Never expand document width.
9. Never create horizontal scrolling.
10. Reposition on open, resize and scroll.
11. Remain correct when browser zoom changes.
12. Close on Escape.
13. Close on outside click.
14. Support mouse, keyboard and touch.
15. Use correct roles and ARIA relationships.
16. Preserve visible focus.
17. Avoid covering the trigger where possible.
18. Avoid clipping inside sticky or overflow containers.

Use an existing reliable positioning library if already installed.

A small dependency such as Floating UI is acceptable if justified and tested.

Do not use fragile hard-coded left or right offsets.

Test at:

- 320 px
- 375 px
- 768 px
- 1024 px
- 1280 px
- 1440 px

and browser zoom:

- 80%
- 90%
- 100%
- 110%
- 125%
- 150%

Apply this primitive to every relevant information icon, not only the visible Signal Lab example.

---

# 7. Remove horizontal overflow completely

Audit the Signal Lab route and shared application shell.

Inspect:

- tooltip positioning
- `width: 100vw`
- fixed widths
- minimum widths
- negative margins
- transforms
- sticky containers
- cards
- dropdowns
- action rows
- long market titles
- header controls
- footer
- scrollbar compensation
- positioned elements

## Acceptance condition

At supported widths:

```javascript
document.documentElement.scrollWidth <= document.documentElement.clientWidth
```

Allow a negligible one-pixel rounding tolerance only where proven necessary.

Required:

- no horizontal scrollbar
- no clipped left side
- no off-screen header
- market titles wrap safely
- controls wrap deliberately
- popovers do not alter document dimensions
- vertical scrolling remains normal

Add browser regression tests.

---

# 8. Fix Signal Lab control spacing

The following elements currently visually merge:

- directional qualification badge
- `Why this fired`
- `Show detail` or `Hide detail`

Create a deliberate action layout.

Required:

- badge is visually separate from buttons
- controls have clear horizontal and vertical gaps
- minimum accessible click targets
- clean wrapping on narrow widths
- no overlapping text
- no controls pressed directly against the qualification message
- collapsed and expanded states remain obvious
- keyboard focus remains visible
- no unnecessary redesign

Test:

- long qualification text
- long market title
- expanded detail
- collapsed detail
- desktop
- narrow desktop
- tablet
- mobile
- all required zoom levels

---

# 9. Local end-to-end verification

After migration and UI fixes, run a complete local acceptance test.

## Database sequence

1. Locate the active SQLite database.
2. Back it up with a timestamp.
3. Record current tables and row counts.
4. Run the migration.
5. Verify schema version.
6. Verify all current ORM columns.
7. inspect incomplete cohorts.
8. Repair only proven incomplete records.
9. Verify valid old rows remain.

## Backend sequence

Verify:

- schema preflight
- `/health`
- readiness if implemented
- `/api/research/status`
- research bootstrap
- six-hour freeze
- repeated six-hour freeze
- daily freeze
- weekly freeze
- immediate forward observation
- causal guard
- research status
- synthetic exclusion
- collector degradation reporting

Expected after successful local freezes:

- six-hour cohort count above zero
- daily cohort count above zero
- weekly cohort count above zero
- total frozen markets above zero
- public selections recorded
- shadow directional signals recorded
- observations recorded
- abstention controls recorded
- synthetic excluded
- edge supported remains false
- calibration remains unavailable
- no missing-column exception
- no partial completed cohort

## Frontend sequence

Verify:

- Opportunities
- Explore
- Signal Lab
- Market Detail
- Replay
- research status
- valid route IDs `2694364` and `2822017`
- invalid route handling
- every information popover
- no horizontal overflow
- action spacing
- title exactly `Arepo`
- Back and Forward restoration
- zoom checks

Create:

`docs/FINAL_PREDEPLOYMENT_LOCAL_ACCEPTANCE.md`

No locally testable requirement may remain Fail.

---

# 10. Automated test gate

Run and pass:

## Backend

- full test suite
- ruff
- schema migration tests
- previous-schema upgrade tests
- idempotent migration tests
- partial-cohort rollback tests
- partial-cohort recovery tests
- concurrency tests
- unavailable-token tests
- minimum-universe tests
- PostgreSQL portability tests
- complete research dry run

## Frontend

- TypeScript
- lint
- Vitest
- production build
- popover boundary tests
- outside-click and Escape tests
- keyboard tests
- horizontal-overflow browser tests
- action-row layout tests
- supported viewport tests

Do not weaken tests to obtain a pass.

---

# 11. Decide the production hosting architecture using current official sources

Use current official documentation only.

Compare:

1. Render paid web service plus Render cron jobs
2. Render web service plus one consolidated Render orchestrator cron, if safe
3. Google Cloud Run service plus Cloud Run Jobs and Cloud Scheduler
4. Render Free Web Service plus GitHub Actions
5. Northflank Developer Sandbox
6. Koyeb free service
7. another option only if it is clearly more suitable

Evaluate against Arepo's real requirements:

- FastAPI API
- persistent PostgreSQL
- headless scheduled collection
- six-hour, daily and weekly freezes
- forward observations
- resolution updates
- microstructure collection
- reliable actual timestamps
- retries
- locks
- idempotency
- manual reruns
- job history
- logs
- secrets
- custom domain
- cold starts
- missed-run risk
- cost
- setup burden
- backup capability
- credible prospective research

Priority order:

1. reliable collection of irreplaceable point-in-time data
2. correctness
3. observability
4. operational simplicity
5. low cost
6. zero cost

Do not choose a weaker system merely to save a small monthly amount.

Create:

`docs/final-hosting-decision.md`

The document must:

- compare the options directly
- state current official limitations
- estimate monthly cost
- choose one primary architecture
- name one cheaper fallback
- explain why the primary was selected

## Default decision rule

Prefer paid Render for operational simplicity and reliable scheduled execution unless current official evidence shows Cloud Run offers materially better reliability and cost without imposing unacceptable setup or maintenance complexity.

Do not describe Northflank Developer Sandbox as production-ready if its own documentation says otherwise.

Do not call delayed best-effort schedules equivalent to a reliable scheduler.

---

# 12. Assess a consolidated orchestrator

Assess whether Arepo can safely consolidate scheduled tasks into one due-task orchestrator.

Potential tasks:

- market and metadata refresh
- price collection
- microstructure collection
- six-hour freeze
- daily freeze
- weekly freeze
- one-hour observations
- six-hour observations
- 24-hour observations
- seven-day observations
- resolutions
- alerts
- stale checks

A consolidated orchestrator is permitted only if it preserves all research semantics.

Required if implemented:

- database advisory lock or equivalent
- one active orchestrator at a time
- actual execution timestamps
- planned due timestamps
- catch-up of missed due work
- no early future observation
- independent task error isolation
- persistent task-run records
- retry state
- idempotency keys
- timeout per task
- failure summary
- non-zero process exit when required
- no silent skipping
- safe manual rerun
- monitoring of overdue tasks

If one orchestrator cannot safely preserve these guarantees, keep separate cron jobs.

Do not consolidate solely to reduce cost.

Add tests for whichever architecture is selected.

---

# 13. Implement the selected deployment configuration

Complete all repository-side deployment work for the chosen primary architecture.

Do not create paid resources or enter user secrets.

## Required deployment assets

Create or update as applicable:

- provider configuration
- `render.yaml`, Dockerfiles or Cloud Run configuration
- migration command
- release/pre-deploy command
- backend build command
- backend start command
- health check
- readiness check
- scheduler commands
- scheduler UTC expressions
- environment-variable declarations
- frontend production API configuration
- deployment verification scripts
- rollback scripts or documented commands
- log and monitoring guidance

Create:

- `docs/FINAL_DEPLOYMENT_PLAN.md`
- `docs/FINAL_ENVIRONMENT_VARIABLES.md`
- `docs/FINAL_SCHEDULED_JOBS.md`
- `docs/FINAL_PRODUCTION_ACCEPTANCE.md`
- `docs/FINAL_ROLLBACK_PLAN.md`
- `docs/FINAL_BACKUP_AND_RETENTION.md`
- `docs/USER_DEPLOYMENT_CHECKLIST.md`

Add scripts where useful:

- `scripts/preflight_deployment.sh`
- `scripts/verify_production.sh`
- `scripts/check_research_health.sh`

Scripts must:

- avoid printing secrets
- return non-zero on failure
- have clear output
- work from documented directories

---

# 14. Production database requirements

The production design must use PostgreSQL, not a local SQLite file.

Verify:

- schema is PostgreSQL-portable
- migrations apply cleanly
- indexes exist for cohort, entry and forward-observation queries
- transactions protect cohort atomicity
- connection configuration is compatible with the selected Supabase connection mode
- secrets stay server-side
- collector jobs connect directly and safely
- migrations do not depend on the web server being awake
- backups are documented
- retention preserves immutable research evidence
- database-size monitoring exists

Do not delete:

- frozen prospective cohorts
- essential frozen entries
- essential forward outcomes
- revisions required for auditability

Raw redundant snapshots may have a documented retention policy only if reproducibility remains intact.

---

# 15. Production operational verification

Run a production-equivalent local dry run of the selected deployment commands.

Prove:

1. migration succeeds
2. API starts
3. health succeeds
4. research status succeeds
5. scheduler command starts without browser activity
6. market collection runs
7. microstructure collection runs
8. six-hour freeze runs
9. daily freeze runs
10. weekly freeze runs
11. forward observation respects causal timing
12. resolution update runs
13. repeated jobs remain idempotent
14. failed jobs are visible
15. incomplete cohorts are not exposed
16. synthetic data is excluded
17. frontend production build uses the configured API base
18. verification script catches intentional misconfiguration

Use test records and controlled clocks where future time is required.

Never insert controlled test records into real performance.

Create:

`docs/final-production-equivalent-dry-run.md`

---

# 16. Exact user deployment handoff

The final report must contain one complete ordered checklist the user can execute without guessing.

Do not merely reference documentation.

For every step state:

- service or page
- exact button/menu
- exact field name
- exact value or source of value
- whether it is secret
- expected result
- common failure
- corrective action

The checklist must cover:

1. verify branch and final commit
2. create pull request
3. merge into `main`
4. create production safety tag
5. create or confirm Supabase project
6. obtain correct PostgreSQL URL
7. configure database password securely
8. run migration or configure release command
9. create backend service
10. enter backend environment variables
11. configure health and readiness checks
12. create every required scheduled job or orchestrator
13. enter every exact UTC schedule
14. configure job secrets
15. run first manual collector sequence
16. verify first real six-hour cohort
17. verify first real daily cohort
18. verify first real weekly cohort
19. verify forward observation
20. verify synthetic exclusion
21. create Vercel frontend
22. set frontend root directory
23. set production API variable
24. deploy frontend
25. connect `arepo.dsheikh.cc`
26. update backend CORS and base URL
27. configure Resend if authentication or alerts require it
28. test sign-up, verification and reset
29. test Signal Lab
30. test Replay research status
31. test market routing
32. test scheduler failure and recovery
33. verify operation with browser closed
34. set monitoring routine
35. configure backup routine
36. define rollback procedure
37. set first 24-hour review
38. set seven-day review
39. set 30-day research review

Do not ask the user to paste secrets into chat.

---

# 17. Track the actual goal

Maintain:

`docs/EDGE_RESEARCH_GOAL.md`

The goal remains:

> Determine whether Arepo's selection and microstructure evidence improves outcomes beyond simple momentum using prospective, immutable, point-in-time evidence after realistic execution costs.

At every milestone verify the work advances:

- prospective collection
- complete cohort freezing
- outcome collection
- baseline comparison
- selection-edge measurement
- ablation
- leakage prevention
- executable performance
- operational reliability

Reject unrelated design work or model retuning.

---

# 18. Independent reviewers

Use independent reviewers for:

## Database and migration

Try to break upgrade, rollback, idempotency and PostgreSQL portability.

## Research provenance

Check no look-ahead and no partial cohort enters evidence.

## UI boundary behaviour

Test popovers, overflow, action controls and accessibility.

## Production architecture

Check every command, schedule, dependency, secret and failure path.

## Operational adversary

Try to produce:

- duplicate cohort
- partial cohort
- missed task
- simultaneous scheduler runs
- early forward observation
- stale status
- hidden collector failure
- migration failure
- secret exposure
- synthetic contamination

## Dayyan acceptance

Use the running product and verify the user can:

- understand the signal
- see the prioritised subset
- inspect Replay status
- trust that collection is automatic
- follow the deployment checklist

Fix all confirmed critical and major findings.

Disclose the actual reviewer structure. Do not claim unavailable Opus subagents.

---

# 19. Completion gate

Do not report completion until:

- migration is implemented and tested
- the existing local database upgrades
- prior rows are preserved
- partial failed cohorts are handled
- six-hour freeze succeeds
- daily freeze succeeds
- weekly freeze succeeds
- repeated freeze is idempotent
- unavailable token behaviour is robust
- all Signal Lab popovers stay in viewport
- horizontal overflow is eliminated
- action controls are clearly spaced
- local acceptance passes
- provider comparison is complete
- one primary hosting path is selected
- provider configuration is implemented
- production-equivalent dry run passes
- exact user deployment checklist exists
- backend tests pass
- frontend tests pass
- Git is clean
- branch is pushed

You are not deploying external paid resources.

You are completing every repository-side action and then giving the user the exact external steps.

---

# 20. Final report

Report:

1. branch
2. final commit
3. push status
4. schema root cause
5. migration approach
6. exact local migration command
7. exact production migration mechanism
8. old-data preservation
9. partial-cohort repair
10. cohort atomicity
11. unavailable-token root cause
12. unavailable-token behaviour
13. tooltip fix
14. horizontal-overflow fix
15. action-spacing fix
16. six-hour freeze result
17. daily freeze result
18. weekly freeze result
19. research-status result
20. backend tests
21. frontend tests
22. local acceptance
23. hosting options compared
24. selected architecture
25. estimated monthly cost
26. cheaper fallback
27. deployment assets created
28. production dry-run result
29. reviewer results
30. exact ordered steps the user must perform next

The final user-facing checklist must be complete and copy-paste ready.

Start now and continue autonomously.
