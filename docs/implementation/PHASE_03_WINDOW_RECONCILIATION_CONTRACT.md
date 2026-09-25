# D061 — post-window request chronology and endpoint diagnostics

Status: implemented, self-reviewed and accepted as a scoped software milestone: 63 affected tests passed.
This implements steps 4–6 of PHASE_03_WINDOW_IDENTITY_NEXT.md. It does not enable a live socket,
registered window feature, origin, SQL admission or accepted prospective panel.

Consume a verified D060 bound window, its original D057 pre-computation and a separately
collected D057 post-computation. Freeze the exact comparison policy and build before actual
reads. Preserve read start/completion, input durability, calculation start/completion and report
durability separately. No caller values, observation clocks, identity or provenance overrides.
Only synthetic evidence is currently admitted by this software path.

For every post-source row, verify its primary capture receipt, hash, request and raw lineage
against the verified source-run/input projection. The request must start at or after the bound
window report acknowledgement. Response receipt after that boundary is insufficient: a request
started during the window remains ineligible even if it returns afterward. Preserve both the
raw window's earlier terminal clock and the conservative report-ack boundary. Missing/failed
Gamma or book responses, changed request target, ordered mapping/rules or lifecycle, closed and
stale evidence remain explicit reasons. An expired pre-binding is never comparable. Keep the
original mapping availability; new evidence cannot backdate or replace it.

The frozen policy specifies post-source receipt-age and endpoint-separation limits (0–300,000ms)
and a receipt hold (1–60,000ms). These are engineering diagnostic limits, not validated native
venue ages. Age is checked at the actual calculation start; the report has a separate availability
clock. Recovery uses those original clocks, never current time.

Replay the verified raw window with D059. Compare only best bid/ask prices and sizes: original
pre-snapshot versus first observed stream snapshot, and valid retained end state versus the
post-snapshot. Preserve exact reduced rational values/differences and receipt-time offsets.
The first stream snapshot is not a fabricated state at subscription time. An invalid/stale/early
terminal tail has no end value; do not fall back to a last good quote. Agreement is endpoint
agreement only. It does not imply equal full depth, native sequence continuity, complete fills,
economic independence or repaired intervening gaps. Keep the original coverage hash and uncovered
duration. Raw strings, zeros, all levels and failed responses remain in primary dependencies.

Exclusive output fs2_window_reconciliation_ lies outside every transitive bound-window,
pre/post computation and raw-source root. No overwrite/resumption. Reserve 16 MiB plus 2 GiB
free space; at most 4 MiB per metadata artefact, six success files, two failure files, 64 KiB
failure allowance and 180-second operation-boundary processing checks. Existing sources are
read and verified, not copied or deleted. Partial writes and cancellation are terminal evidence.
Full replay validates dependencies, exact calculations, clocks and closure. Original-Git recovery
compares the complete report and protects every dependency against nested output.

Required validation: a real synthetic delayed request with start before/window report before
response, changed rule/token/market/closure, failed/missing source pair, stale endpoints,
disagreement, invalid/early tails, original-time recovery, corruption/resealed changes,
concurrent ownership, partial acknowledgement/cancellation, path and capacity limits.
Synthetic passing tests do not satisfy empirical Phase 3 acceptance.

Next implement/test the separately frozen bounded public socket adapter (steps 7–8), then
measured trigger/control and selected external-source admission followed by the representative
prospective pilot. Phase 4 begins only in a fresh Codex conversation after genuine Phase 3
acceptance and durable handover; no Phase 4 work belongs to this task.
