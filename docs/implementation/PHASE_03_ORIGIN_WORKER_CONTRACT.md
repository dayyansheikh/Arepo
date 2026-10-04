# Phase 3 — synthetic origin-worker integration (D053)

The new `exercise_origins` integration requires an explicit `httpx.MockTransport` and refuses
live/default transports. It records real local read/freeze/durability clocks over synthetic
source observations. This is software evidence only, not prospective panel acceptance, SQL
admission or permission to collect a live panel before due-target integration.

## Frozen execution and resource boundaries

One exclusive deterministic `fs2_origin_run_…` per declaration owns the entire attempt.
Reserve D052's full allocation plus 1 MiB worker manifests before invoking activation.
Activation runs internally; no caller-supplied activation summary, origin time, payload,
seed or output path is accepted. Existing/torn runs and activation schedules are never resumed
or advanced. Each activation slot owns an exclusive intent directory; every completed run
reports each slot, including failures, abstentions and expiration.

After the actual scheduled boundary, freeze a source budget from remaining origin-delay time:
three requests, declared bytes per response and three times that total, at most 15 seconds
per request and 180 seconds total. Less than one whole second remaining means no request.
Recheck the gate before each fixed identity→book→trade request. Request the selected Gamma
market, selected token and selected condition; preserve the bounded taker-only trade-page
semantics and make no complete-flow claim. Apply D049 source quota and the declared D051
computation profile. Expiry between requests preserves the partial source journal.

Source/read/computation verification and actual consumption finish before the real origin
freeze. Recheck quote/identity freshness at freeze without reading new values. Compare token,
condition, market, mapping/rule version and outcome against the selected identity; changed
identities abstain. Preserve the original quote, exact midpoint and source quality states even
when the resulting origin abstains. Unknown/closed/rate-limited records are not observed origins.

## Persistence and recovery

The origin-facts acknowledgement must follow freeze, finish within the declared save delay
and precede the target boundary. Derive late-persistence status from immutable facts and
acknowledgements rather than rewriting a saved origin. The final origin receipt must also
precede that target boundary. Keep source/computation lineage, actual read start, actual
freeze, sampling roles and synthetic provenance. No targets are fetched by this milestone.

Use 128 KiB metadata per origin, with 64 KiB reserved for failure/final receipts. The top-level
manifest has 1 MiB with the same failure reserve. Hash every retained source/computation/
intent/fact file into a bounded final receipt: at most 160 files, four path components (including the source-root component),
declared source+computation+metadata bytes, no symlinks, and 60-second snapshot boundary checks.
Partial failure hashes establish byte preservation only, not successful parse/observation
admission. Completed-origin replay additionally verifies the full source and computation
chain and recomputes the original frozen decision. A torn/cancelled run remains incomplete.

The worker preserves all original/source/selection/activation records. Read-only recovery
uses historical clocks and never requires current free disk or reschedules expired slots.
Live orchestration, due-target adaptation, dense feature families and measured controls
remain incomplete. Integrate and test them before removing the synthetic-only API boundary.

## Tests

Full guarded source→read→compute→origin fixture chain; exact request order/identity, quota and
profile binding; actual read/freeze/save ordering; changed rules and closed/rate-limited
abstentions; real delayed save; zero-request expired slots; partial response/expiry preservation;
cancellation and retry refusal; concurrent single ownership; source/metadata tampering;
low-disk preflight and read-only recovery. Full regression and self-review precede commit.
