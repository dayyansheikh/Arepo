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
  identity and snapshot/delta forms; live stream verification remains pending.
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

## Exact remaining work

1. Test cursor-parent progression, actual cancellation/deadline and filesystem-failure
   paths more deeply before collector use; retain failed attempts without invented clocks.
2. Design/test the receipt-to-store bridge, including source registry versions, durability
   links, parser completion clocks, immutable retries and crash recovery. Generic prospective
   admission remains closed. No caller Boolean may bypass it.
3. Build evidence-linked market/condition/token records and graph versions; leave unresolved
   chain/collateral/group links excluded. Refine canonical contract only with explicit decision.
4. Replay snapshots/deltas/gaps/reconnects, then bounded live stream verification; never
   assert complete sequences where the source supplies no proof.
5. Finish source rights/clock/coverage admission matrix, SQLite/PostgreSQL integration and
   v1 regression, self-review, current docs, coherent commits and draft PR acceptance.
   Only then proceed to Phase 3.
