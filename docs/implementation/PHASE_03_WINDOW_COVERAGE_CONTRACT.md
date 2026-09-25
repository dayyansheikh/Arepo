# D059 — decoded receipt-window diagnostics

Status: implemented, self-reviewed and accepted as a software milestone; 90 affected tests passed. Source is a successfully verified D058 synthetic window,
including a cleanly sealed incomplete window. This does not admit live data or F02/F10/F27.

Freeze a new decoder policy and build before actual source reads. Record read start/completion
and durable acknowledgement, then separate computation start/completion/availability. Recheck
source closure, exact report, event hash chain, raw hashes and source acknowledgements at
consumption. Preserve original clocks. No supplied payload, cutoff, seed or provenance override.
New output is exclusive fs2_window_computation_; old window/quote/origin formats are unchanged.

Decode text JSON objects or arrays with strict duplicate-key/nonfinite rejection. Keep raw
frame/element pointers and hashes for every item, including unrelated, invalid, unsupported,
control, late and truncated input. Binary frames remain uninterpreted. Exact PONG is control;
it cannot refresh book age. Bound arrays to 100 elements/frame, 10,000 total items and 10,000
levels/state; retain the original raw evidence on any numerical budget refusal. Existing D057
256-digit/absolute-exponent limits apply before rational arithmetic. No array truncation.

Use exact BookReplay state only for matching source-local token/condition, with snapshot-before-
delta and immutable earlier gap inventory. Unparseable or possibly relevant unsupported input,
identity mismatch, invalid book or inconsistent best-price assertions invalidates state until
another valid snapshot. Proven unrelated messages do not invalidate the selected book. A trade
or tick message is retained separately, not substituted for a quote or proof of execution
reconciliation. Repeated numerical states do not become independent changes. Array elements
share one receipt clock; ordering them creates no extra elapsed duration.

Segment the declared interval using monotonic receipt time and an explicit frozen receipt-hold
ceiling (1–60,000ms). Initial delay, invalidated/stale state and early terminal tail are uncovered.
Out-of-interval frames are retained but cannot alter interval state. A final source snapshot or
heartbeat cannot backfill prior gaps. Preserve exact F08/F09 snapshot diagnostics and the rational
imbalance-times-nanoseconds integral, covered duration, uncovered duration and covered-only mean.
Instantaneous/mean zero remains observed zero; division by zero is unavailable. These are local
receipt reconstruction diagnostics, not native event-time coverage or the registered F27 ratio.
Native age/sequence, causal external identity, complete fills and collateral remain unresolved.

Retain raw state-changing input through primary source references, exact numerical intermediates,
state hashes and all point/segment membership. Avoid duplicating every full book per update;
replay must reconstruct it from the preserved raw snapshot/delta chain. Parser/schema/build
versions and raw pointers make this auditable. SQL/origin/feature admission remains false.

Bound the new output to 64 MiB whole, 16 MiB per artefact, six ordinary metadata files plus two
failure files, 64 KiB failure reserve, 180-second checked processing and 2 GiB free reserve.
The source journal is immutable and accounted independently; do not copy or delete it. Verify
successful closure and recompute exactly at the original calculation cutoff. Original-Git
recovery is required before a real measured consumer run.

Tests: exact rational arithmetic, mixed/array/control/unrelated frames, zero duration between
batched messages, duration versus update weighting, stale/initial/gap/early-tail coverage,
identity conflict, unsupported relevant message, snapshot recovery, crossed/one-sided/duplicate
levels, best-price mismatch, native metadata retention, numeric/array budgets, no future input,
actual read/compute/save order, cancellation/partial writes/concurrency, source/report mutation,
exact cold/original-code replay and affected prior-window regression. No network or production.
