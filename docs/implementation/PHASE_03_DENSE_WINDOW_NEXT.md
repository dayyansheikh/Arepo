# Phase 3 — bounded stream window implementation contract

Status: next scoped implementation after D057. This is a capture/coverage measurement,
not an assertion that public feeds provide complete economic event ordering.

## Evidence and current implementation

The F02/H02 pre-trade depth, F10/H10 execution-adjusted withdrawal and F27/H27 gap-free
60-second persistence designs require stronger evidence than snapshot arithmetic. D057
preserves exact snapshot components but cannot satisfy these windows. Existing
`feature_store/book_replay.py` always reports continuity unproven. The old `stream_probe.py`
is a five-frame/ten-second diagnostic with no application heartbeat; do not silently enlarge
its policy or reuse old diagnostics as a new window.

Official [market-stream documentation](https://docs.polymarket.com/market-data/realtime-data)
checked 2026-09-24 describes a fixed public socket, token subscription, book/price-change/
last-trade/tick messages, and application PING every ten seconds with PONG replies. Its
market-channel examples supply timestamps and hashes but no monotone sequence contract.
Inference: arrival ordering and matching endpoint snapshots cannot certify every intervening
venue update. Do not infer a unique fill from transaction_hash. SDK-normalized camelCase
messages differ from the raw API's snake_case; freeze which representation is parsed.

## Ordered implementation

1. Implement a separate immutable raw window journal with frozen build, source, token,
   condition, finite policy and synthetic/live-diagnostic provenance. Do not modify the
   old probe or BookReplay formats. An actual collector owns receipt clocks; caller-supplied
   rows/clocks are never prospective authority. Keep initial transport synthetic-only until
   its full capture/recovery contract passes. No production or SQL integration.
2. One connection and one fixed subscription. Record subscription and each outbound
   heartbeat intent/completion, every inbound text/binary/control frame including malformed
   and unrelated events, and connection/timeout/cancellation/close evidence. Raw bytes are
   durable before decoding. No reconnection, dynamic universe narrowing or silent retry.
   Preserve initial snapshot, ordered arrivals and end-of-window status; lack of a snapshot
   is unavailable, not an empty valid book. Never continue an invalidated book until a fresh
   snapshot, and never erase the earlier gap from coverage.
3. Freeze a 60-second observation interval anchored to actual subscription-send completion;
   allow at most five seconds to connect/subscribe and two seconds to close. Heartbeats are
   scheduled from that same anchor at ten-second intervals, without cumulative drift.
   Record actual interval duration and late work, never backdate to the schedule. Initial
   snapshot delay is uncovered time. Distinguish deliberate duration completion from message,
   raw-byte, retained-byte or heartbeat limits and transport failure. Persist the terminal
   event even if no source frame arrives.
4. Predeclare maximum 1,000 received frames, 256 KiB per frame, 16 MiB total raw,
   32 MiB whole retained journal, 64 KiB failure reserve and 2 GiB free-space reserve.
   Reserve raw+receipt+ack before receive/write. Enforce transport max_size and queue bounds;
   a library-rejected oversized message has unavailable raw bytes, not an invented prefix.
   If the collector receives an oversized complete frame, preserve the bounded raw prefix
   plus exact observed length/hash and explicit truncation; do not parse it as complete.
   Metadata/sent/terminal records count toward the whole cap. Keep finite file/depth limits,
   canonical paths and single-owner exclusive creation. These are engineering caps, not
   empirical thresholds or market-universe filters.
5. Independently replay complete successful journal closure, original build/policy/hash chain,
   all actual clocks and ordinal continuity. A cleanly recorded transport/budget stop can be
   a verified *incomplete* window; torn local writes cannot be a sealed successful window.
   Fresh read receipts must not rewrite source availability. Preserve failed/cancelled files.
   Add original-code recovery before a real measured run; no parser fallback or repair.
6. Separately implement exact received-window diagnostics from verified journals. Preserve
   source-frame index for array messages, heartbeat versus book-change semantics, explicit
   unsupported events, best-price consistency and raw native clocks/tick sizes. For weighted
   diagnostics use elapsed receipt duration, not number of updates. Report native-clock and
   venue-continuity limits; F02/F10/F27 admission remains false while their specific evidence
   is unproven. Do not label receipt-time diagnostics as the registered feature.
7. Add causal identity, pre/post-window REST observations and coverage comparison under a
   separately frozen full source/request budget. A later matching snapshot can reveal some
   errors but cannot prove an absent intermediate cancellation or trade. Retain disagreement
   and unknown states, and determine which feature families the actual public source supports.
8. Only after tests/review/commit and full capacity preflight, freeze a finite diagnostic run
   on a causally selected market. A successful connection does not by itself admit live
   origins, controls, SQL features or the Phase 3 pilot. Document any required unavailable
   evidence and investigate safe public alternatives rather than manufacturing continuity.

## Required tests and acceptance

Actual receipt/fsync/decode order; raw binary/text/PONG/array/malformed handling; no clocks or
payload overrides; exclusive/concurrent ownership; cancellation during connect/recv/send/save;
partial acknowledgement; file/directory/symlink and input mutation; retained/raw/frame limits;
failed heartbeat, initial snapshot delay, no messages, disconnected and early budget stops;
monotonic/UTC regression; hard receive deadlines and late persistence; exact read-only replay;
original-build recovery and old-probe regression. Synthetic transport may finish early under
a declared shorter test policy, always recorded as such, never pretending sixty seconds elapsed.

Once the capture milestone passes, checkpoint its exact evidence and then implement numerical
window/control integration. Phase 3 and all downstream phases remain gated by the main plan.

## D058 progress — 2026-09-24

A separate synthetic raw-window driver and journal now implement the finite event/persistence,
heartbeat, boundary, byte-count and exact recovery foundations. 40 affected tests passed.
See PHASE_03_WINDOW_CAPTURE_CONTRACT.md for implemented scope and limits. There is still no
live socket adapter, causal identity admission or pre/post REST reconciliation. Next execute
the decoded coverage consumer (step 6), preserving unavailable native sequencing; then refine
steps 7–8 against its outputs and the measured source capabilities. Do not repeat D057/D058.

D059 now implements step 6 through actual durable reads/computation and original-code recovery (90 affected tests passed). Next execute PHASE_03_WINDOW_IDENTITY_NEXT.md for causal source binding, endpoint comparison and a separately tested bounded live adapter. No registered window-feature or live-panel acceptance is inferred.
