# Final backup and retention

## What must never be lost (immutable research evidence)

- `research_cohorts` (frozen cohorts)
- `research_entries` (the frozen screened universe with all cut-off fields)
- `research_forward_observations` (outcomes)
- `market_resolutions` (final resolutions)
- `research_revisions` (audit corrections)

These are point-in-time and irreplaceable: a lost row cannot be recomputed. They have **no deletion
policy**. Retain them for the life of the research programme.

## Backups

- **Supabase** takes automated daily backups on paid plans; on the free plan, enable Point-in-Time
  Recovery when the project graduates to Pro, or take a manual logical dump on a schedule:
  `pg_dump "$DIRECT_DATABASE_URL" -Fc -f arepo-$(date +%F).dump` (use the DIRECT 5432 URL for
  `pg_dump`, not the pooler). Store dumps off-Supabase (e.g. object storage) weekly.
- Verify a restore quarterly into a scratch database and run `migrate_cli check`.

## Retention policy for reproducible-but-redundant data

Only raw, redundant snapshots may be pruned, and only if reproducibility remains intact:

- `microstructure_snapshots`: high-volume 5-minute rows used to build component availability. These
  may be pruned after **90 days** IF no frozen cohort still needs them for reproducibility. Because
  each frozen entry already stores its own component values at the cut-off, pruning old raw
  snapshots does not affect any frozen cohort. Document any prune run.
- Never prune snapshots newer than the oldest unresolved cohort's needs.

## Database-size monitoring

- Watch Supabase's database size in the dashboard; alert at 70% of the plan's limit.
- `scripts/check_research_health.sh` reports cohort counts; a monthly growth review decides when to
  upgrade the Supabase plan (row growth is dominated by `research_entries` ≈ 60 markets × ~9 freezes
  per day, plus forward observations).

## Do not delete

Frozen prospective cohorts, essential frozen entries, essential forward outcomes, and revisions
required for auditability — under any retention rule.
