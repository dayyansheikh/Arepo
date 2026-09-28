# D075 — first bounded public screening measurement

## Purpose and sequencing decision

D068–D074 now test sampling, raw-backed decisions, conditional controls, activation, concurrent
synthetic targets and snapshot components. D065 measured a quiet stream; D073 measured an
external source. Neither has measured book availability or positive/negative control pools
in a probability sample. Measure that limitation now, before building more socket orchestration.
This is one source/screening-stage measurement, not a full origin/target pilot or Phase 3 exit.
No required window, external-relevance, timing or outcome acceptance gate is removed.

## Frozen design (must be committed before selection/acquisition)

Population is the complete **September 21 enumerated open-market frame**, not a claim about
all markets currently listed. Use only `fs2_capture_eaec9cd7e8684953952e1b683c33dd3a` under
original `41fcb0170c7d71716873847639dc181ea12422aa`. Frame age limit 604800s, enumeration span
limit 600s. Preserve all 175,427 source rows, exclusions and unknown categories. A new
sampling seed must be durably generated before reading values; never reuse the old draw.

D069 two-stage design: uniformly sample **four strata**, then **two scheduled members per
sampled stratum**, at most eight screens. Preserve the exact product inclusion probability,
all unsampled strata, singletons and shortage states. No replacement/redraw for a missing book,
changed identity, closure, one-sided pool or failed response. Do not tune on measured counts.
Conditional triggered/control weights are not a global arm-union weight.

Declare a compact-v1 panel with scheduled_slots=8, triggered_slots=8, controls_per_trigger=1,
cycles=1, target_attempts=1, scheduled_per_stratum=2, triggered_per_stratum=2,
cadence_seconds=120, max_origin_delay_seconds=60, max_origin_save_seconds=5,
horizon_seconds=60, tolerance_seconds=5, max_frame_age_seconds=604800,
max_frame_interval_seconds=600, max_quote_age_seconds=60, max_identity_age_seconds=180,
source_response_bytes=65536, source_run_retained_bytes=1048576, strata_limit=4.
Origin/target values are future reservations only; this measurement creates no activation,
origin or due schedule. Subsequent observation stages need a new full combined reservation.

Screening rule: exact absolute F08 snapshot imbalance >=1/3, max_age_ms=60000. This is a
predeclared engineering measurement rule, not a selected predictive winner. Freeze screening
window and assessment maximum ages at 120s; do not reinterpret stale values after the result.
One matched negative per positive where the existing stratum/role planner permits it.

Use bounded concurrency four and the existing immutable screening worker. Each selected member
owns exactly one targeted Gamma request and one token book request, at most **16 requests**
for the entire measurement; 15s/request, 60s/source run, 64KiB/response and 1MiB retained/source.
No retries, alternate source, URL, credential, replacement market, source search or paid service.
The worker enforces its existing 1800s acquisition /7200s total guard, per-child caps, full
screening plus future control/origin/target/recovery reservation and 2GiB free reserve.
Before declaration, calculate that full reservation from the frozen protocol and verify actual
free space. Do not delete evidence or launch if capacity is insufficient.

Roots, each exclusive and terminal:
- panel: `data-dumps/fs2_panel_screening_measurement_20260928_1`
- selection/worker: existing deterministic siblings derived from that panel name
- all decisions/books/raw responses: existing worker-owned paths

Run once only after new public entry point, provenance refusal tests, self-review, coherent
commit and draft PR update. Public entry point has no transport parameter; the existing
synthetic API continues to require MockTransport. Public source mode requires prospective
frame/selection lineage and pins its actual loaded build to the implementation commit before
any request. Synthetic or reconstructed assignments must fail before public acquisition.

## Evidence and interpretation

Report assigned/attempted/observed/failed/stale/closed/changed counts, positives, negatives,
unknowns, matched/unfilled controls, actual acquisition/assessment spans, source bytes and total
retained cost, frozen rule/seed/probabilities and original-Git replay result. Preserve all raw
numerical/clock/provenance evidence. Original screening recovery verifies the full dependency
closure. Do not repeat accepted historical validations as standalone extra reads.

Eight or fewer members do not establish predictive power, representative current-universe
coverage, full matched-control coverage or an accepted panel. Empty/ineligible pools are a
useful measured limitation, not permission to retune thresholds or relabel unknowns. Use the
result to choose the next prospective protocol, preserving this attempt unchanged. Then resume
pre-t0/window and selected-market external mapping integration toward the full bounded pilot.
