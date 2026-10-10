# D063 — durable socket-window driver

Status: implemented, self-reviewed and accepted as a scoped software milestone; 47 affected tests passed.
This supplies the D062 transport's owning driver. It does not admit a feature or complete Phase 3.

Use a new fs2_socket_window_ journal/version. Existing D058–D061 synthetic records and readers
are unchanged. The public function has no caller transport/URI/provenance/token/clock override;
its prior market/token/rules identity derives from a verified D057 targeted source computation.
A separate numeric-loopback function requires synthetic prior inputs and retains synthetic
provenance. Public diagnostics require prospective prior evidence. Mismatch is a retained
refusal, not a promotion of fixture evidence or a fallback to a different source.

Before connect, freeze source/connector/library/options/build, explicit receipt-age limits,
duration and whole storage/operation bounds. Record actual pre-computation read and binding
durability. Require matching known-active source identity, freshness at read completion and
binding durability; check again after connection and subscription-intent persistence immediately
before sending. A delayed send cannot consume stale identity. Save subscription completion age
separately: successful send does not retroactively extend freshness. Source clocks and rules
availability remain original. Closed/invalid prior facts retain a terminal failed journal.

One connection, one derived subscription, no redirects/proxies/auth/retry/reconnect/target search.
Open <=5 seconds, send <=1 second, close <=2 seconds, interval <=60 seconds from actual subscription
send completion (including persistence overhead). Fixed application PING every ten seconds; one
pending receive. Stop/drain that receive before sending a heartbeat. Every successful return
records its actual receipt immediately; append/persistence time is separate. Binary/text/PONG/
unparseable payloads remain raw evidence. Rejected oversize bytes are unavailable with null raw
hash/count, never a fabricated empty prefix. Preserve error class and bounded sent/received close
codes; do not log arbitrary peer reason strings. Local filesystem failures never become upstream
failures. Cancellation closes the actual socket and retains the failed/partial journal.

At most 1,000 received frames, 262,144 bytes per frame, 16 MiB total raw, 1,032 events, 40 MiB
retained and 2 MiB per metadata file; retain a 64 KiB failure reserve and 2 GiB free space.
Processing checks bound 180 seconds at operation boundaries. A received frame exceeding the
remaining raw budget preserves an exact prefix and observed full hash/count, then stops; this is
distinct from a socket-rejected frame whose raw bytes were never returned. Reserve closing events.
Source/pre-computation evidence stays outside the new journal and is never copied or deleted.

Independent replay verifies complete closure, source binding, code/library contract, all raw
hashes, append chain and distinct observation/record/fsync clocks. Replays send-intent/operation
starts, source freshness, single subscription, fixed heartbeat schedule, terminal and cleanup
facts. No current wall clock replaces original freshness. Original-Git recovery protects every
pre/source dependency and emits a new read receipt without reconnecting. Refused, failed, partial,
late, truncated and duration-complete states remain distinct; duration completion is not continuity.

Validation must cover actual loopback wire/heartbeat, connection refusal, peer/oversize failure,
source staleness including after connection, provenance mismatch, cancellation and partial save,
concurrent ownership, raw/clock/identity/report corruption, path/resource limits and original-code
recovery. No public diagnostic may run until this driver and subsequent coverage/reconciliation
integration are tested, reviewed and committed under a separately frozen finite protocol.

Next integrate the new verified socket journal with exact receipt coverage and post-window
request/endpoint reconciliation using a new durable consumer/version. Preserve old synthetic
schemas and gates. Native sequence/fill identity remain unproved. Measured controls, selected
external information and a representative pilot still block full Phase 3 acceptance. Phase 4
begins only in a fresh conversation after the required complete handover.
