# Phase 3 — next measured screening/control boundary

After D066 and backend-wide recovery regression. Read checkpoint, Phase 3 plan, D042 assessment
checks, D050 scheduled-only selection, D056 runtime and D065/D066 evidence/contracts first.
Do not recollect the diagnostic or upgrade its 1s-covered/59s-uncovered result.

## Gaps established by current code

- `panel_selection.py` deliberately sets every member to not-assessed. D066 now authenticates
  individual predeclared snapshot decisions, but no selector consumes those journals yet.
- `sampling.py` assigns arm/stratum-conditional probabilities; it does not supply a global union
  probability or an automatic product weight for a newly invented screening stage.
- The preserved development selection has 107 strata and absent categories. Measuring every
  market at dense cadence is neither needed nor authorised. Complete discovery remains separate
  from a bounded sample; unselected/unassessed markets must stay in the inventory.
- The complete frame is historical. Its permissible age/interval must be declared before a new
  selection; never silently promote the old development draw. Source/execution freshness checks
  and churn/closure records are still required for every actually assessed assignment.
- Runtime remains synthetic-only. A control planner alone must not activate its live path.

## Ordered design and implementation

1. Recompute capacity from actual disk and existing reservation code before fixing the pilot
   shape. Include full-frame read/selection, every screened assessment, every possible control,
   origin and due target, failure records and recovery. Preserve the 2 GiB reserve and all raw
   history. Existing expanded frame mode cannot be launched merely because a smaller run fits.
2. Specify a new bounded screening design with nonzero inclusion probability for each eligible
   member of the declared enumerated population. Preserve full frame/unknown/excluded inventory.
   If sampling strata then markets is used to fit capacity, freeze that design explicitly and
   retain exact probabilities for both stages; do not truncate the first N strata or apply old
   within-stratum weights as population weights. Arm overlap and dependence remain explicit.
3. Freeze rule(s), finite screen slots, seed, age/interval/source budgets, matching criteria,
   control slots and due-target costs before reading screening values. D066's configurable
   snapshot rule is development plumbing; no scientific threshold or winner has been selected.
   Do not select thresholds to reproduce D065's observed imbalance.
4. A durable screening worker must own the selected assignments and D066 declarations before
   their source requests. Preserve every attempted/unavailable/unassessed assignment. A fresh
   mapping must agree with the selected market/token/rules or abstain; no alternate-market search.
5. A verified consumer must read/replay those exact journals, check target/rule lineage, policy
   before primary request start, and source/assessment age at its own actual cutoff. Preserve
   actual read/selection/durability clocks. Caller-supplied D042 hash strings are not admission.
6. Draw triggers only from verified positives and controls only from verified negatives under
   the same rule and comparison window. Unknown/unavailable never enters the negative pool.
   Preserve unfilled control slots; a quiet or one-sided sample is a measurement outcome, not
   permission to redraw or relax the rule. Scheduled arms remain separately identifiable.
7. Derive and test exact conditional weights/matching probabilities, arm overlap and market/event
   deduplication. Distinguish the screened population from the complete enumerated frame. Never
   claim repeated observations or different token outcomes are independent economic events.
8. Persist actual selected origins only after full source/feature lineage is available; preserve
   target deadlines for every arm. Integrate through a new explicit runtime version after tests,
   with original-code recovery and no automatic production/SQL/public API connection.

Required tests: exact small-population probability enumeration, all-unknown/all-negative/all-
positive and empty matched pools; duplicate/foreign/missing declarations; stale/late/future source
and selection clocks; partial-budget stops retaining controls/abstentions; source and resealed
journal tampering; single ownership; full original-code recovery. Do not spend live requests to
solve an algorithm test. Measured control coverage must subsequently pass its frozen pilot gate.

In parallel as a later independently bounded milestone, admit a feasible selected external source
with exact mapping, rights, clocks and missingness. Do not equate a generic BTC ticker with relevant
information for an arbitrary non-crypto market. Unsupported flow/pre-trade-depth/withdrawal/native
continuity families stay explicit unavailable until their own prerequisites are supported.

Exit remains the Phase 3 representative prospective pilot with measured controls, timing and target
coverage. Neither D065 nor D066 completes Phase 3. Phase 4 starts in a fresh conversation only.
