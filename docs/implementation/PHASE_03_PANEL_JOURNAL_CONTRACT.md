# Phase 3 durable panel journal — next milestone contract

Status: original-build read boundary implemented; remaining panel design only, 2026-09-21.
Read actual frame evidence before refining/implementing.
No origins, features, controls or labels are produced by this document. Prerequisites:
Phase 2 source journals, Phase 3 pure sampling/targets and a usable verified frame.

## Dependencies and admission boundary

A fresh measurement run freezes protocol parameters, seed generation, source/frame references,
budgets, target rules and both source/panel computation builds before selection or feature
collection. Synthetic transports remain synthetic. The public generic prospective writer
stays closed; a caller-supplied clock, payload or `prospective` flag cannot open the gate.
Capture/selection/feature/target operations never import application settings or invoke v1
startup, SQL migrations, scans or browser routes. Any SQL indexing remains a separate explicit
local operation with its own post-commit acknowledgement.

A frame's source-exhaustion status is necessary but does not prove an atomic global snapshot.
Freeze permitted enumeration age/interval and coverage interpretation before the pilot, retain
all churn/identity exclusions, and describe the population as the enumerated source population
over that interval. Do not retrospectively call a current complete frame available earlier.
Keep failed/incomplete frame attempts as research records but outside population inference.

## Original-build evidence consumption

Decision D034 implements mechanism 1: `research_panel/original_reader.py` extracts the
original journal-declared Python packages from an explicit full local Git commit into a
disposable directory, verifies every file hash/set and uses an isolated child interpreter.
The original decoder still checks source contracts, Python/library versions, raw/parsed/page
closure and original build identity. Current code never reparses old numerical facts.
No checkout/reset, dependency installation, source request or journal mutation occurs.
Temporary code copies are disposable; source journals and read receipts remain preserved.

`frame_cli inspect-original --journal <absolute-root> --implementation-commit <full-sha>
--output-parent <absolute-existing-directory>` creates a fresh `fs2_frame_read_*` journal.
Its policy pins original policy/report hashes, extracted code, current reader build and actual
metadata-read clock. Its receipt pins the child output and actual verification clocks after
original availability. An incomplete source frame remains incomplete; synthetic remains
synthetic; no origin or model execution is admitted by this command. A read receipt proves
this read, not that a later sampler/model consumed it. Later consumers need their own clocks.

Only sealed original reports are accepted. Missing original Git objects or incompatible
installed libraries fail closed; there is no current-parser fallback or automatic package
installation. Failure after declaration preserves partial output/failure acknowledgement and
requires a fresh read directory. The child has a 300-second timeout; returned JSON is limited
to 16 MiB and must exactly match the sealed original report plus its original acknowledgement.
Tests cover corruption, changed code, library mismatch, mutable/invalid revisions, output
inside evidence, repeated output paths and original journal/repository immutability.

## Ordered implementation tasks

1. Recheck latest frame report/limits/identity exclusions and current tests. If no complete
   usable frame exists, record the actual source/capacity blocker; do not sample the first N
   pages and describe them as representative. Resolve a finite source strategy first.
2. Define immutable panel policy/schema/version and named budgets for frame reads, scheduled
   arms, triggers, controls, dense windows and due outcomes. Reserve control/outcome resources
   before admitting origins. Use disjoint leases and make crash/retry evidence append-only.
3. Generate and seal the random seed before reading selection values. Preserve the full frame
   inventory and row/page references, including excluded/unresolved members and identical or
   contradictory repeated IDs. One predeclared source-ordered outcome per market; no favourable
   outcome choice. Never arbitrate conflicting market versions by arbitrary first/last wins.
4. Define deterministic known-at-cutoff metadata projection. Distinguish Gamma metadata price
   from a valid observed two-sided CLOB midpoint. Keep absent/invalid category, close, liquidity,
   price and source-event/economic grouping as explicit unknowns. Source event IDs are not
   proof of economic independence. Do not infer chain/collateral namespaces from defaults.
5. Record actual verified frame read start/end, projection computation, policy/sample hashes,
   selection cutoff, causal input manifest and durable selection acknowledgement. All used
   page/identity/group/trigger availability must be <= cutoff. Only then request origin inputs.
6. Use the pure sample planner under the frozen scope/strata and explicit frame-capacity limit;
   the default remains 100,000, while explicit version-2 output supports at most 400,000.
   Preserve exact rational weights,
   role overlap, matching probabilities, exclusions and unfilled control slots. Do not choose
   a smaller population or discard controls to fit a budget after selection.
7. Admit source captures through their own durable declarations. Record actual feature reads,
   computation and availability; freeze actual origin time after all origin inputs are ready.
   Scheduled boundary and actual origin must remain separate. Do not call a source-availability
   timestamp proof that the model read it. No retrospective origins from today's old data.
8. Register explicit family coverage for price/context, books, raw trades, flow, depth-normalised
   flow, persistent imbalance, withdrawal, related-market and selected external information.
   A bounded trade page does not prove a complete window; receipt timestamps do not prove venue
   ordering/pre-trade depth. Unsupported families stay unavailable, with primitives retained.
9. Seal origins/feature manifests/abstentions before due-target reads. First-valid receipt-time
   target policy applies to controls and triggered origins alike. Failed/closed/late/missed
   targets remain records. Sparse quotes cannot label first passage or exact path extrema.
10. Implement local replay/crash/concurrency tests, then freeze an actual finite pilot policy
    with timing/control/target coverage gates before its first request. No model winners or
    predictive claims; Phase 4 baseline locking is separate. An unsuccessful pilot remains
    unsuccessful under its original thresholds; refine only a subsequent version.

## Tests and exit evidence for this milestone

Test actual read-before-origin causality, future input rejection, source/panel build mismatch,
old-format handling, deterministic sampling and exact rational round trip, full frame retention,
failed controls, source/page gaps, late/missing/closed labels, lease collision, recovery after
raw/fact/selection/origin/index acknowledgement failure, and local cold copy equivalence.
Measure primitive coverage, receipt/parse/compute/origin lag, target delay, disk and memory.
Document immutable run roots, original implementation commits and all missing evidence.
These gates supplement the current phase plan; they do not mark Phase 3 complete.
