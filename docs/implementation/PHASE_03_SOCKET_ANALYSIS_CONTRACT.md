# Phase 3 — D064 durable socket diagnostics

Implemented software milestone, 2026-09-25; acceptance result in PHASE_03_REVIEW.md.
This is not empirical source acceptance, feature admission or Phase 3 completion.

## Inputs and authority

`record_socket_analysis` accepts a sealed D063 socket root, an optional separately collected
D057 post-book computation, an explicit `WindowReconciliationPolicy` and a fresh output root.
It derives all identity, source provenance, raw bytes and clocks from verified dependencies.
No request, arbitrary transport, caller observation, clock or provenance override is exposed.
Outputs must be outside every socket/pre/post computation and raw-source dependency.

The consumer freezes version/build, policy, paths and limits before actual reading. It preserves
read start/completion, input durability, computation start/completion and result durability.
Every event/raw/ack chain is verified and matched to the socket report; every post-source primary
request receipt is authenticated against the verified observation. Post provenance must match.
Original identity availability is retained separately from these new consumption clocks.

## Exact interpretation

A new adapter feeds verified successful socket receives to the existing D059 exact receipt
projection. Its original synthetic public API and historical journal formats remain unchanged.
Binary, malformed, truncated, unrelated and out-of-interval data retain their existing distinct
states. Socket-rejected bytes remain unavailable. Early termination leaves an uncovered tail;
refusal before subscription produces no numerical interval or fabricated endpoint.

D061's pure endpoint arithmetic is shared behind independently authenticated envelopes. The
socket report's durable acknowledgement is the conservative post-request boundary; response time
alone cannot make an early request eligible. Compare exact best price/size, preserving original
mapping/rules, freshness, failure, closure, missing-post and endpoint-separation reasons. Endpoint
agreement does not repair coverage, establish full-book equivalence or prove native continuity.
The actual source provenance is preserved. All origin/source/feature admission remains false.
F02/F10/F27 still lack their native continuity/fill prerequisites.

## Storage and recovery

New root prefix `fs2_socket_analysis_`; version `fs2-socket-analysis-v1`. Three payload/ack pairs:
policy, input and facts. The facts include whole exact coverage and reconciliation, not a scalar
summary. Nested coverage/reconciliation have explicit socket versions. Hashes bind original
input, policy and exact projection. Six successful files; at most eight including failure pair.
Whole output 64 MiB, individual artifact 16 MiB, failure reserve 64 KiB, free reserve 2 GiB,
180-second processing checks. Full output reserve precedes writing. Exclusive directory creation
makes concurrent writers single-winner. Partial cancellation/failure remains terminal and cannot
be read as a successful closure. No overwrite/resume or deletion.

Independent reading re-verifies all dependencies and replays at the original computation clock.
Original-Git recovery preserves full facts/summary and old clocks, creates a separate read receipt,
and protects all transitive dependencies. Read-only recovery never reconnects or recollects.

## Validation and next gate

Required coverage: actual loopback pre/window/post, exact rational coverage, endpoint agreement
and disagreement, early request, changed/closed/failed/missing post, refusal before subscription,
early close, resealed raw/clock/value/provenance corruption, dependency path protection, terminal
partial persistence, resource refusal, concurrent writers, original-Git recovery and affected
legacy coverage/reconciliation/recovery. See the review for exact final test count and duration.
These are synthetic/loopback software tests, not measured public-source behavior.

Next: freeze and commit one finite public diagnostic protocol and its runner before collection.
Use the already documented fixed D046 target, fresh targeted Gamma/book, at most one 60-second
socket and a separately permitted post-source pair. Recheck source semantics/rights and actual
free disk, reserve all source/socket/computation/recovery costs, declare exact request/time/byte
caps, policies, evidence destination and failure branches. A closed/failed target is a retained
result, never permission to search for another. Do not rerun the universe or accepted historical
reads. No public diagnostic has run under D064. Measured controls, external admission and the
representative prospective pilot remain Phase 3 gates. Phase 4 starts in a fresh conversation.
