# Phase 2 milestone review — 2026-09-20

Phase 2 remains **in progress**. Base: accepted Phase 1 `43999b5`, draft PR #14.
This milestone supplies diagnostic capture and pure parsing/view helpers, not a complete
prospective collector or a validated scientific result.

## Implemented

- Four immutable, hash-versioned source contracts and parameter allowlists, disconnected
  from v1 application settings: Gamma markets, CLOB book, Data API v2 trades and Coinbase
  BTC-USD ticker. Read-only GETs; no credentials, redirects, implicit retries or scans.
- Explicit bounded request/time/byte budgets. Every attempted response keeps raw bytes,
  status/error, query scope, receipt ordinal, session and clocks. Raw files/receipt are
  fsynced before a post-durability acknowledgement; parsed output receives a separate
  acknowledgement. Exclusive files refuse replacement. Partial artefacts remain intact.
- Crash recovery preserves first receipt and uses actual later parse time; missing parse
  acknowledgement refuses admission. Monotonic comparisons apply within clock sessions.
  Clock uncertainty is unknown, never zero. The journal is local diagnostic evidence,
  with no automatic Feature Store write or prospective flag.
- Exact JSON parsing, duplicate-key/nonfinite refusal, ordered source-local identity,
  numerical book/trade primitives, closed paging shapes and explicit native-clock units.
  Source-local IDs do not imply verified chain/collateral or economic event identity.
- Pure as-known version and dependence helpers. Later corrections cannot leak backward;
  unresolved groups prevent split readiness; conservative evaluation groups are ineligible
  as model features. Whole graph versions cannot be mixed.

## Evidence

Three initial diagnostic requests returned 200 at 16:57 UTC; only their output inventory
and hashes were observed, so they are not preserved prospective samples. The subsequent
durable capture at 17:04 UTC retained all four sources locally. Its hash-linked summary is
[PHASE_02_RUNTIME_EVIDENCE.json](PHASE_02_RUNTIME_EVIDENCE.json). Raw evidence remains in
the recorded, Git-ignored `data-dumps/fs2_capture_...` directory, with no deletion/retention
change. Four captures verified read-only and exact Gamma/book/trade parsers succeeded.
Book sample: 36 bid/130 ask levels. Trade sample: two rows and more pages available;
coverage is explicitly bounded, not complete history. All captures remain unadmitted.

Current official sources checked:

