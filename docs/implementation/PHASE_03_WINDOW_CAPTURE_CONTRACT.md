# D058 — finite synthetic raw stream windows

Status: implemented, self-reviewed and accepted as a scoped software milestone; 40 affected tests passed. This is a software
capture/recovery milestone within Phase 3, not live source verification or a feature window.

`window_capture.capture_window` accepts only the exact immutable SyntheticWindowFeed fixture
class, a new canonical output directory, token/condition and explicit duration. There is no
live transport, network connector, external factory, supplied clock or provenance override.
The driver owns actual async receipt and persistence times; all records remain synthetic.
Fixture frames retain text/binary distinction and raw bytes, including arrays, PONG and invalid
JSON. Decoding/identity admission are intentionally deferred to the next scoped consumer.

`window_journal` freezes policy/build/source endpoint and full limits before events. Its flat,
exclusive `fs2_window_` journal preserves connection, subscription intent/completion, heartbeat
intent/completion, each received raw frame, terminal reason and close. Each event has a receipt
clock, ordinal, preceding event hash, exact raw length/hash and post-fsync acknowledgement.
Raw bytes are persisted before any future parsing. Subscription completion anchors the fixed
interval; acknowledgement work consumes that interval. Ten-second heartbeats do not cancel a
pending receive. End-of-interval drains an already completed receive and counts late frames;
a still-pending receive is cancelled rather than attributed a fabricated payload.

Limits: at most 60 seconds (explicit shorter synthetic test policy permitted), 1,000 received
frames, 256 KiB retained per frame, 16 MiB total raw including outbound payloads, 32 MiB total
journal, 64 KiB failure reserve, 64 KiB per metadata file, 1,032 events, two GiB free reserve.
Processing deadlines are checked at boundaries, not a process kill. Whole reservation precedes
directory creation; free/retained checks precede receive/write. Fixed fixture allocation is also
bounded. Frame/raw stops are explicit incomplete reports. Local storage/time/write failures
retain a terminal failure journal; they cannot masquerade as complete reports. No resume or
cleanup deletes evidence. The future live connector must separately enforce socket message/
queue/connection/close bounds and transport-level oversize errors; those are not tested here.

For a fully received oversize fixture, retain only the declared prefix with full observed
length/hash and truncation flag, then stop. Replay checks the prefix length against the frozen
budget. It cannot independently reconstruct the omitted suffix. This is explicitly incomplete
raw evidence, not archive equivalence or permission to truncate existing research history.

Independent replay verifies full file closure and bounds, policy/build, raw hashes, ordinal
chain, actual same-session monotonic/UTC chronology, outbound intent/completion order, heartbeat
schedule and terminal state. A cleanly closed disconnect/budget stop is a verified incomplete
capture. Duration completion establishes only elapsed observation time; continuity, native
clocks, origin and feature-store admission remain false. The original-Git reader preserves the
full report and raw/source clocks, issuing only a new recovery receipt.

## Review and handoff

Review covers raw retention before later interpretation, fixed timing, pending-receive ownership,
late-frame accounting, causal event/ack chronology, prefix limits, cancellation/partial writes,
one concurrent owner and read-only original-code recovery. Existing probe, BookReplay and all
old original-reader APIs/schemas remain unchanged. No databases, live requests or production
paths are involved.

Next implement the verified window decoding/coverage consumer in PHASE_03_DENSE_WINDOW_NEXT.md:
source-frame/array-element lineage, unsupported/control/malformed events, exact snapshots/deltas,
clock/identity mismatches, invalidation and honest uncovered durations. Then independently plan
causal identity plus REST pre/post reconciliation and a real bounded connector; do not infer
registered F02/F10/F27 availability from this synthetic capture. Integrate a new origin version
and full role/control/target reservation only after numerical coverage and runtime tests.
