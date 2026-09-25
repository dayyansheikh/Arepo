# D060 — pre-subscription source identity binding

Status: implemented, self-reviewed and accepted as a scoped software milestone: 17 new plus 52 existing affected tests passed. Scope is the synthetic binding/collection boundary.
This implements steps 1–3 of PHASE_03_WINDOW_IDENTITY_NEXT.md. Post-window comparison and
live socket admission are still separate requirements.

`capture_bound_window` consumes a verified D057 book computation with exactly one observed
Gamma selected-market lookup and one observed book. It accepts no replacement market/token/
condition/payload/clock/provenance argument. The selected identity, ordered outcome, mapping
version (including rule lineage), lifecycle and original availability come from verified facts.
Closed, malformed, missing, numerically ineligible or stale inputs do not start a child window.

Freeze an exclusive fs2_bound_window_ policy before numerical reads. Preserve actual read
start/completion, pre-computation receipt and durable binding acknowledgement. Require explicit
quote/identity receipt-age ceilings of 0–300,000ms at read completion and binding durability.
These are development engineering policies, not measured venue latency or validated freshness.
Only synthetic pre-evidence plus an exact SyntheticWindowFeed is supported in this version;
prospective or mixed provenance cannot be promoted through this path.

Derive the D058 child token and condition from that binding. Require the binding acknowledgement
to precede child declaration and actual subscription. Reassess freshness at original subscription
time; record identity_expired_before_subscription when processing delay crosses the limit.
Keep all earlier bytes/clocks unchanged. This synthetic late run is ineligible; the future live
adapter must also gate before sending on the socket. No origin, SQL or registered feature is
admitted by a fresh binding or a successfully elapsed raw window.

Reserve 40 MiB for the whole new parent including its unchanged 32 MiB child, at most 2 MiB per
parent metadata file, six ordinary metadata files, two failure files and one child directory;
retain 64 KiB failure allowance and 2 GiB free space. Processing checks bound 180 seconds at
operation boundaries. Pre-existing book/source evidence remains separately bounded and retained,
not copied or deleted. Canonical output must lie outside both transitive pre-evidence roots.
One concurrent writer owns the fresh directory; failed/partial/cancelled attempts never resume.

Full recovery recomputes the original binding from source facts, validates read/save/subscription
chronology, child identity and original freshness, and compares the exact report. Original-Git
recovery protects the parent, pre-computation and original raw-source directories from nested
output. It never re-collects the source or re-evaluates freshness against today's clock.

Tests cover actual ordering/identity derivation, closed/stale refusals, delayed subscription,
changed source/identity/child/report, path/argument restrictions, missing binding acknowledgement,
concurrent ownership, cancellation retention, storage/time bounds and original-code recovery.
No real source requests, production changes or scientific evidence are part of this milestone.

Next implement steps 4–6: verify separately collected post-window requests against actual primary
receipt request-start clocks, preserve original mapping availability and report endpoint values/
agreement/disagreement without repairing earlier gaps. Then test the separately frozen live
adapter before any real measurement. All Phase 3 acceptance gates and Phase 3-only scope remain.
