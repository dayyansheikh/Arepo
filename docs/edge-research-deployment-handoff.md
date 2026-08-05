# Edge-research deployment and activation handoff (prompt section 17E)

Everything needed to start continuous, browser-free collection of real prospective evidence. Nothing
here has been run against paid or production services; those steps are yours to perform. Do not paste
secrets into chat; set them in the provider dashboards.

## 0. Confirm the branch and commit

- Branch: `arepo-edge-research-infrastructure`. Confirm `git log -1` is the latest edge-research
  commit and `git status` is clean. Backend 338 tests pass, ruff clean; frontend tsc/lint clean,
  21 vitest, build 16/16.

## 1. Merge to main and tag

1. Open a PR from `arepo-edge-research-infrastructure` into `main`; review the diff (all additive).
2. Merge. Then create a production safety tag: `git tag arepo-edge-research-live && git push --tags`.

## 2. Database (Supabase Postgres)

- Create a Supabase project. Use the **transaction pooler** connection string (port 6543) as
  `DATABASE_URL`, in the async form: `postgresql+asyncpg://USER:PASSWORD@HOST:6543/postgres`.
- Migrations: the app bootstraps its own schema via `create_all` on startup and every CLI run
  (`astrolabe.evaluation.migrations.bootstrap` imports the research models). No Alembic step needed.
  To pre-create explicitly, run once: `python -m astrolabe.evaluation.research_cli research-bootstrap`.
- Secret: `DATABASE_URL` (yes, secret). Expected: tables `research_cohorts`, `research_entries`,
  `research_forward_observations`, `research_revisions` plus the existing ones exist after first run.

## 3. Backend web service (Render) — from `render.yaml`

- Service `arepo-api`, rootDir `backend`, start `uvicorn astrolabe.api.app:app --host 0.0.0.0 --port $PORT`, health `/health`.
- Environment variables (set in the Render dashboard; secrets marked):
  - `DATABASE_URL` (secret), `AUTH_SECRET` (secret, >=32 bytes), `CORS_ORIGINS` (your Vercel URL),
    `APP_BASE_URL`, `ENVIRONMENT=production`, `LOG_JSON=true`, `DEFAULT_MODE=live`,
    `AUTH_COOKIE_SECURE=true`. Email vars only if alerts are enabled.

## 4. Scheduled jobs (Render crons — all in `render.yaml`, all idempotent, all UTC)

| Job | Command | UTC schedule | Expected runtime |
| --- | --- | --- | --- |
| Microstructure snapshots | `python -m astrolabe.ingest.microstructure_cli collect --mode live` | `*/5 * * * *` | seconds |
| Research freeze 6h | `python -m astrolabe.evaluation.research_cli research-freeze --cadence 6h` | `5 0,6,12,18 * * *` | ~1-3 min |
| Research freeze daily | `... research-freeze --cadence daily` | `10 0 * * *` | ~1-3 min |
| Research freeze weekly | `... research-freeze --cadence weekly` | `15 0 * * 1` | ~1-3 min |
| Research forward | `... research-freeze` → `... research-forward` | `*/20 * * * *` | seconds-min (grows) |
| Resolutions | `python -m astrolabe.evaluation.cli resolve --mode live` | `15 */6 * * *` | seconds |

Idempotency keys: freeze `(cadence, cut-off)`; forward `(entry, horizon)`; resolution one row per
market. Re-running any job is safe. Timeout: set 10 min per cron.

## 5. First manual run order (in the Render shell or locally against the prod DB)

Run in THIS order, at or just after a 6-hour boundary so horizons stay causal:

1. `research-bootstrap` — expect "Research tables ready."
2. `research-freeze --cadence 6h` — expect JSON with `frozen: true`, `universe_size` ~40-80.
3. `research-freeze --cadence daily` and `--cadence weekly` — same shape.
4. `research-status` — expect 3 cadences counted, `edge_supported: false`,
   "not yet accumulated enough prospective evidence".
