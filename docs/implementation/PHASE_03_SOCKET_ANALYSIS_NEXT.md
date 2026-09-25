# Phase 3 — socket receipt diagnostics and post-window integration

Status: implemented by D064; see PHASE_03_SOCKET_ANALYSIS_CONTRACT.md and the final validation in PHASE_03_REVIEW.md. Items 1–6 are the accepted software scope after those checks pass. Item 7 remains a separately frozen diagnostic gate. Do not recollect accepted historical evidence.

1. A new versioned durable consumer reads a completed D063 socket journal, its verified prior
   computation and optionally one separately collected post-Gamma/book computation. Preserve the
   exact socket report/metadata/raw/ack chain and actual receipt versus append clocks. The new
   output root must be outside every transitive socket/pre/post computation/raw-source root.
2. Freeze coverage/age/separation policy, loaded build and finite output limits before actual
   reads. Save actual input-read start/end, input durability, calculation start/end and result
   durability. Never supply caller facts, clocks or a replacement provenance label. Keep old
   synthetic D058–D061 formats, hashes and source-admission guards unchanged.
3. Reuse exact D059 receipt reconstruction arithmetic through an explicit new adapter for verified
   D063 events. Preserve raw frame/element hashes and actual acknowledgement availability. Process
   only successfully returned received payloads. Socket-rejected bytes remain unavailable; failed
   or early-ended intervals cannot acquire an invented end state. Refusal before subscription has
   no numerical window and no fabricated start/end clock. Preserve native continuity/fill gates.
4. Reuse the D061 exact endpoint calculation with an authenticated new input envelope, not by
   relabelling a legacy synthetic source. Retain source-local identity/rule availability from the
   prebinding, socket report acknowledgement as conservative post-request boundary, all original
   request-start receipts, post freshness/closure/failure/identity mismatch and exact offsets.
   Match all provenance classes; a loopback source remains synthetic. Missing post evidence is
   explicit unavailable and never triggers an implicit request. A successful close or endpoint
   match cannot erase gaps, admit a feature or imply full-book equivalence.
5. Fully re-read/replay dependencies and calculations at original cutoffs. Include whole coverage
   facts and exact reconciliation, not just a convenient scalar. Original-Git recovery protects
   dependencies and preserves full facts/summary and old clocks. Fixed artefact/file/whole/free/
   processing bounds and terminal partial-write/cancellation/concurrency rules remain mandatory.
6. Tests: real loopback pre/window/post chain, exact coverage/components and endpoint disagreement,
   post request initiated too early, stale/changed/closed/missing post evidence, unsubscribed
   refusal, invalid/early tails, mixed provenance refusal, raw/source/clock/result corruption,
   partial persistence, resource limits, original-code recovery and all affected legacy paths.
7. After tests, self-review and commit, freeze one finite public diagnostic separately: explicit
   fixed market/token, fresh pre-Gamma/book, <=60s socket, post requests only if pre/window status
   permits, exact capacity/storage/time budget and report destination. Public collection is not
   enabled by this contract. Recheck free disk and read rights/source limitations. A closed/failed
   fixed target is retained without target search. No measured controls/pilot acceptance inferred.

After diagnostic semantics are measured, resume family/control/external-source and representative
pilot gates in the Phase 3 plan. Phase 4 begins only in a fresh Codex conversation after genuine
Phase 3 acceptance. Production and all other protected boundaries remain untouched.
