# Phase 3 — interleaved synthetic runtime (D056)

Status: implementation checkpointed; focused tests pass, full validation pending. D053 origin, D054 identity adapter and D055 due worker are
accepted software prerequisites. No live transport, SQL admission or accepted panel is enabled.

One exclusive `fs2_runtime_<panel>` owns bounded origins, target attempts and per-origin target
plans. Freeze a new runtime schema/build/policy and full D052 reservation plus 32 MiB runtime
metadata and 128 KiB per-origin plan before actual activation. Preserve standalone APIs and
old journal schemas; this runtime composes their verified per-origin/per-attempt operations.

Use one serialized priority queue. Initial origin schedules come from D052 activation.
A completed, independently verified origin permits its own target plan to be consumed and
persisted immediately; do not wait for later origins. Target offsets remain D055's fixed
formula. Queue order: scheduled UTC, target before origin on an exact tie, then immutable ID.
Ineligible target jobs are dispatched at their actual plan acknowledgement with no requests.
No outcome-driven retry/early stop, parallel HTTP burst, rescheduling or horizon changes.

Each dispatch records actual start/completion. Bind origin facts/intent to verified receipts;
freeze each target plan with actual read and durability clocks before its requests. Replay
must reproduce the evolving queue, origin/target lineage and all actual ordering. It must
reject missing, extra, reordered or duplicated work and changed identity/value/clock evidence.
Slow serialized work may miss a later window; preserve the expired/late state rather than
weakening the frozen protocol. Cancellation preserves incomplete journals and forbids resume.

Retain all old source numerical evidence. Final outcomes use D055's exact selector, complete
failure blockers and actual target-record availability. Final report has actual read cutoff,
completion and durable acknowledgement. Midpoint change remains a diagnostic only.

Test two real-clock cycles whose first target is due before the second origin; deterministic
ties; slow source latency and honest expiry; cancellation/concurrent ownership; every reserved
slot; semantic replay/tampering; source/profile budget binding and original-build preservation.
Run relevant full regression, self-review, docs, commit and draft PR before acceptance. Dense
features, measured controls, admissible external sources and prospective pilot remain later gates.

The runtime composes the unchanged per-origin and per-target writers/readers inside separate
`origins`, `targets` and `plans` directories. Replay reconstructs the evolving queue from
activation and each verified durable per-origin plan; it checks every dispatch against actual
intent/save clocks. Ineligible targets are dispatched at plan acknowledgement without source
requests. Five focused tests passed in 65.88s. Full regression and final acceptance remain pending.