5. Wait ~1 hour, then `research-forward` — expect `written > 0` (the 1h horizon now elapsed) and
   `invalid_predates_freeze: 0` (because you froze at the boundary).

## 6. First production acceptance test

- `GET /health` → 200. `GET /api/research/status` → 200 with real counts and `edge_supported:false`.
- Open the Replay page → "Edge-research status" shows the amber "not enough evidence yet" banner and
  real cohort counts. `GET /api/cohorts/latest` → 404 (no real weekly cohort yet; synthetic excluded).

## 7. Monitoring

- `GET /api/research/status`: `collector_recent`, `last_successful_freeze`, per-horizon
  `evaluable`/`pending`, `resolved_markets`.
- Watch for: `collector_recent:false` (snapshots stalled), a freeze returning `universe_size:0`
  (upstream discovery failing), or a growing forward backlog. Render cron logs show each run's JSON.
- Alert conditions: no successful freeze in >7 h; forward `written:0` with a large due backlog;
  repeated `unavailable` on the same markets (upstream rate-limit).

## 8. Rollback

- The change is additive. To disable: pause the four `arepo-research-*` crons in Render (collection
  stops; existing frozen cohorts are untouched and immutable). To fully revert code:
  `git reset --hard arepo-before-edge-research-infrastructure` (never delete that tag) and redeploy.
  Frozen research rows can be left in place; nothing reads them into headline product performance.

## What to expect over time

- **First 24 hours**: 4 six-hour cohorts + 1 daily cohort frozen; 1h/6h/24h forward observations
  begin appearing; `evaluable` at 1h/6h rises; no edge verdict (sample tiny). Resolutions rare.
- **First 7 days**: ~28 six-hour + 7 daily + 1 weekly cohorts; 24h outcomes for the first day's
  cohorts complete; 7d outcomes for the earliest cohorts begin; baselines/ablation tables populate
  but remain labelled inconclusive.
- **First 30 days**: ~120 six-hour + 30 daily + ~4 weekly cohorts; hundreds to thousands of frozen
  directional entries with 1h/6h/24h/7d outcomes; the 24h evaluable sample likely crosses the
  `MIN_PROSPECTIVE_SAMPLE` (100) so the FIRST real edge assessment and the first ablation/walk-forward
  reads become meaningful. Calibration still needs ~200 resolved markets, which depends on how many
  frozen markets actually resolve in the window.

## Evidence threshold before any edge assessment

- Repricing edge: at least `MIN_PROSPECTIVE_SAMPLE = 100` evaluable 24h directional outcomes in a
  single walk-forward window, ALL ten criteria met (positive after costs, interval above 0.5, beats
  momentum + price-only + current-implied, stable across windows, ablation adds value beyond
  momentum, thresholds unchanged, adversarial passed). Until then: inconclusive.
- Calibration / Brier / log loss: at least `MIN_CALIBRATION_SAMPLE = 200` resolved predictions AND a
  genuine probability forecast (not yet built). Until then: "Calibration unavailable".

## Next research decision (deterministic)

- **Arepo beats momentum** (higher hit rate AND positive executable move, both intervals excluding
  the tie, across >=2 walk-forward windows): promote the directional model; begin building a
  probability head to unlock calibration.
- **Arepo matches momentum** (ablation shows non-price families add no value): keep the cheaper
  momentum baseline as the product signal; stop claiming the extra families help; investigate
  specific categories/horizons where a difference appears.
- **Arepo underperforms momentum**: treat the composite direction as momentum-plus-noise; redesign
  the direction rule (it is currently just the z-score sign) before any further edge claim.
- **Only one evidence family adds value** (e.g. order book at 1h only): scope the product claim to
  that family and horizon; do not generalise.
- **Executable performance negative despite positive midpoint** (costs exceed the edge): report no
  practical edge regardless of hit rate; revisit only if larger moves or thinner-cost markets appear.
