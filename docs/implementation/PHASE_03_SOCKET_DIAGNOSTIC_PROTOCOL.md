# Phase 3 — D065 fixed public socket diagnostic

Frozen design, 2026-09-25. Run only after the runner/tests/self-review are committed, the draft
PR updated and the exact implementation SHA recorded at runtime. This is one diagnostic, not
sampling, a prospective panel, a registered feature or scientific confirmation.

## Fixed target and source access

Use market `1068745` and token
`71990823545476172057397539228999083435242402644332688321711165550800328090716`,
unchanged from the D046 historical reference. Do not refresh/reinterpret the old selection or
choose a replacement if this target is closed, unavailable or uninformative.

Official documentation checked 2026-09-25:
- https://docs.polymarket.com/api-reference/markets/get-market-by-id
- https://docs.polymarket.com/market-data/prices-order-books
- https://docs.polymarket.com/market-data/realtime-data

Use public unauthenticated Gamma market-ID and CLOB book GETs and the public market WebSocket.
The raw socket protocol specifies `assets_ids`/`type: market`, text PING every ten seconds and
PONG replies. SDK casing differs. Public access here does not establish redistribution rights,
native monotone ordering or archival completeness. No authenticated user channel, bypass,
credentials, private data, purchase or trade. Source registry rights/provenance policy remains
receipt-time internal research; no publication of complete source payloads. Existing native-time,
continuity and economic-unit limitations remain binding.

## Ordered attempt and failure branches

1. CLI has one fixed output: `data-dumps/fs2_socket_diagnostic_20260925_1`. Existing directory
   refuses the run; no automatic resume, retry or second attempt. Require the full immutable Git
   SHA. Extract/hash-check the entire loaded source/panel package against that commit before any
   request. Verify actual free space for the full reservation below before creating the root.
2. Durably freeze target, limits, build, source policy and numerical policies before reading any
   current source value. Save actual stage intents and all primary source/computation clocks.
3. Exactly one fresh pre pair: Gamma market ID, then the fixed CLOB token. Two requests even if
   Gamma returns an ordinary retained error; a torn/exceptional source failure stops instead.
   Compute D057 book facts with 60-second receipt/identity age ceilings.
4. If the pre snapshot is not exactly one observed snapshot, retain its states and recover that
   computation; do not connect or collect post sources. Known-active identity is still enforced
   by the socket driver, not inferred merely from an observed quote.
5. Otherwise attempt one D063 connection, 60,000ms from actual subscription-send completion.
   Identity and quote age ceilings at binding/subscription: 60,000ms each. No retries/reconnects.
   A refusal or connection failure retains the driver's explicit evidence.
6. Collect one post Gamma/book pair only when a subscription was actually sent and original
   identity remained fresh at send completion. Even an early disconnect may have a post pair,
   but its tail stays uncovered. Post requests begin after the socket report acknowledgement.
7. D064 analysis policy: post age 60,000ms; last-receipt/post separation 60,000ms; receipt hold
   1,000ms. These are development engineering ceilings, not validated freshness parameters.
   Missing post remains unavailable; agreement never repairs an interval or establishes profit.
8. Independently re-read each successful child and compare its summary. Recover its exact full
   facts under the original Git SHA into separate read roots. Save those actual read receipts.
   Do not reconnect/recollect during recovery. Preserve any partial failure, with class/stage/time
   only; no untrusted exception text or source secrets in reports.
9. Report exact roots/build/policy hashes, child states and clocks, new recovery clocks, elapsed
   time, parent-process peak resident memory and retained bytes before report. Retained/raw totals
   and relevant frame/gap/endpoint counts are derived read-only into the measurement evidence.
   Parent memory excludes recovery child peak memory; do not claim a whole-tree peak.

## Frozen bounds

| Component | Limit |
|---|---|
| HTTP | At most four GETs: two per pair; no retries; 262,144 bytes/response, 524,288 bytes/pair, 15s/request, 60s/pair |
| Source retention | 16 MiB per pair including parsed artifacts, existing 64 KiB failure reserve |
| Book computations | 16 MiB each, compact child read; 4 MiB artifact, 180s operation checks |
| Socket | One connection, <=60s, 1,000 frames, 262,144 bytes/frame, 16 MiB raw, 40 MiB retained, 1,032 events; original D063 bounds unchanged |
| Analysis | 64 MiB whole, 16 MiB artifact, 180s operation checks |
| Recovery | Up to four original-Git reads, each existing 300s subprocess deadline and 16 MiB output check |
| Diagnostic envelope | 512 MiB whole reservation, 4,096 files, 256 KiB per envelope artifact, 2 GiB untouched free reserve |
| Time | No new acquisition stage/request after 180s; total 1,500s stage checks; individual in-flight work retains its tighter child deadline |

Time checks are stage checks, not a claim of hard real-time cancellation of synchronous disk or
Git operations. The socket has its own actual send-anchored deadline and closes on failure.
Every child has its own finite write budget. Check the remaining full reservation before each
stage. Initial disk evidence is observational; remeasure immediately before the attempt.
Never reclaim space by deleting research evidence or silently narrowing the discovery universe.

## Validation and interpretation

The explicit loopback test seam requires HTTP MockTransport and numeric 127.0.0.1 socket only;
it preserves synthetic provenance. Tests cover the full fixed chain/original recovery, exact
request identity/order/count, closed/failed priors, cancellation/no resume, absent capacity and
uncommitted-code refusal. D063/D064 cover underlying transport/replay/error/causal behavior.

Record every public outcome, including failure or closure. A one-target diagnostic establishes
only the observed behavior of that attempt. It cannot accept family coverage, scheduled controls,
selected external information, native sequencing, an edge or the representative Phase 3 pilot.
After reporting, refine the remaining Phase 3 contract against the actual result. Do not start
Phase 4; its eventual starting point belongs to a fresh Codex conversation.
