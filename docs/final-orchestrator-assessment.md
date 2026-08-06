# Consolidated-orchestrator assessment (prompt section 12)

## Question

Can Arepo safely consolidate its scheduled tasks (market refresh, price + microstructure
collection, 6h/daily/weekly freeze, 1h/6h/24h/7d observations, resolutions, alerts, stale checks)
into ONE due-task orchestrator cron, instead of ~11 separate Render cron jobs?

## Requirements a single orchestrator would have to preserve

Advisory lock (one active orchestrator at a time), actual + planned timestamps, catch-up of missed
due work, no early future observation, independent per-task error isolation, persistent task-run
records, retry state, idempotency keys, per-task timeout, a failure summary, non-zero process exit
when a task fails, no silent skipping, safe manual rerun, and overdue-task monitoring.

## Assessment

The **separate-cron** architecture already provides most of these for free, with better isolation:

- **Failure isolation**: each task is its own Render cron with its own logs, exit status, history
  and one-click manual rerun. A failing forward-observation run cannot affect the weekly freeze.
- **Idempotency**: freeze is idempotent on `(cadence, cutoff)`; forward observations on
  `(entry, horizon)`; resolutions are one-row-per-market. Re-runs are safe by construction.
- **No early observation / catch-up**: the forward collector is due-driven — it records any horizon
  that has elapsed and refuses any that predates the freeze — so a missed 20-minute run is simply
  caught up by the next run. No orchestrator-level catch-up logic is needed.
- **Scheduling**: Render Cron Jobs run at the scheduled UTC minute; there is no shared-process
  contention to coordinate, so no advisory lock is required (each cron is a separate process that
  starts and exits).

A single orchestrator would ADD: a database advisory lock, a task-run table, per-task timeout and
retry-state machinery, and a dispatcher — i.e. more moving parts and a single point of failure,
for the sole benefit of fewer cron entries. The prompt is explicit: *do not consolidate solely to
reduce cost*, and *if one orchestrator cannot safely preserve these guarantees, keep separate cron
jobs*.

## Decision

**Keep separate Render cron jobs** (primary architecture). They already satisfy every guarantee with
strictly better failure isolation and observability, and they are simpler to operate and reason
about. The consolidated orchestrator is documented as the *cheaper fallback* only; it is **not
implemented** because it would trade reliability and isolation for a marginal cron-count reduction,
which the priority order (reliability first) rejects.

If a future constraint (e.g. a hard cap on the number of cron jobs) forces consolidation, the
orchestrator MUST be built with all the guarantees listed above (advisory lock, task-run records,
catch-up, isolation, non-zero exit on failure) before it replaces the separate crons.
