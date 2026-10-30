# D074 — numerical components at the actual origin

## Scope and evidence

The current origin worker already authenticates three fixed source observations, a durable
quote computation and its actual source-read journal. It omitted the numerical book
components implemented by D057. Reuse those verified rows and exact arithmetic before the
origin freeze. No additional source request, duplicate input-read journal, service or SQL
writer is required. This integration is synthetic until the full pilot gates pass.

## Contract

An explicit boolean `features=True` selects concurrent runtime v3 and origin v2. Defaults
remain concurrent v2 / origin v1. Freeze the exact feature policy in the origin intent before
requests; the runtime version commits to all origins using that mode. Record actual read
start, feature computation completion, origin freeze and durable save separately. Replay at
the original read cutoff, then independently recheck the original freeze's identity, freshness
and deadline eligibility. Never move the cutoff to a later recovery time.

Retain exact F08/F09 snapshot numerator/denominator, terminating decimal or explicit absence,
intermediates, source-local units, source observation IDs and the full D057 projection hash.
Source-ordered full levels remain in the immutable raw and input-read dependency closure;
the manifest does not duplicate every level. Missing native age remains unknown. Raw trade
response IDs are retained without a claim of complete flow or unique fill history.

F01/F02/F10/F27, price history, related markets and external information have explicit current
ineligibility reasons. These are candidate snapshot components, not validated predictive
features or evidence that registered window prerequisites passed. A changed/late/stale origin
cannot acquire snapshot eligibility, even when numerical components can still be preserved.

## Resource and failure boundary

At most one snapshot from the existing at-most-ten-observation projector; existing D057
10,000-level and coefficient/exponent bounds remain. New manifest is at most 16 KiB after
freeze annotations; numerical computation has a 30-second monotonic post-check. Existing
128 KiB origin and target-plan metadata reservations/guards include this payload; no quota
is increased and no overlap discount introduced. The source/input raw closure is unchanged.
Oversize or failed computation preserves source bytes and a terminal failed origin. No
retry, backdated save or post-origin feature calculation is admitted. Existing horizon and
late-persistence checks remain authoritative.

## Validation and next integration

Required checks: exact nonterminating ratios; actual computation before origin; due targets
still consume the same frozen quote; complete original-Git replay; resealed component/cutoff/
eligibility/clock corruption refusal; changed rules/failed source; byte failure; explicit mode
and legacy origin/runtime compatibility. New source package edits must wait until tests finish.

After acceptance, integrate bounded pre-t0 observation evidence into this causal origin
manifest, retaining unsupported native continuity and full existing target/control reservations.
Use the existing socket journal/coverage components and bounded concurrency; do not create a
new hosted collector. Selected external-source linkage needs exact market rule/station/date/
metric correspondence; the D073 KNYC source measurement alone does not establish it. Then
freeze a finite public pilot and measure actual timing, controls and target/family coverage.
