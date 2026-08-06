# Final scheduled jobs

All jobs are Render Cron Jobs, all UTC, all idempotent, all headless (no browser). They share the
web service's environment group. Defined in `render.yaml`. Set a 10-minute timeout on each.

## Edge-research pipeline (the jobs that build irreplaceable evidence)

| Job | Command | UTC schedule | Runtime | Idempotency key | Success condition | Alert if |
| --- | --- | --- | --- | --- | --- | --- |
| Microstructure snapshots | `python -m astrolabe.ingest.microstructure_cli collect --mode live` | `*/5 * * * *` | seconds | (market,token,ts) | rows inserted | no run in 30 min |
| Research freeze 6h | `python -m astrolabe.evaluation.research_cli research-freeze --cadence 6h` | `5 0,6,12,18 * * *` | 1–3 min | (6h, cutoff) | JSON `frozen:true` | `rejected:true` or no run in 7h |
| Research freeze daily | `... research-freeze --cadence daily` | `10 0 * * *` | 1–3 min | (daily, cutoff) | `frozen:true` | rejected / missed |
| Research freeze weekly | `... research-freeze --cadence weekly` | `15 0 * * 1` | 1–3 min | (weekly, cutoff) | `frozen:true` | rejected / missed |
| Research forward observations | `python -m astrolabe.evaluation.research_cli research-forward` | `*/20 * * * *` | secs–min | (entry, horizon) | JSON `written>=0` | growing backlog |
| Resolutions | `python -m astrolabe.evaluation.cli resolve --mode live` | `15 */6 * * *` | seconds | one row / market | recorded | repeated errors |

The forward collector is due-driven: it records any horizon that has elapsed since the freeze and
refuses any that predates it, so a missed 20-minute run is simply caught up next time. Freeze jobs
fire a few minutes AFTER each cadence boundary so `frozen_at ≈ cut-off` and every horizon is in the
future.

## Supporting jobs

| Job | Command | UTC schedule | Purpose |
| --- | --- | --- | --- |
| Opportunity snapshot | `python -m astrolabe.opportunity.cli snapshot --mode live` | `10 0 * * *` | daily immutable Opportunity board snapshot |
| (Legacy) weekly cohort rank | `python -m astrolabe.evaluation.cli rank --mode live` | `0 * * * *` | pre-research weekly cohort (retained, harmless) |
| (Legacy) weekly cohort freeze | `python -m astrolabe.evaluation.cli freeze` | `59 23 * * 0` | pre-research weekly cohort |
| (Legacy) forward prices | `python -m astrolabe.evaluation.cli forward` | `30 * * * *` | pre-research forward prices |
| Alerts | `python -m astrolabe.alerts.cli user-dry-run --mode live` | `20 * * * *` | per-user alerts (no-op unless enabled) |

## Manual rerun

Any job can be re-run from the Render dashboard (Cron Job → "Run now") or a shell:
`python -m astrolabe.evaluation.research_cli <command>`. Re-runs are safe (idempotent).

## Repair

`python -m astrolabe.evaluation.research_cli research-repair` removes any never-frozen incomplete
cohort (there should be none) and reports frozen anomalies without deleting evidence.

## Expected cron count

**11** total (6 research-pipeline + 5 supporting). If a hard cap forces fewer, see
`docs/final-orchestrator-assessment.md` (separate crons are the chosen design).
