# AREPO v1 to v2 mapping and loss register

Inspected implementation at production `e50f063d1a51a07eb32fcffeedd841b565ebca33`, 2026-09-20. These are source-code findings, not a fresh production database census. The quantitative counts in the supplied report remain the dated research audit's observations. No production SQL or application CLI was run for Phase 0.

## Repository and branch audit

- Root: `/Users/DayyanSheikh/Projects/astrolabe`; origin: `https://github.com/dayyansheikh/Arepo.git`; GitHub connector confirms public repository/default branch `arepo-free-production-v1` and push permission.
- Fetched production SHA equals expected audit SHA: `e50f063d1a51a07eb32fcffeedd841b565ebca33`.
- Initial local production SHA `8dff5f5ee489f2e9b7ded648f1f18dc679138b51` is an ancestor, with zero local-only commits. New branch created directly from fetched production; local production ref was not reset.
- New production commits since local tip include account digest work, category/replay work, batched observation/freezing writes, pool reliability, cache/egress fixes and scan pause. They are already in the research audit base. No research-snapshot advancement needed reconciliation.
- Lean branch comparison: production 0 ahead / lean 3 ahead, matching research. No merge/cherry-pick.
- Existing tracked tree clean; numerous unrelated untracked prompts/logs/launchers plus docs/email-implementation left untouched and excluded from commits.
- Structure: FastAPI/SQLAlchemy/Pydantic backend, Next.js frontend, GitHub workflows, Render/Vercel config. Existing repository retained.

## Schema and code mapping

Paths below are repository-relative. 'Supersede' applies only to future research authority; no v1 deletion/rewrite is proposed.

| Existing table/model or module | What actually exists | v2 mapping | Action / preservation limit |
|---|---|---|---|
| storage/models.py MarketRow → markets | Mutable cached question/condition/outcomes/category/volume/tick/etc; Float and JSON; updated_at | market_identity_version, condition_identity, token_outcome_version | Reuse serving cache; new immutable identity history. Current values cannot backfill past identities. |
| SnapshotRow → snapshots | token/market FK, Float bid/ask/mid/spread/volume/last, Float book JSON and captured_at | source_observation, book_snapshot, book_level | Preserve existing float values exactly; source decimal spelling and receipt history absent. |
| SourceHealthRow → source_health | Mutable state/last-success/error/latency | source_registry plus operational health | Keep health operational; it cannot prove historical schema/rights/clock verification. |
| ingest/microstructure_store.py → microstructure_snapshots | Float spread/depth/cumulative volume; same token-minute row can be overwritten; captured_at updated | new immutable source/book/feature observations | Supersede for v2 measurement; historical overwritten states and deltas irrecoverable without independent archive. |
| discovery/snapshot_models.py → discovery_scan_runs | Pagination proof, scan boundaries/funnel/counts/status/version and provenance | source/sampling manifests, legacy origin reference | Reuse complete-universe evidence where valid; scan start is not a common receipt time. |
| discovery_signal_snapshots | Append-only per scan/market/token; conditions, nullable event, scores/components/availability, ranking, quote floats | legacy origin/feature references | Preserve all component JSON and numbers, not only tags. Public top flag is a shortlist field, not analysed-universe completeness. |
| discovery_scan_locks | Mutable lease | separate operational collector leases | Reuse pattern, never treat as permanent research evidence. |
| evaluation/research_models.py → research_cohorts | Unique cadence/cutoff; frozen/actual origin/lateness/complete-scan reference/counts | research_origin and manifest linkage | Preserve cutoff scheduled label and stored actual origin exactly; validate limitations separately. |
| research_entries | Unique cohort/market/token, frozen component values/availability/family directions/quote/close/rank/category | feature_value, prediction, origin legacy bridge | Extend through immutable references only. Missing component values/event IDs stay missing. |
| research_forward_observations | Unique entry/horizon, Float quotes, collector timestamp, delay/exact/unavailable | outcome_observation, label_version | Retain delay and original exact flag; v2's stricter target is a different version. |
| research_preclose_observations | Mutable accumulator until closed; first/latest quote and counts | append-only outcomes then labels | Preserve remaining rows; cannot recover every intermediate quote from aggregate. No retroactive reconstruction of path extrema. |
| research_revisions | Append-only cohort correction log | version/revision lineage | Reuse principle, retain old detail; new typed revisions reference exact records. |
| evaluation/models.py → calculation_versions | Algorithm identity/description/time | feature/model/target artifact definitions | Pin original source/calculation versions for v1 replay; do not infer trained model. |
| signal_snapshots, weekly_cohorts, cohort_entries, ranking_audit | Older evaluation lineage with cohort/entry snapshots | legacy manifests/origin links | Preserve separately from discovery_signal_snapshots; do not double count overlapping weekly/daily/6h origins. |
| forward_price_observations | Older price-forward facts | legacy outcome links | Keep exact stored float/time/target version; no fresh source clocks inferred. |
| market_resolutions | One market row; unresolved may become resolved, then not silently flipped | versioned outcome/payout facts | Supersede for future revisions/fractional payouts. Current final status not proof of original availability. |
| evaluation_results | Mutable computed summaries | label_version + experiment result manifest | Preserve legacy outputs; reproducible v2 target separately versioned. |
| opportunity/snapshot_models.py → opportunity_snapshots/opportunity_entries | Frozen product shortlist layer | Optional baseline/product manifest reference | Do not use shortlist as full research population. |
| scheduler_state, scheduler_leases | Mutable due/attempt/success/lease state | Separate operational state | Reuse design, separate heavy/light/dense-window workload and leases. A successful job doesn't prove a usable observation. |
| accounts and alerts tables | User accounts/preferences/deliveries/saved markets | None | Protected, unrelated; no auth migration, exposure or cross-user data changes. |
| schema_migrations | v1 integer version ledger, current version 12 | new fs2 migration ledger | Keep isolated; never bump v1 version merely to create v2 tables. |

