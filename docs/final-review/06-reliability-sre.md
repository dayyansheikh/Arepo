# Agent 6 — SRE / reliability

**Overall verdict: robust enough to run unattended on the free stack, with two operational caveats the
owner must know.** Idempotency, leasing and causal-delay handling are correctly implemented; the real
risks are external (free-tier behaviours), not logic bugs.

## Strongest aspects (evidence)
- **Idempotent single tick** (`scheduler/tick.run_tick`): work gated on elapsed time + causal boundaries,
  not a clock. Duplicate tick → DB lease loser exits 0 (`scheduler/state.acquire_lease`, atomic
  conditional `UPDATE … WHERE held_until < now`, verified for SQLite + Postgres). Late/missed tick → next
  wake catches up; a period with no in-window complete scan is left honestly unfrozen.
- **No partial cohort:** refresh writes a complete scan atomically; `cohort_from_scan` refuses incomplete
  scans; freeze idempotent on `(cadence, cutoff)`. Observations idempotent (get-or-create per
  entry×horizon).
- **Health:** `/admin/health` + `tick status` expose latest complete scan + age, per-job last-run,
  latest cohort with scheduled-vs-actual timing, storage size + level (ok/warn/crit). `db_healthy:false`
  distinguishes a DB outage from a cold start.
- **Backups:** daily `pg_dump | gzip`, `gzip -t` integrity check, size sanity, GitHub artifact; restore
  documented in PRODUCTION_ROLLBACK.md.

## Findings
| Sev | Finding | Evidence | Fix |
|--|--|--|--|
| **Medium** | **Supabase Free pauses after 7 idle days.** If the scheduler is disabled >7d (or Actions is off), the project pauses and the API errors until manual resume. | capacity audit §5 | Documented; the every-~10-min tick keeps it alive in normal operation. Add to health/runbook a note; consider a lightweight keep-alive ping in the tick (already implied by DB writes). |
| **Medium** | **GitHub cron jitter (5–30 min)** means "~10-min refresh" is a *target*; latest-complete-scan age can spike. | .github/workflows/scheduler.yml | The public UI shows actual latest-complete-update time (staging showed "updated 34 hours ago / Out of date"), so freshness is never overstated. Acceptable; owner should expect drift. |
| **Medium** | **Public repo required** for free unlimited Actions minutes; private = 2,000 min/mo, insufficient (~576 min/day at 10-min). | audit §5 | Documented in deploy guide; owner decision. |
| Low | In-memory auth rate-limiter resets on Render cold start; single-instance so effect is minor. | `accounts/ratelimit.py` | Acceptable on Render Free (1 instance). |
| Low | First tick's complete scan (~5 min) approaches the 20-min job timeout only under severe upstream slowness. | scheduler.yml `timeout-minutes: 20` | Bound is generous; fine. |

## Most likely way Arepo silently dies
**The scheduler stops running and nobody notices** (Actions disabled, secret rotated/expired, or repo
made private → minutes exhausted). Mitigation: the UI already shows "Out of date / updated N ago"
honestly, and `/admin/health` shows `latest_complete_scan_age_seconds`; recommend the owner check
`/admin/health` weekly (or wire a simple external uptime ping). This is the one thing to watch.

## Can it run without Dayyan's laptop?
Yes — all compute is Render (API) + GitHub Actions (scheduler/backup) + Supabase (state). The laptop is
only needed for the one-time migration import.

**Conclusion: ship-with-fixes** (document the 7-day pause + jitter clearly for the owner; keep-alive is
inherent). No logic-level reliability defects found.
