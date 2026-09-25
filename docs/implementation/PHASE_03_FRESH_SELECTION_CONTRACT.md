# Phase 3 — declaration-bound fresh selection (D050)

This milestone binds a new selection to an immutable D048 declaration. It does not enable
collection, admit origins or accept the Phase 3 panel. Existing D040 journals retain their
old schema, seed, weights, clocks and reconstructed status.

## Contract

- One deterministic sibling selection directory per declaration, exclusively created. No
  caller seed, clock, assessment payload, selection output path or retry/resume override.
  A failed attempt and every partial file remain preserved.
- Revalidate the declaration, build, full reserved capacity and frozen recipe before reading
  frame numbers. Freeze the selection/control policy and acknowledge it before invoking the
  original Git-pinned frame decoder. Verify its complete page/row inventory and all projections.
- Use the declaration's seed and per-stratum counts. A slot ceiling is a refusal boundary,
  never permission to truncate assignments. Retain unmapped/unknown metadata and exact weights.
- Until a durable trigger computation exists, the only accepted assessment policy is explicitly
  **no measured assessments**. Use D042 assessment semantics with an empty supplied inventory:
  every eligible member is `not_assessed`, neither triggered nor a negative matched control.
  This milestone cannot accept caller-supplied trigger hashes as evidence.
- Store that uniform assessment inventory using a versioned lossless encoding: complete member
  domain from the retained frame projections, constant state/reason, count and canonical hash
  of the expanded D042 inventory. This avoids a duplicate large JSON artefact; replay expands
  and checks the exact inventory. Scheduled assignments retain their explicit assessment state.
- Freshness is checked at actual sampling cutoff and again at the selection's durable
  acknowledgement. Use verified frame interval start (first request start, conservatively
  earlier than first receipt), last first-receipt and actual frame availability. Never substitute
  a new read receipt for source freshness. Enforce frozen age and interval duration, causal UTC
  and same-session monotonic ordering. Recovery checks the original clocks, not today's age.
- A new fresh selection from prospective source evidence may retain prospective provenance;
  synthetic stays synthetic. This is selection provenance only. Collection, origins, SQL
  admission, population inference and panel acceptance remain false.
- Reuse the bounded 1 GiB selection writer, 400,000-row/4,000-page/3 GiB raw/600-second limits
  and existing original-reader reservation. Full role/control/target capacity is rechecked
  before selection. No source requests or database access occur in this operation.

## Validation

Exercise real original-code fixture decoders; declaration-before-read and seed equality;
unknown assessments/control refusal; complete inventory/weights; stale, too-wide and future
frames; expiry while projecting or acknowledging; insufficient capacity; slot overflow without
truncation; source/declaration/plan tampering; failure preservation and concurrent ownership;
read-only recovery without re-aging; legacy regression. Freeze code and review before any
new local live measurement. A smaller-capacity frame or two-stage sample remains a separate
future protocol, not a change to the historical draw.
