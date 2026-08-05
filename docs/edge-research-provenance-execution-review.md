# Edge-research provenance + execution-modelling review

Independent review of the prospective-data pipeline and execution model on
`arepo-edge-research-infrastructure` (backend/astrolabe/evaluation/). Scope: look-ahead in
freezing/forward collection, immutability, idempotency, and honesty of the execution-cost model.

## Bottom line

- **No look-ahead found.** Every frozen input (`ResearchEntryRow`) is captured from a single live
  `now = utcnow()` snapshot (`research_cli.py:54-60`) that flows unchanged through
  `screen_universe` -> `build_entry_inputs` -> `cadence_cutoff` -> `freeze_from_inputs(frozen_at=now)`.
  `cadence_cutoff` only snaps `now` **down**, so `cutoff_at <= frozen_at` always holds by
  construction — a horizon computed as `cutoff_at + horizon` can never resolve before the entry
  price was actually observed once the causal guard (`research_tracking.py:78-88`) is honoured.
  The guard, immutability (`CohortFrozenError`), and idempotent upsert-once semantics for both
  forward observations and resolutions are all real and covered by passing tests
  (`tests/unit/test_research_pipeline.py`, 10/10 pass).
- **Execution costs are honestly modelled and structurally cannot overstate edge**: spread-cross +
  depth-aware slippage + fee are charged on both entry and exit, and missing depth makes the
  executable result `None` rather than assuming free liquidity. `executable_move <= midpoint_move`
  holds unconditionally (all three cost terms are non-negative by construction).

## Findings (severity-ranked)

1. **LOW** — `backend/astrolabe/evaluation/execution.py:39-40` (`slippage_points`): when
   `near_mid_depth <= 0` the function returns the `SLIPPAGE_CAP` (10 points) instead of treating the
   book as unfilled/unavailable. A literal zero-depth book means the trade cannot fill at the
   modelled stake at all — capping at 10 points is a *finite, optimistic* stand-in for what could be
   an infeasible fill, so it can understate cost in this specific edge case. Fix: treat
   `near_mid_depth <= 0` the same as `None` (return `None`, surfacing "unavailable") rather than a
   bounded cap, or keep the cap but document it as a deliberate worst-case ceiling, not a true zero-
   liquidity cost.

2. **LOW** — `backend/astrolabe/evaluation/execution.py:74-78`: when `forward_depth`/`forward_spread`
   are `None`, entry-time depth/spread are substituted for exit. This is a reasonable, documented
   compromise (only used to *avoid* marking the result unavailable) but it silently assumes exit-
   time liquidity/spread equal entry-time conditions, which can go either way (understate cost if
   liquidity dried up, overstate if it improved). Not a look-ahead — entry-time values are already
   known — but worth a status-field flag (e.g. `exit_depth_is_entry_proxy: bool`) so downstream
   consumers can distinguish a fully-observed exit from a proxied one.

3. **INFORMATIONAL** — `backend/astrolabe/evaluation/research_engine.py:42-53` (`cadence_cutoff`):
   snaps `now` down to the cadence boundary for `cutoff_at`, while `frozen_at` (and the actual entry
   prices) are captured a few minutes later per the deployed cron schedule (`render.yaml:101/107/113`,
   +5/+10/+15 min offsets). Horizon targets are computed from `cutoff_at`, not `frozen_at`, so the
   *nominal* "1h" forward window is actually slightly shorter than the true elapsed time from price
   capture (by the freeze delay, a few minutes). This is not look-ahead (the causal guard still
   requires `target >= frozen_at`) and is explicitly reasoned about in
   `docs/edge-research-end-to-end-dry-run.md`; it is only a minor precision note for horizon labels.

4. **INFORMATIONAL** — Parameter reasonableness: `SPREAD_CROSS_FRACTION=0.5`,
   `SLIPPAGE_COEFF=0.5`, `SLIPPAGE_CAP=0.10` (`research_constants.py:66-71`) are declared up front
   (anti-drift) and produce non-trivial round-trip costs (e.g. $100 stake against $1,000 near-mid
   depth => 5pt slippage per leg, 10pt round trip, plus spread crossing) — this leans conservative
   rather than flattering, consistent with the file's stated intent that a small favourable midpoint
   move must not register as edge. No evidence of tuning to outcomes.

## Provenance checklist

| Check | Result |
|---|---|
| Forward collector ever observes early / backfills a horizon predating freeze | No — `target < frozen_at` guard writes terminal-invalid (`midpoint=None`), never backfills; `now < target` skips (never observes early). Tested (`test_horizon_predating_freeze_is_invalid_not_backfilled`, `test_forward_collection_is_causal_and_idempotent`). |
| `frozen_at` is true entry-capture time | Yes — `research_cli.py:54` sets one `now`, reused for screening and passed as `frozen_at`. |
| Frozen cohort/entry rewritable later | No — `add_entry` raises `CohortFrozenError` once `cohort.frozen`; no update/delete path exists on `ResearchEntryRow` anywhere in the codebase. |
| Forward observations idempotent | Yes — `upsert_forward` no-ops if a row already exists for (entry, horizon) (`research_repository.py:241-245`). |
| Resolutions re-flipped | No — `record_resolution` only fills an unset resolution, never overwrites an existing one (`research_tracking.py:144-151`). |
| `screen_universe` look-ahead | None found — uses only `market_service.enrich_markets` / live trades fetched at the same `now`, no future data referenced. |
| Postgres portability | Clean — only portable column types, no raw SQL, no SQLite-specific constructs (`json_extract`, `ON CONFLICT`) in any `research_*.py` file; upserts done via explicit select-then-insert in Python. |
| Timezone handling | Consistent `_utc()` normalization to aware UTC in both `research_repository.py` and `research_tracking.py`; `utcnow()` is tz-aware at the source. |

## Tests run

`cd backend && python -m pytest tests/unit/test_research_pipeline.py -q` → **10 passed**.
