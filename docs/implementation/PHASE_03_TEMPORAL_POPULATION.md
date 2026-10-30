# D096 — prospective deep-sample population

D094 selected two contracts whose stated end preceded frame acquisition. They then returned
closed/nonaccepting identities and absent books. An expired stated endpoint cannot support the
intended future-target measurement. A new, explicit population policy addresses this measured
mismatch; it does not repair D094 or waive its failed6/8gates.

`scheduled_end_after_selection_declaration_or_unknown_v1` is frozen in declarationv4 before
selection's original-frame numerical reads. Selectionv3/planv3 applies the original metadata
close band at the actual selection declaration clock, before sampling. Mapped members with
`close_stratum=past` (endDate<=reference) have an explicit exclusion reason. All raw rows,
identity failures, metadata, past members and their hashes remain in the complete inventory.
Unknown/invalid dates stay eligible; one-sided books are not filtered. Legacy defaults and
previously recorded plans are unchanged.

This changes the target population, not discovery completeness. Inclusion probabilities are
conditional on the stated future-or-unknown endpoint population. Do not generalise them to all
mapped markets; temporal exclusions have zero inclusion under this design. The plan names the
population and reference clock, retains explicit exclusions and mapped-versus-eligible counts.
It uses no prices, outcomes, new source payloads or caller-injected reference clock for the
eligibility decision. Exact stage/within-stratum probabilities are recomputed before collection.

endDate is metadata, not proof of actual closure or trading activity. Postponed-but-open markets
with old endDate are outside this new population. Missing/incorrect metadata can still cause
unavailable targets; an endpoint after declaration can expire during processing. Current source
identity/lifecycle and all actual origin/target clocks remain independently binding. No margin,
threshold or outcome-dependent resampling is added. A finite measurement must report these
limitations and all unavailable members, retaining the unchanged acceptance thresholds.

Validation:101 targeted declaration/bound-selection/bounded-sampling/new-policy cases passed
56.63s; one additional full synthetic owned origin/control/target/original-runtime audit passed
20.85s. New tests cover unknown/invalid metadata, retained unresolved identities, exact weights,
all-past empty populations, unmutated defaults, tamper refusal and original-code recovery.
Logs /tmp/arepo_d096_tests.log and /tmp/arepo_d096_runtime.log. Explicit isolated SQLite,
AUTO_MIGRATE=false, email disabled. Ruff/backend, canonical and whitespace checks pass.
Self-review: opt-in version dispatch, population labels, exclusion denominators, unchanged
raw source inventory, immutable clocks/seed, full cold/original replay and bounded collection.
Synthetic success is not prospective acceptance. No production/SQL/scheduler changes.
