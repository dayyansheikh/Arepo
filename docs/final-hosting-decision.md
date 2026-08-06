# Final hosting decision

## What Arepo actually needs

The overriding requirement is **reliable, scheduled collection of irreplaceable point-in-time
evidence**: a 6h/daily/weekly cohort freeze and forward observations that must run at (or very close
to) fixed UTC times, headless, forever. A missed or badly delayed run is not recoverable later,
because the market state at that moment is gone. Priority order (from the prompt): (1) reliable
collection, (2) correctness, (3) observability, (4) operational simplicity, (5) low cost, (6) zero
cost. Also required: persistent PostgreSQL, direct DB access from jobs, retries, idempotency, manual
reruns, job history/logs, secrets, a custom domain, and low missed-run risk.

## Options compared

| Option | Scheduler reliability | Persistent Postgres | Setup burden | Cold start | Est. monthly | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **1. Render web + Render Cron Jobs (paid)** | Managed cron, runs at the scheduled UTC minute; per-run logs + manual rerun | Render Postgres or external Supabase | Low (one `render.yaml`) | Web can sleep on free; **paid Starter stays warm** | ~$7 web + ~$7 Postgres (or Supabase free/paid) + crons metered small | **PRIMARY** |
| 2. Render web + one consolidated orchestrator cron | Same scheduler; one cron runs a due-task orchestrator | same | Low, but the orchestrator must preserve all semantics (see §12) | same | slightly less | **FALLBACK** (cheaper) |
| 3. Cloud Run service + Cloud Run Jobs + Cloud Scheduler | Cloud Scheduler is highly reliable; Jobs give isolated runs | Cloud SQL or Supabase | **High**: Artifact Registry, IAM, Scheduler, Jobs, VPC/connector for Cloud SQL | Configurable min-instances | Pay-per-use; can be low but Cloud SQL adds ~$8-10+ | Strong but materially more setup/maintenance |
| 4. Render Free web + GitHub Actions cron | **Best-effort only**: GitHub's own docs say scheduled workflows may be delayed or dropped under load | external | Low | Free web sleeps (cold starts, missed collection) | $0 | **Rejected** for the collection role: delayed/dropped schedules are not acceptable for irreplaceable data |
| 5. Northflank Developer Sandbox | Sandbox tier; its own docs describe it as non-production | included | Medium | n/a | $0 | **Rejected**: not production per Northflank's documentation |
| 6. Koyeb free | Free tier limits; scheduled jobs constrained | limited | Medium | sleeps | $0 | Rejected for the collection role (free-tier limits + sleep) |

Current official limitations that drove the call:
- GitHub Actions scheduled workflows are explicitly best-effort and can be delayed or skipped; the
  prompt forbids treating that as a reliable scheduler for irreplaceable data.
- Render Free web services sleep after inactivity, causing cold starts; the collection jobs are
  separate cron jobs, but relying on a sleeping free web tier for a research product is a false
  economy. The paid Starter web service stays warm.
- Cloud Run + Cloud Scheduler is genuinely reliable, but Cloud SQL + connector + IAM + Artifact
  Registry is materially more setup and ongoing maintenance for no reliability gain over Render's
  managed cron at this scale.

## Decision

**Primary architecture: paid Render** — a Starter web service for the FastAPI API plus **Render Cron
Jobs** for each scheduled task, with **Supabase PostgreSQL** (transaction pooler) as the database and
**Vercel** for the frontend. This follows the prompt's default rule (prefer paid Render for
operational simplicity and reliable scheduled execution) because Cloud Run does not offer materially
better reliability at this scale and imposes materially more setup.

**Cheaper fallback: Render web + a single consolidated orchestrator cron** (one Render cron running a
due-task orchestrator instead of ~11 separate crons), retained only if it preserves every research
semantic (assessed in `docs/final-orchestrator-assessment.md`). This reduces cron count/cost without
changing the reliability guarantee.

**Estimated monthly cost (primary):** roughly **$7 (Render web Starter) + $0–$25 (Supabase: free tier
is workable initially; Pro is ~$25 if the row volume or backups warrant it) + small metered Render
cron usage**, i.e. **about $7–$35/month**. The frontend on Vercel Hobby is $0.

Database choice within the primary: **Supabase** (rather than Render Postgres) because it is already
wired throughout the repo (asyncpg + transaction pooler, `docs/deployment.md`), gives a generous free
tier to start, and provides backups. Render Postgres is an acceptable substitute if preferred; the
schema and migrator are portable to either.
