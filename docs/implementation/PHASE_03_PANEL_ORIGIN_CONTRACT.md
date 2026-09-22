# Phase 3 next integration — declared panel, actual origins and due observations

Status: D048 declaration/reservation implemented and tested; collector/origin integration
remains planned. D040/D041 historical selection, D042 assessment-aware
sampling, D043 actual input reads, D044–D046 quote computation/identity refresh and D047
original computation reads are prerequisites. Phase 3 remains incomplete.

## Concrete gaps to resolve first

The saved 107-market draw is explicitly reconstructed development selection. The two-read
D046 measurement used its first assignment only as a fixed diagnostic target. Neither can
be renamed an accepted prospective panel. The next writer must declare its own protocol
before selection/collection, record actual operations and preserve all prior provenance.

Existing `select_target` requires mapping availability before origin, while a newly fetched
Gamma identity is available after origin. Target collection therefore needs the exact mapping
frozen at origin plus separately recorded current lifecycle/identity consistency checks. Do
not replace the old mapping's availability with a refresh time or backdate a new mapping.
Likewise D046 `market_closed` and other quality states cannot be passed unexamined into the
older `Quote.source_status` vocabulary. Specify and test an explicit versioned adapter that
retains original states and distinguishes known closure, invalid identity and unavailable data.

## Ordered implementation boundary

1. Reload checkpoint/master/phase, this contract, panel journal contract and the actual D046
   evidence. Inspect origin/feature/outcome contracts in Feature Store v2. Keep the generic
   prospective SQL writer closed during journal implementation.
2. Implement a frozen panel protocol and exclusive journal declaration before numerical reads
   or network calls. Pin build, permitted frame interval/age, selection policy/seed generation,
   origin cadence/delay, receipt freshness, target horizons/tolerances, source rights scope,
   feature-family availability and explicit finite budgets. Caller clocks, seeds selected
   after outcomes, arbitrary sources and provenance overrides are not authority.
3. Reserve complete costs for frame verification, each origin, matched controls and due
   observations before selection. Preserve complete discovery; refuse inadequate capacity
   rather than truncate the universe or silently drop control/outcome work. Do not launch
   another 8-GiB-output frame with insufficient disk. Any smaller finite retained-byte cap
   must be separately tested and may stop incomplete, never claim reduced-universe completion.
4. Resolve fresh selection as a new explicitly versioned operation. It may reuse verified
   frame facts only within the *predeclared* interval/age contract and at their real availability.
   Use the original decoder where needed, record actual reads and internally freeze seed before
   reading selection values. Retain old draw/weights/provenance; no in-place promotion. Record
   every unresolved/churned/closed assignment and exact sampling weights, never redraw to
   improve coverage. Category remains unknown unless separate causal enrichment exists.
5. Implement durable selection and origin intents keyed by panel, assignment/token and
   scheduled boundary. Keep scheduled time distinct from actual read/computation/origin time.
   Shared market roles must not duplicate scientific events. Only one worker owns an intent;
   torn intents become preserved failures, not rewritten successful origins.
6. Gather fixed, bounded fresh identity/book/trade primitives through the declared SourceRun
   policy. Record actual input reads and D045 computation. Origin writer consumes verified
   journals itself, binds full identity/feature/sampling closure, checks freshness again at
   actual origin freeze, and writes an immutable origin or explicit abstention. Unknown
   triggers are not measured-negative controls. No caller-supplied projection/hash alone
   authenticates evidence. No source-clock, complete-trade-window or economic-group invention.
7. Seal origin acknowledgement before any due-target request; refuse origins whose save is
   already beyond the target boundary. A separately budgeted due worker retains every attempt
   and invokes the versioned frozen-identity adapter and first-valid target rule. Pending,
   unavailable, late, closed and observed stay distinct; no carried-price fallback or sparse
   path-extrema claim. Interrupted/expired windows stay missed under their original protocol.
8. Report per-family coverage and abstentions. Price/book plumbing cannot stand in for raw
   trade completeness, pre-trade depth-normalised flow, persistent imbalance, withdrawal,
   related markets or external information. Implement those required family windows and
   durable trigger assessments before calling the full Phase 3 pilot accepted.
9. Test and commit the integration before freezing a new bounded live pilot. Freeze pilot
   timing/control/target gates before its first source request. Preserve failed and inconclusive
   runs; refine a later protocol version rather than its old acceptance criteria.

## Tests and review gates

### D048 declaration milestone refinement

Implement the immutable declaration first; no collection function is exposed. Freeze explicit
scheduled/trigger/control slot ceilings, cycle cadence, origin save/delay bounds, receipt-age
limits, frame age/interval, fixed horizon/tolerance/attempt count, source response cap and
per-source-run retained-byte quota. Generate a fresh internal random seed before numerical
reads. Reserve worst-case distinct role slots without assuming overlap, all source requests
and all D045 computation outputs, plus 1 GiB future selection output, 16 MiB original-frame
read output, 1 MiB declaration/failure space and 2 GiB free reserve. Inspect disk before writing.

An allocation is a frozen quota, not proof that existing SourceRun writes enforce it. Record
`runtime_source_retention_guard_required` and keep collection disabled. The next collector
must add/test that guard before any public use of this declaration. Reserve origin reads
as three source calls (identity/book/trades) and each target attempt as two (identity/book);
flow/window completeness remains unavailable. Use existing SourceRun per-response bounds and
D045's 64 MiB whole-computation reservation. Overlarge panels must fail capacity preflight,
not truncate scheduled/control assignments. Future refinement can reduce writer limits only
with its own tested explicit version; do not infer a smaller guaranteed quota from one small
runtime response. This milestone neither validates the frame nor accepts a selected panel.

- Policy and capacity reservation precede reads/selection/requests; reject future/late inputs,
  old selection promotion, fabricated trigger negatives and origin acknowledgement after due time.
- Exact old/new mapping consistency, mapping frozen at origin, changed token/outcome/rules,
  nullable lifecycle, source failures and explicit target-state adaptation.
- Concurrent intent ownership, repeated cadence/token idempotency, crash at every durable
  boundary, no source request before declaration or after finite stop; preserve partial files.
- Exact source/feature/sampling lineage, rational weights, full exclusion inventories,
  scheduled/trigger/control overlap and control/outcome resource reservation.
- Original-code recovery leaves old clocks and values unchanged; no DB/settings/startup imports.
- Full isolated regression, self-review, docs, coherent commit and draft PR before live pilot.

## Acceptance and handoff

This integration is complete only with verified actual origin-before-outcome causality and
immutable failed/late/closed records under frozen rules. Full Phase 3 additionally requires
its feature-family and control coverage, bounded live pilot and timing/target acceptance.
Synthetic fixtures prove software behavior only. Phase 4 remains gated. No production
migrations, deployment, scans, retention changes or external scheduler activation.
