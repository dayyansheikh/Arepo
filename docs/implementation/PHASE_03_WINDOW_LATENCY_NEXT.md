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
