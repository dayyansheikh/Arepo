# D076 next — distinguish endpoint omissions from changed economic identity

## Measured trigger for the change

D075 ran once under e27149761b1fdc73ff10915fa7a331de30d03da7. Eight Gamma HTTP 200,
six book HTTP 200 and two book HTTP 404; 41,576 raw bytes. All eight screens remain
unavailable under their committed full-mapping comparison. Original-Git recovery passed.
Raw targeted Gamma identities differ from their sampled frame identities **only** in
source_event_ids: one frame event ID versus an empty parsed list for every sampled market.
Six valid snapshot calculations (three above /three below the frozen threshold) are not
admitted triggers/controls. Preserve the old result, roots, cutoffs and original reader.
Evidence: PHASE_03_SCREENING_MEASUREMENT_EVIDENCE.json. Do not rerun the frozen attempt.

## Shortest safe implementation

1. Inspect source_parsers.gamma_identity, quote_inputs mapping projection, screening._inputs,
   origin_worker._choice and target identity checks. Preserve the old mapping hash recipe.
2. Add a small explicit versioned comparison policy that distinguishes exact full mapping,
   exact core economic identity with unavailable event membership, and changed/unknown core.
   Core must include market/condition/question/rules/resolution source, full ordered tokens
   and outcomes, labels and every other current identity field. Do not simply ignore hashes.
3. One bounded implementation option: validate the frame identity's own canonical hash; derive
   its canonical identity with only source_event_ids=[] and compare that hash against the
   authenticated current mapping_version. This establishes equality of every remaining field
   without fabricating current event IDs or duplicating source reads. Only permit this state
   when the old event list is nonempty. Preserve both original hashes and explicit membership
   unavailable status. Reject differing nonempty memberships and any core change. Empty lists
   already conflate source absence/empty in this parser: do not infer affirmative absence.
4. Freeze the new comparison policy before source collection in a new opt-in screening
   schema/version. Existing v1 defaults/replay remain exact. Add the result to measured states;
   do not change raw source identities or fill event IDs from the old frame. Membership from
   the frame remains as-of frame time, not refreshed current economic independence.
5. Apply the same explicit semantics to later new origin/target versions before a live pilot;
   current strict synthetic defaults may remain. Do not admit a new screening policy to the
   old origin/runtime silently. Window features, event grouping and selected external-source
   relevance remain separate prerequisites.
6. Tests: real endpoint asymmetry fixture (frame events present, targeted events omitted),
   full-hash equality, changed rules/question/condition/token order/labels/resolution source,
   differing nonempty events, unavailable mapping, resealed comparator/policy corruption,
   causal cutoff and original-code recovery. Synthetic fixture parity hid this actual source
   difference; add asymmetric source shapes, not broad acceptance of arbitrary mismatches.
7. Review/commit/tests/PR before collecting under the new policy. Do not reinterpret D075
   as a prospective success under new code. Any counterfactual calculation is retrospective
   diagnostic only and must use a separate output with original provenance intact.
8. Predeclare a fresh bounded attempt only after the corrected policy is tested. Reuse the
   complete frame only within its already frozen 604800-second age limit (September 28
   approximately 23:30 UTC). If expired, do not extend it silently: plan a fresh complete
   frame with measured capacity, or stop at the data gate. Preserve all failed attempts.

## Acceptance and handoff

New source-stage measurement must preserve exact sampling probabilities, full failures,
actual measurement/recovery clocks and conditional control weights. A finite screen is
still not the full Phase 3 origin/target pilot. Resume bounded pre-t0 observation and
selected-market external mapping against the measured limitations. No Phase 4 here.
