# D086 — remove measured causal-path replay delay

D085 is terminal, failed and immutable. Its original-code audit passed;276 artifact hashes/
sizes independently match. Three observed origins have three valid targets and one observed
matched pair; four members had unavailable pre-books, one later quote became one-sided.
Four10s socket intervals completed. Three cover1s under the frozen receipt hold policy;
the fourth covers4.196189209s. These are receipt diagnostics, never venue continuity.

No history was eligible: window ages at origin read were67.367183–103.429699s against60s;
freeze ages76.409882–109.514748s. Prior quote ages at freeze121.217612–155.643060s exceed
120s. Raw facts and missingness are preserved. Do not relax those limits or rerun this draw.
All selected questions concerned esports/football; the old KNYC observation is unrelated.
Current event membership/economic grouping remains unresolved, not silently inferred.

## Measured intervals and inspected code

Quote receipt to actual subscription:34.008859–36.526592s. Window end to owned entry completion:
7.451595–21.183505s. Last entry completion to runtime declaration:19.524143s. Runtime declaration
18:30:00.294100UTC preceded screening availability18:30:08.393151UTC and scheduled origin
boundary18:30:19.021949UTC. Later origin queue/replay adds further delay. These are measured
intervals; attributing every microsecond to one function would require profiling.

Code inspection identifies redundant cold reads on the live path: owned_windows.read repeats
all already-produced book/socket/analysis recovery before activation; origin_window projector
replays the complete dependency again at each origin. Existing writers already return verified
results. Cold/original readers must still perform full verification. D079–D081 use process-owned
proofs to keep full-population replay off this path; apply that established pattern narrowly.

## Ordered next action

1. Implement an internally minted, bounded immutable window receipt/context from actual writer
   outputs. Worker acquisition owns selected roots and returned results. Do not accept caller
   payloads/hashes/clocks as a prospective shortcut. Bind persisted entry hashes and all actual
   availability; never backdate reads or turn later replay into earlier knowledge.
2. Use this context on the live worker/runtime path instead of owned_windows.read's full replay.
   Retain identical cold/original replay and byte-for-byte result equivalence. Test substitution,
   missing-member retention, byte bounds, post-capture mutation, source provenance and original
   recovery. Keep the frozen freshness checks at actual read AND freeze.
3. If measured remaining delay requires it, bind the already-verified compact numerical inputs
   to the origin writer through the same private ownership mechanism. Preserve actual current
   quote identity and exact arithmetic; audit recomputes from original raw evidence. Do not add
   a cache keyed only by root/hash that any caller can populate or disable integrity checks.
4. Compare bounded8-member synthetic timing and actual call counts against the old causal path
   before freezing another finite empirical protocol. A scalable persistent pre-t0 subscription
   with an actual causal freeze is an alternative if measured delay still demands it; do not
   build it speculatively or keep restarting duplicate observers to hide latency.
5. Separately review unavailable-book prevalence against source lifecycle/quote evidence.
   No redraw, denominator substitution or threshold tuning. A future eligibility definition
   must be declared from causal source evidence and retain full-universe/frame inventory.
   The latency repair alone cannot turn D085's three observed markets into six.

No new public collection until this scoped repair is tested/reviewed/committed and a separate
protocol is frozen. Phase3 remains incomplete; production and Phase4 stay closed.

## Narrow ownership design for the next implementation

Prefer extending owned_windows.py rather than a new service. A private factory, called only
by the actual owned screening worker after frozen selection, can return per-index acquisition
and finish closures. Freeze a bounded canonical copy of the selected assignments, worker
policy hash/build and configuration. Each acquisition closure calls the real existing writer
and captures its verified return plus persisted entry acknowledgement inside private state;
finish must refuse missing, duplicate or substituted members. It accepts no caller results.

Before reusing that proof, verify unchanged policy/build and a bounded byte/hash manifest of
all actual immutable pre-book/source/socket/analysis dependencies, including expected absence
for unavailable windows. Hash verification is not a substitute for initial parser verification:
only real writer outputs can mint the proof. Full cold/original readers continue replaying
all sources and formulas. Require warm/cold output equality and post-capture mutation refusal.

Test call counts without replacing protected functions (profiling was used in D079): no
owned_windows.read full replay before source/origin/target completion on the warm path;
cold/original recovery still invokes it afterward. Add missing/duplicate slot, mutation and
reservation/cancellation regressions. This first repair only removes the measured pre-runtime
replay interval; measure remaining latency before deciding on deeper origin projection reuse
or persistent observation. No new empirical attempt is frozen by this note.


## D086 implementation boundary (2026-10-05)

Steps1–2 implemented: the owned worker freezes private bounded assignments and acquisition/
finish closures. Actual collectors populate each slot once. Pre-book/source bytes are sealed
before acquisition and checked afterward; socket bytes are sealed before the analysis writer
verifies them. Entry and analysis hashes/results bind the writer output before reuse. Bounded
streamed manifests cover directories, files and expected window absence, reject symlinks and
mutations, and are rechecked before activation. No caller payload or persisted context mints
this proof. Missing members remain explicit. The existing full cold/original reader and all
read/freeze freshness checks remain in force; no output schema, empirical threshold or limit
was relaxed. Collection still uses one bounded observer per selected token.

