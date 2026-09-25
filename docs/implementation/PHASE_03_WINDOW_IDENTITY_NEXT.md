# Phase 3 — causal window identity and endpoint reconciliation

Status: next scoped work after D059. Implement this binding before opening a live socket.

D059 consumes complete raw window journals and reports exact receipt reconstruction diagnostics.
Its declared token/condition is not a verified prior market/rules mapping. Endpoint snapshots
cannot prove every intermediate cancellation/fill; native sequencing and F02/F10/F27 remain gated.

## Ordered scope

1. Consume one successful D057 book computation through its verified reader. Require exactly
   one observed matching selected-market Gamma identity and one book, fresh at the *actual*
   pre-window read/save and subscription boundary. Retain market/condition/token/outcome,
   mapping version, lifecycle/rules provenance, source receipt/availability and computation
   receipt separately. Do not accept caller payloads or re-use current mappings retrospectively.
2. Freeze an exclusive bounded window binding policy before this read. Record actual read and
   durable binding availability before window subscription. Reject source/reader provenance
   mixing; injected transports stay synthetic. No historical selection refresh by implication.
   Window token/condition come from the verified binding, not a second arbitrary argument.
3. Bind the subsequent raw window to the saved pre-window computation/hash. Preserve an initial
   stream snapshot delay and all gaps. A delayed subscription whose identity/quote freshness
   expired is explicit ineligible evidence, not retroactively fresh. No caller clocks, resumption
   or mutable activation. Reuse D058 fixed budgets/heartbeat handling; do not expand them silently.
4. Consume separately collected post-window Gamma/book facts only when their *request starts*
   follow the original window's terminal acknowledgement. Match the original ordered mapping,
   rule/lifecycle fingerprint and fixed token. A changed identity, closure or missing source is
   explicit unavailable/changed status. Post-window facts cannot change earlier diagnostics,
   mapping availability, origin or gap classification.
5. Compare exact executable levels or explicitly scoped best-quote components at each endpoint,
   retaining exact values/differences and clock offsets. Matching values indicate endpoint
   agreement only. Distinct zero levels/source representations remain in their raw sources;
   do not claim full-book equivalence from a best-quote comparison. A separate full-book
   comparison must normalise exact numerical keys, not raw-string formatting, and preserve
   duplicates as invalid instead of silently collapsing them.
6. Full replay binds every dependency, source/read/compute/save clock and exact comparison.
   New recovery output cannot be nested in any source, computation, window or binding directory.
   Bound all new metadata and source reservations, retain partial failures and test concurrency,
   stale/late identity, changed rules/token, early post request, endpoint disagreement, source
   mutation and old-code recovery. No SQL admission or live collector is enabled by pure helpers.
7. Then implement a separately frozen public-socket diagnostic adapter using verified bindings.
   Keep the raw wire API fixed and authentication absent. One subscription, ten-second PINGs,
   at most 60s plus connect/close deadlines, no retry/reconnect or alternate target. Explicitly
   disable environment proxies, compression and transport pings; limit message/queue sizes.
   A transport-rejected oversized message has unavailable raw bytes, not a fabricated prefix.
   Capture actual send/receive/close errors, socket diagnostics and refusal states. Test a real
   local loopback connection as well as synthetic fault paths before a live run.
8. Freeze a single finite diagnostic protocol and commit it before its requests. The previous
   D046 market is a possible fixed target reference, not a new representative selection.
   Inspect lifecycle first and preserve a closed/failed attempt without chasing another target.
   Compare measured semantics with the source contract. Keep source admission and Phase 3 pilot
   acceptance distinct from diagnostic socket success. Do not start Phase 4 in this task.

Official raw market stream and heartbeat basis rechecked 2026-09-24:
https://docs.polymarket.com/market-data/realtime-data . Installed websockets is 17.0.1;
its current connect signature defaults to environment proxy discovery, so the future fixed
public connector must explicitly set proxy=None. No dependency change/install is needed.

Once this milestone is accepted, proceed to measured trigger/control assessments and selected
external-source admission, followed by the separately frozen representative development pilot.
Those requirements still block Phase 3 acceptance. On genuine acceptance stop with the fresh-chat
handover specified by the user's Phase 3-only continuation instruction.

## D060 implementation scope — 2026-09-24

Steps 1–3 now have an exclusive synthetic wrapper, actual pre-computation read and binding
receipt, identity-derived child subscription, original-time freshness replay and transitive
original-code recovery. See PHASE_03_BOUND_WINDOW_CONTRACT.md. This does not supply steps 4–8.

The next post-window consumer must inspect primary `verify_capture` receipt request-start
clocks, reached through verified source-observation capture URIs. The projected row's first
receipt time alone cannot exclude a request initiated during the window and completed later.
Freeze the comparison policy before those reads; use the bound window's durable report receipt
as a conservative after-window boundary and preserve the raw window's earlier terminal time
separately. Source errors, changed mapping/rules, closure, stale and mismatching endpoint values
remain explicit outcomes. An invalid/expired pre-binding can never produce an eligible
comparison. All new original-code recovery output must be outside every transitive dependency.

## D061 implementation scope — 2026-09-25

Steps 4–6 are implemented with primary post-request chronology, original mapping/rule lineage,
explicit unavailability and exact scoped endpoint diagnostics. Final validation is recorded in
the checkpoint/review; see PHASE_03_WINDOW_RECONCILIATION_CONTRACT.md. Next steps 7–8 are refined
in PHASE_03_SOCKET_TRANSPORT_NEXT.md. Redirect rejection is necessary in addition to disabling
proxy discovery; local library inspection found automatic redirect handling. No live socket or
prospective journal admission is enabled by D061.
