# D083 — causal pre-origin window dependency

The successful D082 snapshot pilot remains immutable. Its origins cannot be enriched after
outcomes. This contract extends future origins using the existing socket/book journals;
it neither creates a service nor admits continuous-window features.

## Input and numerical contract

`origin_window.project_origin_window` authenticates a complete `socket_analysis` dependency
through its existing reader, then verifies the retained prior book hash, provenance and
availability at the supplied cutoff. The consuming origin writer must own the actual cutoff
and authenticated current quote; this helper is not an external prospective-record API.
A socket analysis containing a separate post endpoint is refused. Original summaries,
computation/report/event hashes, actual subscription/end/availability clocks and source
mapping versions remain in a bounded16KiB projection.

Prior and current token, condition, market, outcome and complete actual mapping must agree.
Changed/unavailable identities preserve diagnostics with an unavailable history; no event-ID
exception is silently borrowed from frame-to-current screening. Both current source and
mapping must be available at cutoff. Future analysis/current evidence is an error. Stale
prior observations/windows, unavailable quotes and a current receipt before window end are
explicit reasons. Freshness is an immutable explicit `OriginWindowPolicy`, not a new clock.

The historical primitive preserves prior/current midpoint, exact rational difference and
actual receipt separation in milliseconds, with original observation IDs. It is an irregular
two-point series, not a native-clock series or locked momentum model. Phase3 recording fixtures
may serialize the current midpoint and historical change; fitting/baseline selection stays
in Phase4. Numerical conservation includes negative, zero and unavailable values distinctly.

Coverage retains declared, reconstructed-receipt and uncovered durations, exact imbalance
integral and covered-only ratios with the original hold policy. Complete native continuity,
F02/F10/F27 eligibility and feature-store admission remain false. Silence, PONGs, early closure
or matching endpoints never fill an evidence gap. Raw segments remain in the authenticated
socket-analysis journal; the compact origin projection references their exact hashes.

## Integration boundary and ordered work

First test the causal dependency projector against actual loopback/source journals, not
invented prospective records: exact arithmetic, frozen-cutoff replay, changed identity,
future/stale evidence, missing snapshots, silent/disconnected windows and tampered raw input.
Then extend only an explicitly versioned owned origin/runtime path. Existing snapshot
versions and their original readers retain their contracts.

The worker must reserve all window/analysis/verification bytes before requests and bind
exact selected-token roots internally. Use bounded concurrent pre-t0 subscriptions and real
state freezing. A caller-supplied window path alone is not prospective authentication.
Window failure retains its sampled member and unavailable state; it never redraws a market.
The origin record must preserve actual window-read start, computation and freeze clocks;
original recovery authenticates all transitive dependencies at the recorded cutoff.

This component alone does not finish D083. Runtime ownership, preflight accounting, failure
states, cancellation drainage and full original-code recovery must be integrated/tested
before a new finite public protocol is frozen. Do not repeat D082's accepted test/measurement
without a relevant new change. No production or Phase4 action is included.

## Implemented origin boundary

`fs2-owned-window-origin-v4` records an explicit canonical analysis root and immutable
`OriginWindowPolicy` in the origin intent. It is accepted only with owned activation,
feature mode and compatible actual transport provenance. The authenticated current quote
comes from the existing origin source/computation chain. The actual origin read-start clock
is the dependency cutoff; feature computation and freeze remain separately recorded.

`fs2-origin-window-manifest-v2` references the analysis hash and preserves the compact window
projection alongside the existing snapshot manifest. At actual freeze it rechecks history
and window ages and origin eligibility. Expiry keeps numerical history in the dependency
projection but removes it from eligible feature values with explicit reasons. Both the
snapshot manifest and the final window projection retain16KiB ceilings inside the existing
origin metadata quota. Cold origin recovery recomputes the dependency at the original read
cutoff and repeats eligibility at the original freeze; subsequent tampering is refused.

This is an origin-writer component, not public orchestration acceptance. The existing
concurrent runtime still expects snapshot-only origin v3. The next version must bind its
internally collected per-market window dependencies and preserve failed/missing observers,
expand the preflight reservation, route original-runtime recovery and prove bounded
cancellation/target scheduling. No caller-supplied prospective history shortcut is enabled.
