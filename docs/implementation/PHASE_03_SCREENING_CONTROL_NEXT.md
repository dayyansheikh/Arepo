# Phase 3 — measured screening/control integration

After D066 and D067 regression recovery. D068 implements the declaration and authenticated consumer described below; the bounded source worker and origin integration remain. Read checkpoint, Phase 3 plan, D042 assessment
checks, D050 scheduled-only selection, D056 runtime and D065/D066 evidence/contracts first.
Do not recollect the diagnostic or upgrade its 1s-covered/59s-uncovered result.

## Gaps established by current code

- `panel_selection.py` retains the original all-unassessed first-stage draw. D068 consumes its
  exact selected members into a separate predeclared screening journal, authenticates D066
  decisions and calls the existing sampler for conditional trigger/control roles. The original
  selection and complete inventory remain unchanged; no live collector or origin admits these roles yet.
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


## D068 implemented boundary

`screening.py` owns a bounded batch of 1–256 selected markets. It verifies the complete fresh
selection before declaring a random second-stage seed, exact snapshot rule, freshness limits,
all assignments and deterministic future D066/book paths. Every D066 declaration follows that
acknowledgement and precedes its own primary source requests. The screening journal reserves
64 MiB of metadata plus 96 MiB per decision (64 MiB result and two 16 MiB declaration artefacts),
with the existing 2 GiB free reserve. This is **not** the full collector reservation.

Completion has one exclusive intent and actual cutoff/read/compute/save clocks. It authenticates
source-backed D066 decisions, matches frame mapping/rule versions and provenance, then retains
measured negatives, positives, unavailable and unassessed states. Missing result roots remain
unassessed; torn/corrupt results refuse completion. Later additions cannot alter a sealed batch.
Partial screening keeps scheduled assignments and unfilled control slots; no automatic redraw.

The first-stage inclusion probability stays on each assignment. Second-stage inclusion and
matching probabilities are conditional on the screened sample and measured states; no global
arm/union weight is invented by multiplying them. All scheduled first-stage members remain in
the resulting plan. The result is development measurement plumbing, not an admitted origin,
representative live pilot or validated edge. Full original-code recovery protects selection,
frame, panel, declarations, books and their sources.

## Exact next implementation work

1. Add one bounded worker around existing SourceRun → book computation → D066 → D068. Freeze
   source paths, response/request/time quotas and the *whole* source/book/assessment/recovery/
   origin/control/target reservation before requests. Consume only the owned assignments;
   preserve failure/unknown states and never search for replacement markets.
2. Before activation, prove the selected role counts fit the frozen panel reservation. D068
   produces a conditional research plan, not resource admission. Its roles may overlap but
   cannot spend an assumed overlap discount. Existing one-per-stratum sampling cannot produce
   within-stratum matched controls from that screen; predeclare an adequate future sample.
   Inspect current capacity and existing protocol before choosing its shape. Do not silently
   truncate strata, reinterpret historical draws, or introduce a new sampler unnecessarily.
3. Integrate a versioned activation/runtime that actually consumes the verified screening roles
   and keeps the existing immutable origin/target deadlines. Preserve all causal checks,
   finite budgets and original-code recovery. The current runtime stays synthetic-only.
4. Freeze and commit a scientifically explicit public pilot protocol before any collection;
   include selected external information and honest unsupported family states. Measure actual
   controls, origin/target timing and coverage against its predeclared gate. Phase 3 remains
   incomplete until that empirical acceptance passes; Phase 4 remains a fresh-chat task.


## Capacity finding and next design — 2026-09-27 (not implemented)

Read only the already accepted historical selection plan for sizing: 107 strata, 98 with at
least two members and nine singletons. Two per stratum would select 205 markets. Current free
space was 27,055,919,104 bytes. D068 declarations/results (96 MiB each), existing book outputs
(16 MiB each) and two original-reader output ceilings (16 MiB each) alone imply 205 ×144 MiB,
plus 64 MiB batch metadata and 2 GiB reserve: 33168556032 bytes, before source captures,
frame/selection, origin/control/target journals and recovery metadata. The unrestricted shape
therefore cannot be promised within current capacity. These are historical sizing facts, not
a new sampling draw or empirical pilot. No history was deleted or revalidated.

Use a versioned bounded two-stage stratum draw to retain the existing matching dimensions;
do not coarsen or truncate them to evade the limit. Predeclare a cap L, uniform without-
replacement stratum selection, and up to two scheduled markets per selected stratum before
source assessment. For T eligible strata and N eligible members in a stratum, preserve both
stage probabilities and the exact first-stage market inclusion:

    min(L,T)/T × min(2,N)/N

All eligible members retain a nonzero chance, including unknown strata; all unsampled strata,
full inventory and singleton/unfilled-control outcomes remain explicit. D068's later matched
roles still have only conditional probabilities, not an invented global arm weight. A 32-stratum
cap (at most 64 screens) is a sizing candidate, not a frozen public protocol: settle it only
with the complete enforced source/book/recovery/origin/control/target reservation. Keep all
numerical covariates and current matching fields. Never reuse an old draw as a fresh selection.

Implement this as a small versioned extension of the existing sampler/declaration/selection,
with legacy hashes/readers preserved; no new service, database, queue or storage system. Test
small-population exact inclusion, T<L, singletons/unknowns, reproducibility, no future inputs,
full inventory, resource overflow, and original-code recovery. Then connect D068, the bounded
source worker and verified-role activation. This resolves a required sampling/resource gate,
not an optional infrastructure project. Do not spend public requests before these boundaries
are tested and the full pilot protocol committed.


Runtime timing finding: current activation gives every market in a cycle the same scheduled
UTC boundary (activation.py, _summary). The serialized runtime orders jobs by that boundary,
so a large initial batch can keep dispatching already-due origins ahead of a subsequently due
target. The next versioned activation must predeclare market offsets and a finite dispatch
budget, or otherwise prove the queue meets the frozen target tolerances at the chosen size.
Test multi-market source/computation delays and target-before-origin ties before the public
pilot. Do not simply widen deadlines after observing misses or alter old schedules. This is
an existing timing-acceptance requirement, not a request for new hosted scheduling infrastructure.

## D069 implementation and current next action

The bounded stratum draw is implemented in sampling/panel declaration/selection and accepted
by the D068 screening reader. Each selected assignment and every stratum report retain exact
stage probabilities; unselected strata remain `stratum_not_sampled`, never exclusions. Full
inventory/recovery stays unchanged. Default legacy schemas remain unchanged. The old activation
rejects the new selection version. This resolves the sampling design prerequisite only.

Next implement the bounded source worker with whole source/book/assessment/recovery plus
origin/control/target reservation. Then consume authenticated roles in a versioned runtime.
Do not select a public cap until that complete reservation fits actual capacity. The panel
remains a pilot/validation mechanism, not the final ML dataset.

Current user observation guidance supersedes any interpretation of the timing note above as
requiring artificial staggering: prefer persistent pre-t0 subscriptions, bounded concurrent or
sharded observers and causal state freezing when appropriate. Duplicate observers need measured
reliability benefit. Preserve fixed deadlines and uncovered intervals; socket silence is not
continuity evidence. Collect, measure, identify the actual limitation, fix it, then collect again.
