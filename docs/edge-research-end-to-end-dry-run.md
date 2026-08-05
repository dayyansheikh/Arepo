# Edge-research production-equivalent dry run (prompt section 17B)

Purpose: prove the whole pipeline works end to end WITHOUT a browser, and prove the causal guards,
before deployment. It does **not** create real prospective evidence. Two runs are recorded: a
deterministic in-memory run (in CI) and a live run against real Polymarket (throwaway DB).

## A. Deterministic end-to-end run (CI, `tests/unit/test_research_dry_run.py`)

One test chains the full sequence with a controlled clock and fixture feed, so it is repeatable and
proves the VALID forward path (which the live run cannot, because 24h has not elapsed):

| Stage | Proven by |
| --- | --- |
| 1-9 freeze 6h + daily + weekly of the full universe | `freeze_from_inputs` x3; `universe_size==5`, roles asserted |
| 10-11 full universe + public/shadow/observation/abstention roles persisted | role counts asserted |
| 12-15 collect 1h/6h/24h outcomes (controlled clock, fixture feed; 7d not yet due) | `collect_due_forward(now=cutoff+25h)`; 7d coverage == 0 |
| 16 final resolution recorded (fixture) | `record_resolution`; `resolved_markets == 1` |
| 17-18 midpoint + executable results | `full_arepo.mean_executable_move is not None` |
| 19 baselines on the same observations | `baseline_table`; 10 baselines; Arepo/momentum agreement == 1.0 |
| 20 ablation | `ablation_table`; `without_momentum` present |
| 21 walk-forward partitions | entries carry `walk_forward_partition="live"`; `test_research_analysis` |
| 22 research status | `status()`; cadence counts, roles, coverage, edge verdict |
| 23 Replay display of the cohort | `ResearchStatusSection` renders `/api/research/status` |

Result: **passes**. Edge verdict stays NOT supported (sample far below the predeclared minimum),
which is the correct honest outcome. Test rows are in-memory only and never touch a real database.

## B. Live run against real Polymarket (throwaway SQLite DB)

Commands run (throwaway `dryrun2.db`, deleted after):

```
python -m astrolabe.evaluation.research_cli research-freeze --cadence 6h
python -m astrolabe.evaluation.research_cli research-freeze --cadence daily
python -m astrolabe.evaluation.research_cli research-freeze --cadence weekly
python -m astrolabe.evaluation.research_cli research-forward
python -m astrolabe.evaluation.research_cli research-status
# then served via uvicorn: GET /api/research/status, /api/research/horizon/24h
```

Observed output:

| Job | Result |
| --- | --- |
| research-freeze --cadence 6h | `universe_size=60, directional=12, public=10, shadow=2, observation=10, abstention=38`, frozen |
| research-freeze --cadence daily | `universe_size=60, directional=13, public=10, shadow=3, observation=10, abstention=37`, frozen |
| research-freeze --cadence weekly | `universe_size=60, directional=13, public=10, shadow=3, observation=10, abstention=37`, frozen |
| re-run research-freeze --cadence 6h | `already_frozen: true` (idempotent, no duplicate) |
| research-forward | `written=0, unavailable=0, invalid_predates_freeze=300, already_present=0` |
| research-status | 3 cadences x1; `total_frozen_markets=180`; edge **not supported**; `meets_minimum_sample=false` |
| GET /api/research/status | HTTP 200; cadences `{6h:1, daily:1, weekly:1}`; `edge_supported=false` |
| GET /api/research/horizon/24h | HTTP 200; `evaluable=0`, 10 baselines, 9 ablation variants |

### Why `invalid_predates_freeze=300` here (and not in production)

The dry run froze all three cadences at once, mid-period, so each snapped cut-off (e.g. the weekly
Monday 00:00, the daily 00:00) was already hours or days in the past when the freeze ran. The
entry prices were captured at the freeze moment (`frozen_at`), so a 1h/6h/24h horizon measured from
the *cut-off* had already elapsed before the entry existed. The collector correctly refuses to
backfill those with a current price and records them terminal-invalid (`midpoint=None` + reason),
rather than inventing a forward move. **In production this never happens**: the freeze crons fire a
few minutes after each cadence boundary, so `frozen_at ≈ cut-off` and every horizon is genuinely in
the future. The valid forward path is proven deterministically in run A.

### Isolation of test records

Both runs use throwaway databases (in-memory for A, a deleted temp file for B). No test or dry-run
row is written to the real database, and none can enter real performance: the status API reads only
`provenance_class='prospective'` rows, the edge verdict requires the predeclared minimum sample, and
synthetic cohorts are excluded everywhere (see `docs/synthetic-replay-decision.md`).

## Verdict

The pipeline runs end to end without a browser: discover -> prices -> order book -> trade flow ->
signals -> rank -> freeze (6h/daily/weekly, full universe, roles) -> persist -> forward observe
(causal) -> resolve -> midpoint + executable results -> baselines -> ablation -> walk-forward ->
research status -> Replay display. The only thing not yet present is **time**: real forward outcomes
accrue after the horizons elapse on cohorts frozen at the boundary in production.