- [Data API v2 migration](https://docs.polymarket.com/api-reference/data-api/migrating-from-v1):
  new integration uses v2 envelopes, snake_case and cursors; v1 behavior remains unchanged.
- [Public trades](https://docs.polymarket.com/api-reference/feeds/list-trades): explicit
  taker-only scope and cursor lineage. Transaction hash alone is not a fill identity.
- [Order book](https://docs.polymarket.com/api-reference/market-data/get-order-book): native
  timestamp retained; this REST page alone does not establish its unit unambiguously.
- [Markets](https://docs.polymarket.com/api-reference/markets/list-markets) and
  [market stream](https://docs.polymarket.com/api-reference/wss/market): ordered source
  identity and snapshot/delta forms; bounded live stream verification is now recorded below.
- [Coinbase ticker](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker):
  last-trade time is distinct from the complete bid/ask snapshot's receipt time.

Public runtime success is not bulk/commercial redistribution permission. Source contracts
declare only bounded local diagnostics; rights admission remains part of the source bridge.

## Validation and self-review

39 targeted tests passed covering exact values, failure/partial capture, corruption,
crash recovery, clock regression, request/byte/time guards, no redirect/retry, source
identity/rule changes, paging uncertainty, and as-of/dependence isolation. Full backend
regression result is recorded in the checkpoint after completion. Full backend Ruff,
contract checker and whitespace checks passed. Actual live probes made four finite public
requests; no database, scanner, scheduler or production configuration was touched.

Self-review: preserve raw and parsed artefact availability separately from later index-row
durability. The journal is not tamper-proof against filesystem owners, and fsync depends on
the local filesystem/storage guarantees. Do not treat diagnostic JSON as research admission.
The current source-specific parsers are pure transformations; the bridge must record their
actual computation time rather than borrow the earlier generic JSON parse timestamp.
The as-of helpers operate on validated version rows; group annotation quality is a separate
scientific prerequisite, not inferred from connected-component output.

## Second milestone — continuation at 21:43 UTC

The cursor/deadline/filesystem failure regressions are implemented: 23 capture tests pass.
Cancellation preserves partial bytes and remains cancellation; failed raw fsync leaves no
acknowledgement; v2 receipts hash-link the session file. Original v1 diagnostics still verify.

The diagnostic bridge adds source-specific parse artefacts with actual later parse/ack
clocks, imports to an explicitly guarded local schema, preserves receipt/raw bytes, and
appends runtime registry verification without a circular FK. Real earlier diagnostics are
reconstructed; mock transports are synthetic. Rights scope explicitly denies model-feature
admission. Nine bridge tests pass, including interrupted import, same-payload retries,
permission/rate-limit/source errors, partial source parse refusal and concurrency. The bridge
also ran inside the actual disposable PostgreSQL integration before testing privilege drift.

All four preserved live diagnostic captures imported successfully to disposable local SQLite
at `/var/folders/l7/7lfr1jg93_n7jjr5wswnzs4r0000gn/T/arepo_v2_bridge_p1ssbs48/fs2_test_diagnostics.sqlite`;
each retry was identical. Source-specific artefacts were appended under the original capture
directories, leaving prior bytes unchanged. No further live source requests were needed.

Exact book replay has six tests: snapshots, zero-size removal, atomic invalid batches,
receipt identity conflicts, reconnects, clock regressions, bounded work and raw lineage.
Review found that rejecting an invalid delta must also invalidate continuity: the numerical
book remains unchanged, but further deltas now require a fresh snapshot. Continuous native
sequence completeness is never claimed, even with a usable returned snapshot.

Evidence-linked Gamma projection now preserves condition, market, ordered token and group
versions with actual transform acknowledgements. Source event groups remain explicitly
unresolved economic dependence; chain/collateral are not inferred. A local end-to-end test
checks exact values, as-of links and idempotency. The two captured markets projected to
12 immutable records and an identical retry in disposable SQLite.

Four stream tests cover finite capture, quiet timeout, oversized mock frame and local fsync
failure. Actual public verification captured a quiet snapshot/timeout, then a separately
selected active token's snapshot and four price changes; exact replay succeeded. See the
two stream evidence JSON files. These are finite diagnostics, not a continuous collector.

Self-review fixed cross-session UTC regression, rejection-induced replay gaps, filesystem
errors being mistaken for network errors, and parser-build versioning. Remaining loaded-code
versus on-disk hash limitation is explicitly recorded in PHASE_02_SOURCE_ADMISSION.md.
No production code paths, configuration, migration activation or scheduler changed.

## Exact remaining work

Final second-milestone validation: **674 passed, zero skipped**, 30.46s, including disposable
PostgreSQL 17.11; one existing Starlette/httpx warning. Full backend Ruff, canonical contract
checker and whitespace checks passed. Full suite used an explicit temporary SQLite URL,
AUTO_MIGRATE=true, disabled alert/digest email, AREPO_FS2_POSTGRES_BIN pointing to local
PostgreSQL 17 binaries, and `backend/.venv/bin/python -m pytest backend/tests -q --tb=short`.
Frontend unchanged. Self-review of causal clocks, failure handling, immutable retries and
protected production paths is complete for this diagnostic milestone, not Phase 2 acceptance.

Design and test the trusted prospective capture/registry admission boundary described in
[PHASE_02_SOURCE_ADMISSION.md](PHASE_02_SOURCE_ADMISSION.md). The diagnostic bridge is
deliberately not that interface. Pin loaded parser builds, settle journal versus SQL-readable
availability and preserve post-durability evidence. Refine the canonical contract explicitly
where needed, then implement causal admission and failure/recovery tests. Recheck all phase
acceptance gates, final tests/review/docs/commit/draft PR before Phase 3. Current Phase 2
acceptance remains incomplete.
