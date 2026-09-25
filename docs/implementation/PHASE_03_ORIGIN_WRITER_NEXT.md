# Next Phase 3 integration — actual origin journal

Implementation contract to refine against D048–D051 outputs before coding. It is not an
implemented collector, admitted origin or permission to run a live pilot. Current selection
and declaration keep `collection_enabled=false`; no flag may simply be flipped.

## Ordered work

1. Reload checkpoint/master/Phase 3, panel-origin and fresh-selection contracts; inspect
   declaration, selection, SourceRun quotas, actual input reads, quote computation and target
   rules. D051 compact profiles remove one reservation constraint; they do not establish
   capacity for a fresh frame or authorize repeated source measurements.
2. Add a separate, immutable collector activation journal with an exclusive deterministic
   relationship to one declaration and one verified selection. Consume the full selection
   through its verified reader and record actual activation read/start/save clocks. Check
   original frame freshness again. Do not use a copied summary or caller hashes as authority.
3. Freeze an explicit first scheduled boundary derived from the activation acknowledgement
   and a versioned lead interval, then all cycle boundaries from declared cadence. This avoids
   treating minutes spent verifying a large frame as a backdated origin. Include lead time
   in the collector deadline contract. Choose/refine this rule before the first source request,
   never after inspecting price or outcomes.
4. Derive one origin intent per panel/cycle/market/token. Retain all role annotations, but
   never count overlapping roles as separate scientific events. Exclusive intent creation
   is worker ownership; interrupted intents stay failed, never resumed as successful ones.
   Every declared assignment must end in a saved origin or explicit skipped/failed/late record.
5. The worker itself makes the fixed identity→book→bounded-trade requests for the selected
   assignment, using its condition/token lineage and D046 targeted source policy. Apply D049
   retained-byte quota, declared response cap, finite request/time bounds and D051 profile
   exactly. Check the scheduled delay/deadline before operations; expired slots make no new
   requests. No unbounded retries, alternate market or new seed. A trade page is not a complete
   flow window. Retain source failures and all raw bytes.
6. Run the declared quote computation over the actual source run. Consume its verified full
   facts in the origin writer, recording real read/freeze/acknowledgement clocks. Check the
   selected market/token/condition, mapping/rule version, source policy/quota, computation
   profile, complete source closure and all input availability. Preserve mapping known before
   receipt; abstain on changed/ambiguous mapping rather than relabeling an assignment.
7. At actual freeze, recheck receipt and identity age, scheduled-delay limit and source→read→
   computation→origin ordering. Preserve exact numerical fields, quality states, sampling
   lineage, family missingness and source provenance. Origin persistence must finish within
   the declared save limit and before its target boundary. Failed/late saves remain immutable
   evidence and cannot become usable origins by rewriting a field. No SQL admission yet.
8. Target requests cannot start before a verified durable origin. Implement the explicit
   frozen-identity adapter before a target worker: bind the origin mapping's original
   availability and separately retain fresh mapping/lifecycle consistency evidence. Map
   `market_closed` deliberately to known closure; unknown lifecycle, changed rules, invalid
   identity and source failures stay separate abstentions. Resolve failed-book requested
   token from verified request metadata, never from a missing response field.
9. Apply the existing first-valid receipt target rule without replacing pending earlier
   observations or inventing event clocks. Preserve every attempt, late/missed/closed window,
   real computation availability and exact outcome derivation. Reserve all attempts before
   activation; no post-outcome redraw or threshold change.

## Tests and boundary

Use streamed synthetic sources and real local journals to exercise the complete activation→
intent→source→read→compute→origin→target chain. Prove fixed request identity/order, exclusive
ownership, idempotent failed-slot refusal, all declared slot coverage, source/profile quota
binding, original clock preservation, expired-slot zero requests, stale/changed mapping
abstention, failure at each durable boundary and origin acknowledgement before outcome calls.
Include real acknowledgement-delay tests where needed; fabricated timestamps cannot prove
runtime causality. Pin a coherent tested build and self-review before any live pilot proposal.

Full Phase 3 acceptance still requires the remaining feature families, actual measured trigger
negatives/control coverage and prospective pilot gates. Synthetic success or scheduled-only
receipt quotes cannot substitute for them. Production and historical evidence remain untouched.

## D052 activation refinement

The activation read/schedule milestone is implemented in `research_panel/activation.py`;
see PHASE_03_ACTIVATION_CONTRACT.md. Its development lead is explicitly two seconds,
not an empirically validated latency guarantee. It reserves additional activation and
per-origin/target metadata space and keeps all collection/admission flags false. Resume
with the actual worker, not another selection or activation measurement.

The next worker should own one deterministic run directory before invoking activation,
reserve its own bounded top-level manifest space in addition to D052 allocation, and derive
every source/computation/intent directory from the frozen slot IDs. It must consume actual
activation output internally (no caller-supplied summary), enforce each slot's delay gate
before requests and at origin freeze, and record every failed/late/abstaining slot. Default
SourceRun bounds may be reduced from the remaining delay but never expanded past declared
response/retention caps. Match Gamma/book/trade requests to selected market/token/condition
and verify the exact fresh mapping version against the selected identity. A fresh changed
identity is an abstention, not permission to reinterpret the draw.

Persist exact quote/identity facts, all source and computation lineage, actual freeze and
acknowledgement. Derive eligibility from immutable facts and acknowledgements: a late save
must not be repaired into an eligible origin. Retain failed source/compute trees without
claiming their partial contents are validated observations. A source quota failure or HTTP
error cannot silently drop an assigned slot. Complete this synthetic end-to-end path and
the target adapter/worker before a new live pilot. No production entry point or scheduler.
