# Phase 2 acceptance review — 2026-09-20

**Accepted**, implementation `54be417`, 685 backend tests passed. Draft PR #15 remains open,
stacked on Phase 1 #14 and Phase 0 #13. No production merge or rollout.

## Result and scope

Phase 2 supplies exact bounded public source capture, durable receipt/parse evidence,
evidence-linked identity versions, causal as-of/dependence helpers and snapshot/delta replay.
A dedicated predeclared source journal admits new receipt-time source facts, with SQL as a
later index and its own post-commit acknowledgement. Generic prospective writes remain
closed. This source interface does not implement a representative panel, predictive models,
economic value or production collection.

Capture persists raw bytes/receipt before parsing and retains failed attempts, original
clocks, source scope and session ordinals. Exclusive files and fsync acknowledgements prevent
silent replacement or invented recovery clocks. Source-specific parsing and identity
transforms have separate actual computation/acknowledgement evidence. Exact numbers and
original spellings remain intact. Source-run policy/build is durable before requests; injected
transports stay synthetic and old diagnostic directories cannot be adopted.

Build identity pins package files before import, compares loaded function code with compiled
source and refuses changes before/after capture and read. Registry and source rows are derived
only from complete verified primary artefacts. A dedicated index function takes a run directory,
never caller-supplied prospective records or a bypass flag. Read-only recovery refuses torn or
missing artefacts. A preserved local copy projects identical rows, including original URIs.

Gamma identities preserve source condition/question IDs, outcome ordering, rule hashes and
revisions. Unknown chain/collateral/token-contract namespaces remain unresolved. Source-event
groups do not establish independent economic causes; as-known and conservative evaluation
views remain distinct. Rejected deltas/reconnects invalidate replay until a full snapshot.
No continuous native sequence completeness is asserted.

## Runtime evidence and limits

- PHASE_02_RUNTIME_EVIDENCE.json: four preserved HTTP diagnostics at 17:04 UTC, Gamma,
  CLOB REST book, Data API v2 trades and Coinbase. All earlier diagnostics remain unadmitted
  for prospective research; local imports are reconstructed. Two Gamma markets projected to
  12 identity/group records with identical retry.
- PHASE_02_STREAM_EVIDENCE.json: quiet-token full snapshot plus explicit timeout.
- PHASE_02_ACTIVE_STREAM_EVIDENCE.json: separate bounded active-token selection, then one
  snapshot and four price-change frames, replayed exactly. No continuous collector.
- PHASE_02_PROSPECTIVE_SOURCE_EVIDENCE.json: new predeclared source-only run at 22:37 UTC,
  three requests, three observed HTTP 200 responses, nine registry/observation records,
  identical local SQL retry, 83,967 journal/receipt bytes. Receipt-to-primary availability:
  Gamma 40.566 ms, book 39.211 ms, trade page 72.735 ms in this one run. These three timings
  do not estimate a latency distribution. No event-time availability, representative sampling,
  model evaluation or predictive claim.

Preserve all referenced local data-dumps roots. Local SQL indexes are projections; the original
journal and exact build `54be417` are needed to verify the new source run. Later code must not
silently reinterpret an old run. Archive-equivalence certification remains a separate gate.

## Source verification basis

[Gamma markets](https://docs.polymarket.com/api-reference/markets/list-markets),
[CLOB book](https://docs.polymarket.com/api-reference/market-data/get-order-book),
[Data API v2 trades](https://docs.polymarket.com/api-reference/feeds/list-trades),
[v2 migration](https://docs.polymarket.com/api-reference/data-api/migrating-from-v1),
[market stream](https://docs.polymarket.com/api-reference/wss/market), and
[Coinbase ticker](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker)
were checked for current fields and protocol semantics. New trade capture uses v2 snake_case,
explicit taker-only scope and cursor lineage; the existing v1 client is unchanged.

Native ambiguous clock units remain unadmitted; transaction hash is not a fill identity.
Coinbase last-trade time is not the entire quote's publication time. Bounded public access is
not a commercial redistribution licence. The exact admitted purpose and exclusions are in
[the matrix](PHASE_02_SOURCE_ADMISSION.md) and
[the source contract](../architecture/V2_PROSPECTIVE_SOURCE_ADMISSION.md).

## Validation and self-review

Final full backend: **685 passed, zero skipped**, 36.03s; one existing Starlette/httpx warning.
Test setup: fresh temporary SQLite DATABASE_URL, AUTO_MIGRATE=true, alert/digest email false,
AREPO_FS2_POSTGRES_BIN=/usr/local/opt/postgresql@17/bin, then
`backend/.venv/bin/python -m pytest backend/tests -q --tb=short`.
PostgreSQL 17.11 is an actual disposable authenticated loopback cluster, never production.

Full backend Ruff, canonical checker (13 hashes, 452 fields, 21 entities, 140 mappings,
60 feature/experiment cards, 11 phase contracts) and whitespace checks passed.
Tests cover exact primitives, duplicate/malformed payloads, immutable receipts, cancellation,
rate limits, failed fsync, page scope/cursors, clocks, identity revisions/as-of exclusion,
unresolved dependence, replay gaps, source policy/build binding, cutoff filtering, no
diagnostic promotion, SQL rollback, post-commit receipt failure, retries and preserved copies.

Self-review found and fixed rejection-induced replay gaps, cross-session UTC regression,
filesystem failures misclassified as network failures and parser build drift. Final review
checked causal ordering, durability semantics, numerical preservation, failure recovery,
bounded work and protected paths. No v1 configuration/API/scheduler/frontend changes occurred.
SQL owner/filesystem owner tampering is outside these integrity guards; hashes are not
authenticated evidence against a malicious owner. fsync depends on storage guarantees.
The source availability acknowledgement concerns primary input facts, not its own receipt's
bytes or a later model execution. Phase 3 must record actual read/computation before origins.

## Phase 3 handoff

Source-only interface accepted. Next refine a representative bounded measurement protocol,
sampling/control frame and actual origin/feature/target persistence. Admitted source clocks
support receipt-time analysis only. Sparse trades do not establish complete flow; source
event IDs do not prove independence. Streams/external ticker still require their own prospective
admission before use as model inputs. Missing families remain explicitly ineligible.
