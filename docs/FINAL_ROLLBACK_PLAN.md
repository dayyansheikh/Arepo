# Final rollback plan

The edge-research change is **additive** (new tables, new nullable columns, new crons). Rolling back
application code never requires a schema rollback: older code simply ignores the extra columns, and
no data is lost.

## Stop collection immediately (no code change)

Pause the four `arepo-research-*` cron jobs in the Render dashboard. Collection stops; every frozen
cohort and observation is immutable and untouched. Resume by un-pausing.

## Roll back the API

1. In Render → the web service → "Manual Deploy" → pick the previous successful deploy, or
   `git revert`/redeploy the prior commit.
2. Do **not** drop or alter research tables/columns. The additive schema is forward-compatible with
   older code.
3. If you must revert the whole branch locally: `git reset --hard arepo-before-final-predeployment-launch-readiness`
   (never delete that tag) and redeploy. Leave the production schema as-is.

## Database

- Never hand-drop `research_cohorts`, `research_entries`, `research_forward_observations` or
  `research_revisions`, or any frozen prospective evidence. These are the irreplaceable record.
- The migrator only ever ADDs; there is no destructive migration to reverse.
- If a bad row is written, use `research-repair` (removes only never-frozen incomplete cohorts) or a
  manual, audited SQL fix plus a `research_revisions` entry — never a silent mutation of frozen data.

## Frontend

Vercel keeps every deployment; use "Instant Rollback" to the previous build. The frontend is
read-only against the API, so a rollback has no data effect.

## Verification after rollback

Run `API_BASE=<url> scripts/verify_production.sh` — expect health 200, research status 200,
`incomplete_cohorts=0`.