## Pipeline inspection and consequences

`discovery/bounded_discovery.py` reconciles keyset market/event paths with fallback/completeness checks. `scan_service.py` normalises markets, applies public eligibility and enriches every eligible market; ranking/display comes later. v2 sampled deep collection must be a separate population design, not removal of markets from the current discovery universe.

`ingest/normalize.py` keeps condition ID and outcome token strings but normalises price/size/liquidity through floats. Event tags reach category classification; durable event identity does not survive all paths. `opportunity/scoring.py`/snapshots carry partial identity. Future identity extraction should consume retained raw metadata before this lossy normalisation boundary, not guess from titles.

`analytics/anomaly.py` has seven heuristic weighted components, renormalises available weights, caps book-only strength and sets direction from the sign of price z-score. `research_predictors.py` explicitly documents identical AREPO/momentum direction, and v1 hit-rate excludes flat cases. These are reproducible historical baselines, not multiclass probability models or independent non-price ablations.

`analytics/flow.py` computes relative size, median/MAD, percentile, opposing notional share, top-wallet shares/HHI, cluster counts and late-life quantities. Detail dictionaries preserve some intermediates, but raw fills are not permanently persisted by a dedicated v1 trade table. Current history counts are not as-of wallet skill; 'evidence families' are heuristics, not empirically independent sources.

`cohort_from_scan.py` copies stored scan values into frozen entries, refuses incomplete scans, and defaults the stored origin to scan start. `research_engine.py`/`research_repository.py` enforce immutable/idempotent frozen cohorts and revisions. `research_tracking.py` writes due outcomes once, batches tokens and separates closure/unavailability. Its `now` precedes fetches and quote source timestamp is assigned at collection. These strengths remain; the v2 availability contract is stricter and cannot be certified retroactively.

## Irrecoverable information

| Missing material | What can honestly survive | What must not be reconstructed as fact |
|---|---|---|
| Native venue timestamps discarded/fallback used | Original stored timestamp plus collector/unknown semantics | Venue time or latency by subtracting a guessed constant. |
| First receipt/parse completion | Stored created/captured fields with exact original meanings | Historical first public/AREPO availability. |
| Event IDs/chain/rules missing | Condition/token links and separately evidenced later grouping | As-known event mappings using today's metadata. |
| Source decimals converted to Float | Exact stored IEEE-754 value and original JSON, if any | Original decimal spelling/precision. |
| Historical book deltas and lost minute updates | Snapshots and aggregate depth with coverage caveats | Cancellations, queue position, gap-free reconstructed books, path extrema. |
| Never-collected component values | Null/availability records and existing raw components | Volume acceleration, spread/depth change where audited coverage is zero. |
| Raw fills/window completeness | Existing aggregate flow details when present | Economic fill deduplication, arbitrary future quantiles, wallet/time sequences. |
| Wallet history/text vintages | Later reconstruction with honest provenance | Past wallet knowledge, prerelease expectations, original story receipt or revision state. |
| Scheduled origin vs late actual freeze/observation | Exact stored cutoffs, origin, delay and source scan | Timely predictions/outcomes that were never recorded. |

## Infrastructure-sensitive boundaries

`storage/migrate.py` is metadata-driven and v12; `_read_version` calls CREATE TABLE IF NOT EXISTS even from check. `evaluation/migrations.py`, API deps and scheduler entry points can auto-migrate. Render build invokes upgrade and AUTO_MIGRATE=true; both workflow groups also set it true. Do not execute these against production or inherited .env.

Scan workflow schedule is commented out; collection remains every 15 minutes. Do not restart scans. Current default retention can prune old non-cohort scan and microstructure history; archive is optional and only scan rows are archived. Even with archive configured, microstructure deletion is not covered by the scan archive path. Existing local archive verifies compressed checksum and row count, not scientific equivalence; R2 implementation raises. These paths cannot establish the v2 archive gate. No production retention setting has been inspected or changed here; config defaults are not proof of live environment values.

API read surfaces use persisted scans/cohorts and market-service cache; v2 remains offline from serving. Account access remains fastapi-users/JWT/HTTP-only cookies. Supabase Data API exposure was a conditional concern in the research audit, not a demonstrated exploit. New research tables must receive explicit access controls in their own tested migration.
