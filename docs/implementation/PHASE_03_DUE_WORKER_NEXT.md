# Next Phase 3 boundary — synthetic due worker (D055 implemented)

Prerequisites: accepted D053 origin worker and D054 frozen-identity adapter. D055 passes
all 1,193 backend tests, including 17 new due-worker cases. Keep the API
synthetic-only until full origin/target orchestration, feature-family/control coverage and
pilot policy are tested. Do not restart live scans or recapture the historical frame.

## Ordered implementation

1. Claim one deterministic target run per panel, freeze worker policy/build and the existing
   worst-case target reservation before reading origin values. No caller clocks, outcomes,
   selected origin lists or alternate target assignments. Do not mutate the origin directory.
2. Consume the complete verified origin run and exact origin facts. Record actual read start/
   completion and acknowledgement. Preserve every slot, including ineligible origins. Only a
   replayed `observed` origin whose final receipt precedes its target can issue requests.
3. Freeze target attempt times from actual origin+horizon and integer offsets
   floor(attempt_index * tolerance_seconds / target_attempts). All attempts and all target
   horizons come from the original declaration. No outcome-driven retry or early stop.
   Process one serialized global queue ordered by scheduled time, origin ID and attempt index.
4. For each attempt, claim an exclusive directory and persist actual intent before requests.
   Ineligible origins and attempts already past the tolerance deadline issue no requests.
   Recheck deadline before both fixed Gamma-market and book calls. Reserve and enforce the
   declared source quota/profile, two response budgets and finite request duration. A response
   that arrives beyond tolerance is retained and explicitly late, never timestamp-repaired.
5. Compute the quote through D045, then consume verified source/computation facts and D054
   adaptation. Bind requested market/token, targeted source policy, declared quotas/profile,
   original frozen identity and fresh consistency. Use actual durable computation availability.
   Retain the full adaptation and actual read/computation/save clocks. Hash complete/partial
   source trees within the existing finite per-attempt budget; failed attempts stay terminal.
6. Preserve every attempt. At final reporting, consume verified attempts at an actual cutoff
   and run the first-valid selector. No failed/partial book computation may disappear before
   choosing a later quote: unresolved evidence makes the outcome incomplete, with blocking
   attempt IDs and no selected value. It cannot silently become a valid missing/flat result.
   Keep target status, excluded quality states, censoring and late attempts distinct.
7. Exact signed midpoint change is a receipt-price diagnostic only, computed with sufficient
   decimal precision after a valid target exists. No execution profit, feature-store label or
   predictive edge claim. No midpoint delta for closed/unavailable/pending/incomplete outcomes.
8. Reader fully replays origins, target source/computation/adaptation, immutable schedules,
   requests and the original final cutoff. No current-clock refresh, resume or replacement.
   A torn worker report stays incomplete; preserve failures and source bytes.

## Tests and limits

Streamed end-to-end synthetic origins plus due sources; actual origin acknowledgement before
all target calls; no early calls; identity changes and known closure; request failures and
late receipts; earlier incomplete computation blocks later valid target; fixed attempts and
full slot coverage; canceled/torn workers; one concurrent owner; partial raw preservation;
resealed source/request/outcome tampering; exact decimal change and read-only replay.

A separate worker started after an entire multi-cycle origin run can legitimately miss early
windows. Record those misses. This milestone must not be described as concurrent live panel
orchestration. Integrate origins and due scheduling before any pilot; do not extend old
horizons or silently reschedule to compensate for worker startup/verification overhead.

## D055 implementation refinement

`research_panel/due_worker.py` now provides a separate synthetic-only executor and full
read-only replay. It claims `fs2_target_run_<panel>` once, with 32 MiB top-level metadata,
16 MiB artefacts, 128 KiB per-attempt metadata, 64 KiB failure reserves and 2 GiB free disk.
All original source/computation reservations remain required; storage is never reclaimed.
Every origin's frozen attempt count is retained, including ineligible and expired attempts.
Partial failure is `incomplete_evidence` and blocks selection of later valid quotes.

Requests begin only after the saved target plan and verified origin receipt. Frozen two-request
budgets use the remaining deadline rounded up to a whole second, with at most 15 seconds per
request and 180 seconds total; deadline is rechecked before each request. This permits a final
response to finish beyond tolerance, which is recorded and excluded as late. It never permits
a new request after the tolerance deadline. No source retry or outcome-driven early stop.

Outcome selection uses availability of the final durable target receipt, including adapter
calculation/persistence; the earlier quote-computation acknowledgement remains separately
preserved in the adaptation. The report records its actual final cutoff and durability. An
exact signed midpoint change is retained only for an observed target, in price units, with
no executable-profit or edge claim. Review binds the consumed origin facts/intent bytes to
the exact hashes verified during origin recovery.

## Next integration boundary after D055 acceptance

Read checkpoint/master/current phase and actual D053–D055 outputs before refining this work.
Implement one bounded synthetic orchestration policy that can process due targets while later
origin cycles remain outstanding. The standalone due worker cannot meet that timing contract
by waiting for the entire origin run; retain its missed windows as recorded.

Freeze single-worker ownership, complete source/metadata reservation and deterministic queue
ordering before activation. Enqueue each origin from the immutable activation schedule; only
a freshly verified durable origin may add its fixed target attempts. Persist each per-origin
target schedule before any request. Prefer a deterministic serialized queue with due time,
then a predeclared tie rule, so a bounded test never opens uncontrolled request concurrency.
Record actual dispatch times and preserve expiration after slow source/compute operations.
The implementation must not backdate targets, reuse caller-provided origin facts, silently
resume torn work, or change the horizon to compensate for latency.

Keep old journal readers and standalone APIs intact; use an explicit new orchestration schema
and full closure reader. Test at least two interleaved origin cycles, due-before-next-origin
ordering, ties, slow origins causing honest missed targets, cancellation, duplicate ownership,
all-role coverage, exact old mapping and availability, and original-build recovery. Validate
and commit before evaluating any live activation. Dense primitive families, durable measured
trigger/control evidence and full prospective pilot gates remain subsequent Phase 3 work.
