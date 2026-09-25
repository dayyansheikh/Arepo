# Phase 3 — bounded market socket transport integration

Status: next implementation contract after D061; not live admission or a run instruction.

Before editing, reload the checkpoint and identity/window contracts. Existing D058–D061 journals
are synthetic-only; never relabel those saved artefacts as prospective. Implement a versioned
transport/journal path whose provenance derives from its actual connector and verified prior
source evidence. A loopback/injected connector always remains synthetic. Keep the original
synthetic API, reports and original-Git readers recoverable.

1. Fixed public URI from the pinned clob.market_stream contract; no auth, headers supplied by
   callers, environment proxies, alternate targets, retries, reconnect iterator or redirects.
   Installed websockets 17.0.1 has proxy=True and supports HTTP redirects by default. Pass
   proxy=None, compression=None, ping_interval=None and reject every redirect in a bounded
   connector subclass. Do not mutate process environment or global library settings.
2. Freeze URI/source contract/version/library/budgets, pre-source identity rules and policy before
   connect. Verify actual fresh pre-Gamma/book computation and durable binding, then recheck
   freshness immediately before the actual subscription send (including connection delay).
   Expired/closed/failed input is a retained refusal, not a new target search.
3. One selected asset subscription {assets_ids:[token],type:market}; actual send-intent and
   completion are separate. Fixed ten-second text PINGs; no protocol transport pings. One pending
   receive, receipt clocks sampled at actual return, preserve binary/text/PONG/invalid frames.
   Bounded connect<=5s, duration<=60s and close<=2s, frame<=262144 bytes, queue<=4, fixed total
   bytes/messages from D058. Include local persistence/processing in the overall bound; no
   independent full window restarted after acknowledgement delay.
4. Socket rejection of an oversized frame has unavailable bytes. Preserve received close code /
   exception class and operation, not a fabricated raw prefix or invented full-frame hash. Journal
   acknowledgements and source availability remain distinct from transport receipt/send times.
   Preserve close errors/cancellation; do not swallow local disk errors as upstream failures.
5. Finalise and independently recover raw closure, clocks, code/provenance and verified prebinding.
   Integrate decoded coverage and D061 post-request reconciliation through a versioned reader;
   do not weaken the original synthetic build/provenance guard. Native continuity and registered
   features stay unproven even when all transport operations succeed.
6. Tests must use an actual local loopback server as well as fault injection: exact subscription,
   heartbeat/PONG, binary/text, no-redirect/no-proxy options, oversized frame, quiet timeout,
   peer disconnect, send/connect/close failure, cancellation, late receive, stale subscription,
   duplicate ownership, primary corruption and original-code recovery. Verify no lingering
   socket/server/task. Never use public services to satisfy unit tests.
7. Self-review, proportionate regression and commit the finished transport protocol before any
   public diagnostic. Then freeze one separately scoped, capacity-checked diagnostic using a
   fixed target (D046 historical target is only a candidate). Preserve a closed/failed attempt
   and do not chase alternatives. Report source access/semantics honestly; no representative
   pilot, control coverage or model input admission is inferred from one socket run.

Official raw market stream/heartbeat basis in PHASE_03_WINDOW_IDENTITY_NEXT.md. Recheck current
primary documentation before implementing an external-facing protocol. This contract supplements
steps 7–8; it does not supersede measured control/external-source/pilot acceptance. Phase 4 begins
only in a fresh Codex conversation after full Phase 3 acceptance and handover.

Primary sources rechecked 2026-09-25:
- https://docs.polymarket.com/market-data/realtime-data (raw market API tab; the SDK envelope
  uses different field names and must not replace the raw protocol).
- https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html (17.0.1).
- Installed websockets.asyncio.client.connect signature and process_redirect implementation
  inspected read-only. No dependency or environment configuration changed.

## D062 connector boundary — 2026-09-25

The connection primitive is implemented in socket_connector.py. It fixes the public URI and
all connection options, refuses redirects/retries, pins tested websockets 17.0.1, and exposes
an explicit numeric 127.0.0.1 loopback seam whose transport provenance remains synthetic. Actual
loopback tests cover raw text/binary/PING-PONG, rejected oversize data, redirects, disconnects
and cancellation. Close has an outer two-second deadline and aborts on failure without hiding
the original exception. Validation counts belong in the checkpoint/review.

This is a transport primitive only. It opens no socket on import, is not wired into any app,
CLI, journal, scheduler or collector, and does not verify identity or confer source admission.
The returned raw connection requires its owning driver to schedule ten-second PINGs, record
actual operation/receipt/durability clocks, impose window/message/total-byte budgets and close
in finally. Do not call the public factory manually as a substitute for the still-required
durable driver. Synthetic D058–D061 files remain unchanged and cannot be relabelled prospective.

Exact next implementation: versioned durable socket-window driver with verified fresh prebinding,
actual connection/subscription/receive/close facts and explicit partial/failed attempts. Freeze the
whole transport/source protocol before connect; recheck prebinding after connection and before
send. Use the new connector internally with no arbitrary factory/URI override in the public path.
Add a separate explicitly synthetic loopback path for fault tests. Extend independent and
original-code recovery, then integrate coverage/post-window reconciliation. Commit and test that
whole driver before any separately frozen public diagnostic. All remaining Phase 3 empirical
gates still apply.
