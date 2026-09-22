# Phase 3 source-journal quota prerequisite

Status: planned. D048's resource reservation cannot authorize collection until actual
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
