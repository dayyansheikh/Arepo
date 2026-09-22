# Phase 3 source-journal quota prerequisite

Status: D049 implemented; 1,059 full backend tests passed (167.05s), self-reviewed; no live measurement in this milestone. D048's resource reservation cannot authorize collection until actual
SourceRun writes enforce the declared retained-byte quota.

## Scope and implementation

Add an opt-in quota to SourceRun, preserving the existing default run format/semantics.
Freeze the exact quota in a separate run schema version before requests. Bound total
retained files to the explicit per-run limit (1–256 MiB), with a 64 KiB failure reserve and
2 GiB free-space reserve. Keep existing raw/request/time caps in force.

All source-journal exclusive writes must pass a task-local quota guard: session/run records,
raw responses, receipts/acks, generic parse, source-specific parse and admission records.
Count actual retained bytes recursively including failed/partial files, not only raw payloads.
Reject symlink traversal, unexpected excessive depth/file count and writes outside the
guarded root. Do not read source payloads while accounting sizes. Check before opening a
new file; preserve earlier evidence when a write refuses. No overwrite or deletion.

Use a task-local context so concurrent unrelated runs cannot borrow or overwrite each
other's budget. A failed guarded run records a small bounded failure marker using only its
reserved space, becomes terminal and rejects subsequent collection/admission. A failed
marker write must never obscure the original error. Constructor failures preserve any
partial files. Replaying a successful guarded run checks its frozen quota and actual usage.

The panel declaration remains collection-disabled until a future collector proves it
applied the declared quota, frame/source rights, selection and origin/target requirements.
No live measurement or production action is part of this implementation milestone.

## Tests and acceptance

- Successful guarded synthetic Gamma/book/trade runs and D043/D045 integration; old default
  schema still excludes the optional quota and remains bounded by its existing rules.
- Refusal before overflow, including raw, generic/source parse and admission writes; intact
  prior bytes, failure reserve and terminal retry refusal. Empty/partial attempts retained.
- Exact quota validation, rehashed policy/usage tampering, low disk, file/depth/symlink scope,
  task-local isolation with interleaved async runs, and unchanged output on read-only replay.
- No inherited application settings, database, credentials, runtime network during tests,
  deletion, shortened retention or production collection. Full isolated regression and
  reviewed coherent commit/draft PR before the next panel integration step.

Implementation scope: quotas are cooperative application write guards for one SourceRun,
not filesystem preallocation or protection against an external process changing files.
Before HTTP reserve the bounded raw response plus a 64 KiB receipt/ack allowance; every
actual write still checks its exact size and free space. Unexpected I/O failures preserve
whatever reached disk and never establish unavailable acknowledgement clocks.

Guarded v2 SourceRuns remain journal-only: the existing optional SQL index writes a receipt
back into its source root, so it refuses this new run schema before database access until
that separate writer is quota-aware. Existing default v1 indexing remains supported.
No parsing/repair writer outside SourceRun is authorized to mutate guarded primary journals.
D048 declarations still require a future collector to apply and verify these quotas.