Nineteen scoped tests pass in338.88s, including the profiled full runtime/original recovery:
full owned_windows.read occurs only after all14 synthetic HTTP calls. Two additional
verification-to-proof mutation cases passed in38.92s (21 scoped cases total). No public collection ran.
Next measure the eight-member synthetic causal path under the committed implementation;
compare owned finish with post-target full cold replay on the same retained evidence, report
that comparison's timing/order limitations, and inspect remaining origin freshness/queue costs.

Separate retained-evidence review: PHASE_03_WINDOW_AVAILABILITY_REVIEW.json verifies eight
Gamma payload hashes. All four unavailable D085 pre-books accompanied closed=true and
acceptingOrders=false at their actual screening receipts. This is stale frame lifecycle, not
proof of a transport defect. Keep D085 unchanged. A future frame/eligibility design must be
frozen before a new draw, retain the complete universe and unknown/excluded states, and must
not relabel this failed panel or substitute its denominator. No future draw is authorized by
this review alone; the finite protocol gate above still applies.

## D086 eight-member result and next action — 2026-10-05

Implementation531c3c38b511069e1c2a5d13d9766f9385cfe2e6. Finite synthetic measurement
`data-dumps/fs2_synthetic_latency_20261005_1` is terminal and must not be rerun/resumed.
Eight10s windows retained; activation refused stale screened roles before any origin/target.
No public request, complete runtime audit, predictive evidence or Phase3 acceptance.

Saved context equals complete post-failure cold replay. Last entry durable availability to
runtime declaration0.622521s; cold replay29.326286833s. This is an observed handoff interval
versus later replay, not randomized A/B or isolated CPU timing. First-batch windows already
81.319464–81.385908s old at declaration (limit60s); second batch22.160243–26.437577s.
Prior quotes49.88355–113.198221s old then; further activation processing caused the stale-role
refusal. These clocks show remaining acquisition/analysis delay; the handoff repair alone is
insufficient. The wrapper lost in-memory profiler timings on exception; those are unavailable,
not reconstructed. Full script, failure trace, clocks and artifact hashes are retained in
PHASE_03_WINDOW_LATENCY_EVIDENCE.json. First extraction needed a tagged-UTC decoding fix;
final independent cold/context equality and evidence extraction passed. Raw runs unchanged.

Exact next action (D087): read this evidence, then make one bounded local read-only CPU/call
profile of existing pre-book/binding/socket-analysis verification over the retained synthetic
inputs. Persist profiling output even on failure. Quantify repeated build/source replay and
queue costs before choosing the smallest repair (owned verified inputs, or persistent/sharded
observation with a causal freeze if required). Keep existing60s/120s freshness, full original
recovery, one observer per token unless measured reliability justifies duplication, complete
population inventory and explicit missingness. Do not repeat accepted21 tests without changes.
No new public run until the repair and separately frozen lifecycle/frame protocol are ready.
The four closed D085 markets remain in their failed draw; no retrospective filtering/redraw.
Phase3 stays incomplete, Phase4 only in a fresh conversation after genuine acceptance.

## D087 — measured compilation overhead and bounded expectation cache

Read-only cProfile of retained D086 member000: pre-book487130500ns, with162 compilations
consuming363913126ns; socket analysis2013804375ns, with666 compilations consuming1541182456ns.
Profiling overhead included; not an end-to-end or empirical market measurement. Full script/
results: PHASE_03_VERIFICATION_PROFILE.json. Evidence supports a small verifier optimization
before new observer infrastructure.

Cache at most256 immutable expected-code tuples keyed by exact source bytes AND filename,
with a lock for concurrent first use and LRU eviction. Do not cache successful verification:
every call still hashes current package files, checks the import-time build, checks actual
loaded functions and reads dependency versions. Changed bytes/paths never reuse expectations;
warm function replacement still fails. Output schema, numerical/source recovery and all causal
clocks/freshness remain unchanged. This is not an owner-tamper security boundary.

76 targeted tests passed119.88s: research_build_cache, feature_store_source_run,
research_panel_frame, research_panel_owned_windows, research_panel_window_context. Includes
cold/warm compile counts, mutation after warmup, source byte changes, key separation, threads,
eviction, public override refusals, missingness, cancellation and original-code recovery.
Ruff/backend, canonical and whitespace checks pass. Self-review covered cache mutability/
bounds/concurrency, freshness and unchanged per-call code/file checks. No public request.
Next: one fresh eight-member synthetic measurement at fs2_synthetic_latency_20261005_2,
script /tmp/arepo_d087_benchmark.py, after commit. Same4 workers,10s windows,60s window/120s
history freshness; preserve timing even on failure. Failed D086 roots remain untouched.
