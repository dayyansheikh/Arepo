# Final production-equivalent dry run (prompt section 15)

Ran the actual deployment commands locally, headless (no browser), against a throwaway database, to
prove the production sequence works before handoff. Controlled fixtures/clocks are used only where
future time is required; no test record enters real performance.

## Sequence and results

| # | Step | Command | Result |
| --- | --- | --- | --- |
| 1 | Migration (release command) | `python -m astrolabe.storage.migrate_cli upgrade` | `from_version 0 → to_version 3` on a fresh DB (all tables created) |
| 2 | Schema check | `migrate_cli check` | `current: true`, version 3 |
| 3 | API starts | `uvicorn astrolabe.api.app:app` | `/health` → 200 |
| 4 | Research status | `GET /api/research/status` | 200; `model_version=arepo-model-1`, `edge_supported=false`, `incomplete_cohorts=0` |
| 5 | 6h freeze (headless) | `research-freeze --cadence 6h` | `frozen:true`, universe 60, excluded 0, degraded false |
| 6 | Daily freeze | `research-freeze --cadence daily` | `frozen:true`, universe 60 |
| 7 | Weekly freeze | `research-freeze --cadence weekly` | `frozen:true`, universe 60 |
| 8 | Full universe + roles persisted | (freeze summary) | public/shadow/observation/abstention recorded; 60 markets each |
| 9 | Repeated 6h freeze (idempotent) | `research-freeze --cadence 6h` | `already_frozen:true` (no duplicate) |
| 10 | Forward observation (causal) | `research-forward` | `invalid_predates_freeze:180` — horizons that predate a mid-period freeze are rejected, NOT backfilled (the causal guard; in production the boundary-aligned cron makes horizons genuinely future) |
| 11 | Resolution update | `astrolabe.evaluation.cli resolve` | runs headless (records any available resolution) |
| 12 | Incomplete-cohort repair | `research-repair` | `removed_incomplete: []`, `frozen_anomalies: []` (clean) |
| 13 | Synthetic excluded | `GET /api/cohorts/latest` | 404 (synthetic never served as real) |
| 14 | Verification script | `scripts/verify_production.sh` | `VERIFY OK` |
| 15 | Misconfiguration caught | `verify_production.sh` with wrong API base | `VERIFY FAIL: health returned 000` (non-zero exit) |

## What this proves

Discover → collect prices/order book/trade flow → signals → rank → freeze (6h/daily/weekly, full
universe, roles) → persist → forward observe (causal) → resolve → research status, all without a
browser and with migrations applied as an explicit step. Repeated jobs are idempotent; failed
observations are visible; incomplete cohorts are not exposed; synthetic data is excluded; and the
verification script catches an intentional misconfiguration.

## What it does not (and cannot) prove locally

The passage of real time: genuine 1h/6h/24h/7d outcomes only accrue after those horizons elapse on
cohorts frozen at the boundary in production. The valid forward-observation code path (as opposed to
the causal-rejection path exercised here mid-period) is proven deterministically by
`tests/unit/test_research_dry_run.py` with a controlled clock.

## Test-record isolation

The dry run used `/tmp/arepo-proddry.db`, deleted after. No row was written to the real database or
to production, and none can enter real performance (status reads only `provenance='prospective'`,
the edge verdict requires the predeclared minimum sample, synthetic is filtered everywhere).
