# Next Phase 3 boundary — synthetic due worker (D055 proposal)

Prerequisites: accepted D053 origin worker and D054 frozen-identity adapter. Keep the API
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
