# Phase 3 next finite frame capacity — implementation contract

Status: planned, not implemented or run. Prior attempts remain incomplete. Read checkpoint,
phase/frame/panel contracts and D034–D035 before implementation. No scientific threshold or
population definition changes are proposed. This is the exact next engineering milestone.

## Evidence and scope

Actual Gamma scope exceeds 100,000 returned rows. Attempt 2 used 645 MB raw, 1.58 GB retained,
343 MB peak resident and about 196 seconds for enumeration. D034 verified the complete original
journal under its original build without recollection. D035 permits an explicitly declared
400,000-member pure plan; the single-stratum synthetic measurement used 323 MB /29.3 seconds.
These are bounded observations, not guarantees about remaining Gamma pages or metadata tails.

Keep all `closed=false` source rows; do not narrow dates/categories/liquidity, merge incomplete
prefixes, change source identity semantics or turn source groups into independent events.
Continue to retain unknown/excluded identities and all raw numerical/source facts. No models,
origins, production database, scheduler or retention changes belong in this milestone.

## Ordered tasks

1. Reload actual tests/code and verify current local memory/free disk. The prior machine had
   8 GiB RAM and about 16 GB free disk. Check capacity again; do not assume it is unchanged.
2. Implement an explicit larger `FrameBudget`/CLI mode for at most 4,000 sequential requests,
   100 rows/page, 4 MiB/page, 3 GiB raw total, 15s/request, 900s request-admission window,
   8 GiB retained stop and 2 GiB free reserve. These are proposed future ceilings, not active
   collection authority from this document alone. They fit the previous disk measurement but
   need fresh preflight; fail without creating a run if the full reserve is unavailable.
3. Require verified first-page evidence AND the preserved request-ceiling attempt as cost
   lineage before exceeding existing 1,000-request /1 GiB raw /3 GiB retained maxima. Distinguish
   prior byte-ceiling proof from prior request-ceiling proof. Verify all referenced raw bytes,
   receipts/page/report hashes, original policy/scope and actual stop condition; synthetic
   evidence must never authorize live collection. Do not weaken original build admission.
4. Preserve existing small diagnostic/default limits. Freeze larger ceilings explicitly in a
   fresh policy. No hidden retries, old-run extension, budget changes during a run or current
   parser substitution for old facts. Streaming page verification continues; report-size and
   identity-index costs must remain bounded within the actual machine. Housekeeping time is
   separate from admission time. Avoid overlapping capacity measurement with regression tests.
5. Add fault tests for missing/wrong/truncated capacity proof, synthetic/live mismatch,
   raw/request stop distinction, over-max ceilings, free-space refusal and original-journal
   immutability. Run targeted/full isolated checks, self-review, update D036 and commit before
   collection. Existing 755-test result is historical, not validation of those future changes.
6. If preflight and tests pass, run exactly one fresh finite attempt. Preserve its own root,
   implementation hash, source interval, original report/ack and bytes/memory/latency metrics.
   A continuing cursor at any ceiling is still incomplete. Never relabel or delete any prior
   attempt. If safe capacity cannot reach a complete frame, document required data/capacity
   and stop; no paid infrastructure or deletion as an automatic workaround.
7. Inspect complete exhaustion, conflicts and unresolved mapping counts. A complete interval
   enumeration is not an atomic population snapshot. Refine/pin freshness and coverage
   interpretation before seed/sample use. Then implement durable protocol/seed/sample/actual
   read/computation/origin journals per `PHASE_03_PANEL_JOURNAL_CONTRACT.md`, followed by bounded
   collectors/targets and the predeclared prospective pilot. No Phase 4 transition yet.

## Acceptance and output

New bounds are explicit, tested and frozen before requests. Original attempts remain byte-for-
byte intact and retain original status. The new result truthfully reports exhaustion or the
exact incomplete stop; no caller-supplied completeness or synthetic evidence admits a panel.
Update checkpoint/review/master and draft #16. Commit the measurement evidence separately from
its predeclared code/protocol. Phase 3 acceptance still requires the full prospective pilot.
