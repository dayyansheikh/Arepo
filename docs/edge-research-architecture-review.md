# Edge-research architecture review (prompt section 17A / 17C)

Traces the complete path from live Polymarket input to stored prospective evidence and Replay
output, and answers the deployment guarantee. Every stage below is implemented and exercised by the
dry run (`docs/edge-research-end-to-end-dry-run.md`) unless the limitation says otherwise.

## Stage trace

| # | Stage | Module | Table | Job | Idempotency / retry | Failure state |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Market discovery | `service/sources.py` (LiveSource) | (upstream) | freeze crons | read-only; retries via httpx | degrades to fewer markets |
| 2 | Canonical id resolution | `service/market_service.py` | `research_entries.market_id/condition_id/token_id` | freeze | deterministic | market skipped |
| 3 | Price collection | `analytics/*`, `service/enrich.py` | snapshot fields | freeze | best-effort per token | token skipped ("live token data unavailable") |
| 4 | Trade-flow collection | `clients/data_api.py`, `opportunity/service.market_flow_indicators` | frozen `tradeflow_direction` | freeze | try/except, degrades to [] | flow families absent |
| 5 | Order-book collection | `analytics/microstructure.py` | `spread/near_mid_depth`, `orderbook_direction` | freeze | best-effort | book features absent |
| 6 | Wallet/participant evidence | `analytics/flow.py` | evidence families | freeze | best-effort | family absent |
| 7 | Feature calculation | `analytics/anomaly.py`, `enrich.py` | `component_scores`, `component_availability` | freeze | pure | components None (never zero) |
| 8 | Direction assignment | `analytics/zscore.py`, `anomaly.py` | `direction`, `momentum/orderbook/tradeflow_direction` | freeze | deterministic | direction None -> abstention |
| 9 | Confidence | `opportunity/scoring.reliability` | `confidence` | freeze | deterministic | lower confidence |
| 10 | Research Priority | `opportunity/scoring.score_opportunity` | `research_priority` | freeze | deterministic | 0 |
| 11 | Public ranking | `research_engine.build_entry_inputs` | `role`, `rank` | freeze | deterministic | fewer public |
| 12 | Shadow inclusion | `research_engine.build_entry_inputs` | `role=shadow/observation/abstention` | freeze | FULL universe kept | n/a |
| 13 | Cohort creation | `research_repository.get_or_create_cohort` | `research_cohorts` | freeze | get-or-create on (cadence,cutoff) | duplicate refused |
| 14 | Cohort freeze | `research_repository.freeze_cohort` | `research_cohorts.frozen` | freeze | idempotent; frozen guard | re-freeze no-op |
| 15 | Persistence | `research_repository.add_entry` | `research_entries` | freeze | unique (cohort,market,token) | duplicate returns existing |
| 16 | Forward observation | `research_tracking.collect_due_forward` | `research_forward_observations` | research-forward (20 min) | unique (entry,horizon); causal guard | unavailable/invalid recorded |
| 17 | Final resolution | `research_tracking.record_resolution`, `evaluation.tracking` | `market_resolutions` | arepo-resolve (6h) | one row per market; never re-flip | pending |
| 18 | Baseline calc | `research_analysis.baseline_table` | (computed) | status API | pure | inconclusive on small n |
| 19 | Feature ablation | `research_analysis.ablation_table` | (computed) | status API | pure/deterministic | inconclusive |
| 20 | Walk-forward assignment | `research_walk_forward` + `research_entries.walk_forward_partition` | `research_entries` | freeze | immutable per entry | live default |
| 21 | Execution-cost calc | `execution.evaluate_execution` | (computed) | status API | pure | unavailable if depth missing |
| 22 | Research-status API | `research_service.ResearchReadService` | reads all | web service | read-only | honest empty state |
| 23 | Replay display | `frontend/app/replay/page.tsx` (`ResearchStatusSection`) | via API | web (frontend) | n/a | "no evidence yet" |
| 24 | Monitoring / recovery | `research_service.status`, `research_tracking.pending_forward_backlog` | reads | status API | n/a | backlog/last-run surfaced |

## Risk checklist (prompt section 17A) — findings and resolutions

- **Mutable historical state**: resolved. Frozen cohorts/entries are immutable (`CohortFrozenError`);
  corrections go to `research_revisions`, never in place.
- **Race conditions / duplicate cohorts / duplicate observations / duplicate resolutions**: resolved
  by unique constraints `(cadence,cutoff)`, `(cohort,market,token)`, `(entry,horizon)`, and the
  one-row-per-market resolution upsert.
- **Jobs that run in the wrong order**: freeze -> forward -> resolve are independent and idempotent;
  forward only acts on already-frozen cohorts; resolve is order-independent. No step silently blocks
  later steps.
- **Jobs relying on browser activity**: none. All work is CLI crons.
- **Look-ahead / mutable cut-off**: the forward collector refuses any horizon that predates the
  freeze (causal guard, proven in the dry run), and frozen entries are never rewritten.
- **SQLite assumptions on PostgreSQL**: only portable column types are used (String/Integer/Float/
  Boolean/JSON/DateTime(timezone=True)); `_utc()` reattaches UTC for SQLite naive datetimes. No
  SQLite-only SQL. Bootstrap uses `create_all` (safe on both).
- **Transaction-pooler / prepared-statement issues**: the app already runs asyncpg against the
  Supabase pooler in `docs/deployment.md`; the research tables add no server-side prepared-statement
  dependency (plain CRUD).
- **Secrets exposed to the frontend**: none; the frontend calls only public read routes.
- **Frontend depends on unavailable routes**: `ResearchStatusSection` returns null until the API
  responds; the route is registered in `app.py`.
- **Silent collector failures**: `_safe_quote` swallows per-token feed errors but records an
  `unavailable_reason`; the status API surfaces `collector_recent`, last freeze and backlog.
- **Unbounded API calls / rate limits**: freeze scans a bounded universe (limit 60); forward calls
  `market_detail` once per due (entry,horizon). This scales with accumulated cohorts and is the main
  operational cost to watch (see monitoring). Limitation noted below.

## Known limitations (not blockers)

- **Forward-collection cost grows with cohorts**: at 20-minute cadence, each due (entry,horizon)
  calls `market_detail`. As cohorts accumulate this is the dominant upstream load; batching by market
  is a future optimisation. Monitored via `pending_forward_backlog`.
- **Per-family directions are model-limited**: `momentum_direction` is the z-score sign, so momentum,
  price-only and Arepo share a direction by construction. This is the honest scientific state the
  ablation is designed to expose, not a defect.
- **No probability head yet**: calibration/Brier/log-loss stay guarded until a genuine probability
  forecast or a validated confidence->frequency mapping exists.

## Deployment guarantee

> Once the user completes the deployment steps, will Arepo begin collecting real prospective
> evidence automatically without any browser being open?

**Yes, verified** — for the collection mechanism, subject to the user completing the external setup
(Postgres URL, Render service, the four research crons enabled). Proven by: the CLI freeze/forward/
status commands run headless against a real upstream (dry run B); the crons are defined in
`render.yaml` with boundary-aligned schedules that keep horizons causal; idempotency, immutability
and the causal guard are covered by tests; and the schema is Postgres-portable. What cannot be
verified locally is the passage of real time: genuine 1h/6h/24h/7d outcomes only accrue after those
horizons elapse on cohorts frozen at the boundary in production.
