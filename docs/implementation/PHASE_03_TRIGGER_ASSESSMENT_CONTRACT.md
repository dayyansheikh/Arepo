# Phase 3 — D066 predeclared snapshot assessment

Current implementation boundary after D065. This is measurement plumbing for control eligibility,
not a validated trigger, model, Phase 4 baseline or native-clock/window admission.

D042 can check caller-supplied assessment records but cannot prove their primary sources or actual
computation. Add a durable writer which authenticates D057 book computations and their primary
request-start receipts itself. An old diagnostic may never be relabelled an assessed control.

1. Declare one market/token, intended fresh book computation path, exact rational absolute-F08
   threshold and receipt/identity age ceilings before source collection. No default scientific
   threshold; 0 < threshold <= 1. Fixtures use 1/2 to test equality/negative/positive boundaries,
   not because it is an evidence-selected parameter. Hash/build and actual declaration durability
   precede every Gamma/book request. The caller cannot supply observations, results or clocks.
2. Claim an exclusive computation child; partial failure remains terminal. Actual verified source
   reads precede computation and durability. All post-declaration primary request receipts, fixed
   request identities, book summary/raw chain and source provenance must match. No source request
   is made by this consumer; source acquisition remains an independently bounded operation.
3. Derive exact absolute snapshot imbalance from preserved numerator/denominator components.
   Triggered means >= the declared threshold; observed below threshold means untriggered.
   Failed/missing/closed/changed/wrong/stale inputs mean unavailable or refuse corrupted evidence,
   never negative. Explicitly known-active lifecycle required. Preserve signed input, absolute
   value, threshold, exact difference and all reasons, source clocks and original computation.
4. The output is a development snapshot rule, not complete-flow/persistence/withdrawal eligibility.
   Record input receipt window and actual new read/computation/durability clocks separately. An
   assessment becomes available only at its own durable acknowledgement. A later sampler must
   verify the journal and recheck age; copied hash strings are insufficient runtime evidence.
5. Independently replay at original computation time with exact source/declaration closure. Add
   original-Git recovery protecting declaration, book computation and source roots without new
   requests or changed clocks. No SQL/source/feature/origin admission is enabled.
6. Keep finite file/byte/time/free-space bounds, no overwrite/resume, concurrent single ownership,
   terminal partial writes and original evidence protection. Test future/early source clocks,
   stale/unavailable inputs, target mismatch, exact threshold equality/negative decisions, raw or
   resealed-result tampering, cancellation, collisions and original full-facts recovery.

Follow-up: authenticating these outputs into a measured screening subset/control-selection
journal with exact conditional weights and unchanged full-frame scope. The current scheduled-only
selector and synthetic runtime remain unchanged. Screening definitions, sample costs and external
source admission must be frozen before their own new collection; do not retrofit D065.

## Implemented storage and recovery

`declare_snapshot_trigger` freezes the rule/target/intended future book path in a new
`fs2_trigger_declaration_` root. `record_snapshot_trigger` exclusively owns its fixed
`fs2_trigger_computation_result` child. Three child payload/ack pairs preserve computation policy,
actual input reads (including full verified source/book facts) and exact decision facts.
Independent reading verifies parent/child closure, full dependency equality, all clocks and
original-cutoff arithmetic. `read_original_trigger_computation` preserves full facts/summary
under original Git code and creates a new read receipt outside all transitive dependencies.

Existing bounded computation storage guard: 64 MiB child, 16 MiB artifact, eight-file ceiling
including failure pair, 64 KiB failure reserve, 2 GiB free reserve, 180s processing checks.
Parent declaration is bounded by the same artifact/space guard. Both roots retain partial writes;
only complete successful closure can be consumed. No new source acquisition, sampling admission,
SQL or production path. A later sampler must authenticate this journal and check freshness at its
own cutoff; this module does not materialize caller-supplied `TriggerAssessment` as actual evidence.
