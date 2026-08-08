# Agent 7 — Data-integrity / causal-audit

**Overall verdict: integrity is sound; two Medium gaps to close before/at the live migration.**
Immutability, append-only guarantees, causal timing and per-cohort denominators are correct. The
weakest links are (a) migration *value-level* verification and (b) the not-yet-built long-term
aggregate's dedup rule.

## Verified-correct invariants (evidence)
- **Append-only / immutable:** `discovery/snapshot_models.py` snapshots keyed unique on
  (scan_id, market_id, token_id); `research_entries` frozen values copied at freeze; freeze is
  idempotent on `(cadence, cutoff_at)` unique constraint (`research_models.ResearchCohortRow.__table_args__`)
  with an `IntegrityError` fallback. A frozen cohort's entries are never rewritten.
- **Causal timing:** `research_cohorts` stores `cutoff_at` (scheduled label) **and** `frozen_at` /
  `evaluation_origin_at` (actual causal origin) + `lateness_seconds`. Staging shows cohort 2 cutoff
  12:00 vs frozen 16:02 (lateness 14,527 s) — recorded honestly, evaluation measured from 16:02. No
  look-ahead: `scheduler/tick._freeze_due_cadences` only freezes a period once a **complete** scan
  exists with `started_at >= boundary`.
- **No fabrication:** unavailable observations stored as `midpoint IS NULL` + reason (1,005/1,382 at
  1h/6h in staging) rather than back-filled. `cohort_from_scan` **refuses an incomplete scan**.
- **Denominator identity (per cohort):** `research_replay` — expected+against+no_change+pending == scope
  total (16+13+1+50=80 verified). Live Replay does **not** aggregate across cohorts, so repeated
  snapshots are not mis-counted as independent. `research_analysis`/`replay_stats` are **not**
  API-exposed.
- **Retention safety:** `scheduler/retention.run_retention` prunes **only** category-C
  (`discovery_signal_snapshots`, `microstructure_snapshots`), never cohort-referenced scans, the latest
  complete scan, or any permanent research/account table. **No cohort/entry/observation is ever deleted.**
  So "no silent destruction of research evidence" holds today by construction.

## Findings
| Sev | Finding | Evidence | Fix |
|--|--|--|--|
| **Medium** | Migration reconciliation verifies per-table **counts** + cohort `entries==universe_size`, but does **not** verify per-record **immutable values** match. With `ON CONFLICT DO NOTHING`, a destination row whose PK pre-exists with *different* content would be silently kept, and later production rows can make `dest>=source` pass. §10 explicitly requires "for every source record… immutable values match." | `storage/import_sqlite.py` `_reconcile` (counts + cohort invariant only) | Add a value-level verification pass: for each source PK, confirm the destination row exists and a set of immutable columns (frozen values, timestamps, calc versions) hashes-equal. Fail closed on mismatch. **(remediated this pass)** |
| **Medium** | Long-term aggregate (spec §7) not yet built; when old detail is archived it must count **each market once per period**, not once per (market×cohort), else pooled cohorts of the same universe overstate evidence. | design gap | Specify the market-dedup + per-scope/per-horizon summary schema now; build when first cohorts approach archive age. Documented in DECISIONS + PRODUCTION_ROLLBACK. |
| Low | `import_sqlite` datetime coercion assumes naive SQLite times are UTC (they are, by app convention) | `_coerce_row` | Correct given the app writes UTC; documented. |

## Most dangerous potential causal-invalidity (currently mitigated)
If a future release ever exposed a **cross-cohort pooled** Replay number without market-level dedup, it
would show a *plausible but causally invalid* inflated sample. Mitigation: keep the aggregate's dedup
rule explicit and tested before it ships; live Replay stays per-cohort.

## Migration acceptance (for the live import, §10)
Run: dry-run → inspect reconciliation → `--require-empty` real import → verify counts → **verify
per-record immutable values (new check)** → verify cohort invariants → confirm Replay reads migrated
cohorts. Never modifies the source SQLite (`?mode=ro`).

**Conclusion: ship-with-fixes** (add value-level migration verification before the genuine Postgres
import; specify the aggregate dedup rule). Core provenance is trustworthy.
