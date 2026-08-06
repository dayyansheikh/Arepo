# Predeployment architecture + provenance review

Independent review of `arepo-final-predeployment-launch-readiness` against render.yaml, the FINAL_*
docs, the deployment/health scripts, and the research freeze/forward/status code path.

## Verified correct (no finding needed)

- Every cron `command:` in `render.yaml` matches a real CLI subcommand: `research_cli
  research-freeze --cadence {6h,daily,weekly}` (research_cli.py:108-110), `research-forward`
  (:111), `microstructure_cli collect` (microstructure_cli.py:44), `opportunity.cli snapshot`
  (opportunity/cli.py:64), `evaluation.cli {rank,freeze,forward,resolve}` (evaluation/cli.py:100),
  `alerts.cli user-dry-run` (alerts/cli.py:91). No typo, no nonexistent command.
- Freeze schedules fire minutes after each cadence boundary (6h at :05, daily at 00:10, weekly Mon
  00:15) and `cadence_cutoff()` (research_engine.py:46-57) snaps down to the boundary, so
  `cutoff_at < frozen_at` always — every horizon target is genuinely future. The forward causal
  guard (research_tracking.py:73-88) independently rejects (never backfills) any horizon whose
  target predates `frozen_at`, confirmed by the dry run (`invalid_predates_freeze:180`, doc line 20).
- `research-forward` every 20 min comfortably serves the 1h horizon (tolerance window 900s).
- `preDeployCommand: migrate_cli upgrade` runs as a Render release-phase step, independent of the web
  process; jobs also self-migrate via `bootstrap()` → `auto_migrate` setting (migrations.py:20-34),
  gated correctly by `AUTO_MIGRATE`; `migrate_cli check` passes locally (`current: true`, v3).
- `config.py` env vars all documented in FINAL_ENVIRONMENT_VARIABLES.md; `ALERT_*`/`RESEND_API_KEY`
  live in a separate `alerts/config.py` (also fully documented) — no orphaned or undocumented var.
  Only `NEXT_PUBLIC_API_BASE` is exposed to the frontend; it is non-secret (a public API URL).
- `/api/research/status` and `/api/research/horizon` read only `provenance='prospective'` +
  `frozen=True` cohorts, filtered further to `is_reportable()` partitions (live/heldout) for any
  performance number (research_service.py:61-70, research_walk_forward.py:83-85).
- `/api/cohorts/latest` explicitly excludes `provenance_class == "synthetic"` and 404s honestly when
  no real cohort exists (cohorts.py:31-52).
- A rejected freeze (`usable < 5` or `exclusion_rate > 60%`) returns before any cohort row is created
  — `freeze_from_inputs` short-circuits on `decision.freeze == False` (research_engine.py:279-289);
  a merely *degraded* freeze (exclusion 20–60%) still creates and freezes a cohort, correctly
  distinct from rejection.
- Freeze is atomic (entries + freeze in one transaction, explicit rollback on error,
  research_engine.py:313-328) and immutable (`CohortFrozenError` on re-add or provenance mutation
  after freeze).
- Scripts (`preflight_deployment.sh`, `verify_production.sh`, `check_research_health.sh`) all use
  `set -euo pipefail`, an explicit `fail()` that exits non-zero, and never `echo`/print raw secret
  values (only booleans/counts/model_version).
- The hosting decision honestly rejects GitHub Actions cron ("best-effort... not acceptable for
  irreplaceable data") and Northflank sandbox ("not production per Northflank's own docs"), and
  correctly does not overstate Render Cron's reliability beyond "runs at the scheduled UTC minute.”

## Findings

1. LOW | `docs/FINAL_SCHEDULED_JOBS.md:14` | The "Research forward observations" row lists Command
   as `... research-freeze` → `... research-forward`, implying the forward cron also runs a freeze.
   The actual `render.yaml` (`arepo-research-forward`, line 129) runs only `research-forward`,
   which is correct — the doc row is stray/copy-pasted from the freeze rows above it. No functional
   bug, but a reader following the doc instead of render.yaml would misconfigure a manual rerun.
   Fix: correct the Command cell to `python -m astrolabe.evaluation.research_cli research-forward`.

2. INFO | `render.yaml:94-99`, `evaluation/cli.py` | The alerts cron and the two "legacy" weekly
   cohort crons (`rank`, `freeze` at cli.py) are retained alongside the new research pipeline,
   bringing the total to 11 crons as documented. Confirmed harmless (separate tables, `/api/cohorts`
   already excludes synthetic) — flagged only so a future cost-trim doesn't mistake them for
   research-critical.

No other typo, nonexistent command, look-ahead path, or partial-cohort exposure was found.

## Bottom line

Once the user completes the external steps (Supabase project + pooler URL, Render blueprint deploy,
env group, Vercel deploy + domain), Arepo will collect real prospective evidence automatically,
headless, with no browser: migrations apply as an explicit release step before traffic/crons run,
all 11 cron commands and UTC schedules are correct and causally safe (freezes always precede their
horizons; the forward collector cannot observe early or backfill), secrets are never exposed to the
frontend, and the API surfaces only prospective, non-synthetic, reportable-partition evidence. The
one doc inconsistency (finding 1) is cosmetic and does not affect the deployed system.
